"""
X Validation
Checks candidates against X/Twitter to measure real-time traction.
Uses custom X API server (POST /api/search) for validation searches.
Assigns verdict: HOT / EARLY / NOT_YET
"""
import aiohttp
from typing import List
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.trend_detector.models import Candidate, XValidation, Watchlist
from app.trend_detector.config import (
    X_API_SERVER_URL,
    VALIDATION_THRESHOLDS,
    WATCHLIST_MAX_CHECKS,
    WATCHLIST_CHECK_INTERVAL,
)


class XValidator:
    """Validate candidates by checking activity on X via custom API"""

    REQUEST_TIMEOUT = 60   # seconds per search request
    MAX_VALIDATIONS_PER_BATCH = 15  # Max candidates to validate per cycle

    def is_configured(self) -> bool:
        return bool(X_API_SERVER_URL)

    async def _search_x(self, query: str, session: aiohttp.ClientSession) -> List[dict]:
        """Search recent tweets on X via custom API POST /api/search"""
        try:
            async with session.post(
                f"{X_API_SERVER_URL}/api/search",
                json={
                    "query": query,
                    "type": "Latest",
                    "max_pages": 3,
                },
                timeout=aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT),
            ) as resp:
                if resp.status != 200:
                    print(f"[XValidator] Search API error: {resp.status}")
                    return []

                data = await resp.json()
                if data.get("error"):
                    print(f"[XValidator] Search error: {data['error']}")
                    return []

                return data.get("tweets", [])

        except Exception as e:
            print(f"[XValidator] Search request error: {e}")
            return []

    def _build_search_query(self, candidate: Candidate) -> str:
        """Build an X search query from candidate title (unique per candidate)"""
        # Use title first (unique per candidate), fall back to keywords
        title = (candidate.title or "").strip()
        if title:
            # Take first meaningful chunk of the title (3-6 words)
            words = title.split()[:6]
            query = " ".join(words)
        elif candidate.keywords:
            terms = candidate.keywords.split(",")[:3]
            query = " ".join(t.strip() for t in terms if t.strip())
        else:
            return ""

        if len(query) > 200:
            query = query[:200]

        return query

    def _analyze_results(self, tweets: List[dict]) -> dict:
        """Analyze tweets from custom API to get validation metrics"""
        if not tweets:
            return {
                "post_count": 0,
                "unique_authors": 0,
                "total_engagement": 0,
                "post_density_per_hour": 0.0,
                "recent_post_count": 0,
            }

        authors = set()
        total_engagement = 0
        timestamps = []
        now = datetime.now(timezone.utc)

        for tweet in tweets:
            screen_name = tweet.get("screen_name", "")
            if screen_name:
                authors.add(screen_name)

            # Sum engagement from custom API fields
            likes = tweet.get("favorite_count", 0) or 0
            retweets = tweet.get("retweet_count", 0) or 0
            replies = tweet.get("reply_count", 0) or 0
            total_engagement += likes + retweets + replies

            # Parse timestamp
            created_at = tweet.get("created_at")
            if created_at:
                try:
                    ts = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
                    timestamps.append(ts)
                except (ValueError, TypeError):
                    pass

        # Calculate density from RECENT tweets only (last 4 hours)
        recent_cutoff = now - timedelta(hours=4)
        recent_timestamps = [ts for ts in timestamps if ts >= recent_cutoff]
        recent_count = len(recent_timestamps)

        post_density = 0.0
        if recent_count >= 2:
            post_density = recent_count / 4.0  # posts per hour over the last 4 hours
        elif recent_count == 1:
            post_density = 1.0

        return {
            "post_count": len(tweets),
            "unique_authors": len(authors),
            "total_engagement": total_engagement,
            "post_density_per_hour": round(post_density, 2),
            "recent_post_count": recent_count,
        }

    def _decide_verdict(self, metrics: dict, score: float) -> str:
        """
        Decide HOT / EARLY / NOT_YET based on metrics and score.
        
        HOT paths:
          1. High score + enough authors + recent activity (density)
          2. High score + massive engagement (>10K) — viral even if density is low
        """
        hot = VALIDATION_THRESHOLDS["hot"]
        early = VALIDATION_THRESHOLDS["early"]

        # Path 1: Standard — score + authors + density
        standard_hot = (
            score >= hot["min_score"]
            and metrics["unique_authors"] >= hot["min_unique_authors"]
            and metrics["post_density_per_hour"] >= hot["min_post_density"]
        )

        # Path 2: Viral engagement — score + high engagement even without density
        viral_hot = (
            score >= hot["min_score"]
            and metrics["total_engagement"] >= 10000
            and metrics["unique_authors"] >= 3
        )

        if standard_hot or viral_hot:
            return "HOT"

        if (
            score >= early["min_score"]
            and (
                metrics["unique_authors"] >= early["min_unique_authors"]
                or metrics["total_engagement"] >= 1000
            )
        ):
            return "EARLY"

        return "NOT_YET"

    async def validate(self, candidates: List[Candidate], db: Session) -> List[Candidate]:
        """
        Validate a list of candidates against X.
        - HOT → status = 'hot', proceed to classifier
        - EARLY → add to watchlist
        - NOT_YET → status = 'not_yet', loop back for re-scoring later
        
        Returns only HOT candidates.
        """
        if not self.is_configured():
            print("[XValidator] Not configured — using score-only fallback")
            hot_candidates = []
            for candidate in candidates:
                if candidate.score >= VALIDATION_THRESHOLDS["hot"]["min_score"]:
                    candidate.status = "hot"
                    hot_candidates.append(candidate)
                elif candidate.score >= VALIDATION_THRESHOLDS["early"]["min_score"]:
                    candidate.status = "early"
                    self._add_to_watchlist(candidate, db)
                else:
                    candidate.status = "not_yet"
            db.commit()
            print(f"[XValidator] Score-only: {len(hot_candidates)} HOT, {len(candidates) - len(hot_candidates)} deferred")
            return hot_candidates

        hot_candidates = []

        # Only validate candidates with score >= early threshold (skip low-score ones)
        early_min = VALIDATION_THRESHOLDS["early"]["min_score"]
        worth_validating = [c for c in candidates if c.score >= early_min]
        skip_count = len(candidates) - len(worth_validating)

        # Mark low-score candidates as not_yet without wasting API calls
        for c in candidates:
            if c.score < early_min:
                c.status = "not_yet"

        # Limit batch size to avoid long-running validation cycles
        to_validate = worth_validating[:self.MAX_VALIDATIONS_PER_BATCH]
        if skip_count > 0 or len(worth_validating) > len(to_validate):
            print(f"[XValidator] Validating {len(to_validate)} of {len(candidates)} candidates (skipped {skip_count} low-score, deferred {max(0, len(worth_validating) - len(to_validate))} overflow)")

        async with aiohttp.ClientSession() as session:
            for candidate in to_validate:
                query = self._build_search_query(candidate)
                tweets = await self._search_x(query, session)
                metrics = self._analyze_results(tweets)
                verdict = self._decide_verdict(metrics, candidate.score)

                # Save validation record
                validation = XValidation(
                    candidate_id=candidate.id,
                    search_query=query,
                    post_count=metrics["post_count"],
                    unique_authors=metrics["unique_authors"],
                    total_engagement=metrics["total_engagement"],
                    post_density_per_hour=metrics["post_density_per_hour"],
                    verdict=verdict,
                    raw_data={
                        "tweet_count_raw": len(tweets),
                        "query_used": query,
                    },
                    checked_at=datetime.now(timezone.utc),
                )
                db.add(validation)

                # Update candidate status
                candidate.status = verdict.lower()

                if verdict == "HOT":
                    hot_candidates.append(candidate)
                elif verdict == "EARLY":
                    self._add_to_watchlist(candidate, db)

        db.commit()
        print(f"[XValidator] Validated {len(candidates)} → {len(hot_candidates)} HOT")
        return hot_candidates

    def _add_to_watchlist(self, candidate: Candidate, db: Session):
        """Add an EARLY candidate to the watchlist for re-checking"""
        existing = (
            db.query(Watchlist)
            .filter(Watchlist.candidate_id == candidate.id, Watchlist.is_active == True)
            .first()
        )
        if existing:
            return

        watchlist_entry = Watchlist(
            candidate_id=candidate.id,
            check_count=0,
            max_checks=WATCHLIST_MAX_CHECKS,
            next_check_at=datetime.now(timezone.utc) + timedelta(minutes=WATCHLIST_CHECK_INTERVAL),
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(watchlist_entry)
