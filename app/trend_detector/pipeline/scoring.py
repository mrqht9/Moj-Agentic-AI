"""
Scoring Engine
Calculates priority score for each candidate based on configurable weighted metrics.
"""
from typing import List
from sqlalchemy.orm import Session

from app.trend_detector.models import Candidate
from app.trend_detector.config import (
    SCORING_WEIGHTS,
    PLATFORM_THRESHOLDS,
)


class ScoringEngine:
    """Calculate weighted score for candidates based on engagement metrics"""

    def _get_thresholds(self, platform: str) -> dict:
        """Get thresholds for a specific platform, fallback to reddit defaults"""
        return PLATFORM_THRESHOLDS.get(platform, PLATFORM_THRESHOLDS.get("reddit", {}))

    def _score_candidate(self, candidate: Candidate) -> float:
        """
        Calculate score for a single candidate.
        Each metric that exceeds its platform threshold earns the configured weight points.
        Cross-platform bonus if seen on 2+ platforms.
        Trending source bonus for aggregator platforms (e.g. Google Trends).
        """
        score = 0.0

        # Get all platforms this candidate appeared on
        platforms = [p.strip() for p in (candidate.platforms or "reddit").split(",") if p.strip()]
        primary_platform = platforms[0]
        thresholds = self._get_thresholds(primary_platform)

        # Views
        if candidate.views_total > thresholds.get("views", 0):
            score += SCORING_WEIGHTS.get("views", 0)

        # Likes
        if candidate.likes_total > thresholds.get("likes", 0):
            score += SCORING_WEIGHTS.get("likes", 0)

        # Reshares
        if candidate.reshares_total > thresholds.get("reshares", 0):
            score += SCORING_WEIGHTS.get("reshares", 0)

        # Comments
        if candidate.comments_total > thresholds.get("comments", 0):
            score += SCORING_WEIGHTS.get("comments", 0)

        # Cross-platform bonus
        if candidate.platform_count and candidate.platform_count >= 2:
            score += SCORING_WEIGHTS.get("cross_platform", 0)

        # Trending source bonus (Google Trends, etc.)
        for plat in platforms:
            plat_config = PLATFORM_THRESHOLDS.get(plat, {})
            if plat_config.get("is_trending_source"):
                score += SCORING_WEIGHTS.get("trending_source", 0)
                break  # Only award once

        # Media bonus
        if candidate.media_url:
            score += SCORING_WEIGHTS.get("has_media", 0)

        return score

    def process(self, candidates: List[Candidate], db: Session) -> List[Candidate]:
        """
        Score all provided candidates and update their score in the DB.
        Returns candidates sorted by score descending.
        """
        for candidate in candidates:
            candidate.score = self._score_candidate(candidate)

        db.commit()

        scored = sorted(candidates, key=lambda c: c.score, reverse=True)
        print(f"[ScoringEngine] Scored {len(scored)} candidates — top score: {scored[0].score if scored else 0}")
        return scored
