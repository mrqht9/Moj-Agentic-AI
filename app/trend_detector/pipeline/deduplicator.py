"""
Deduplicator & Merger
Takes unprocessed Signals, groups similar ones, and creates/updates Candidates.
Uses title-based fingerprinting + keyword overlap for similarity.
"""
import hashlib
import re
from typing import List
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.trend_detector.models import Signal, Candidate


class Deduplicator:
    """Deduplicate signals and merge into candidates"""

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison: lowercase, strip punctuation/whitespace"""
        if not text:
            return ""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text

    def _fingerprint(self, title: str, keywords: str = "") -> str:
        """Create a SHA-256 fingerprint from normalized title + keywords"""
        normalized = self._normalize_text(title)
        if keywords:
            normalized += " " + self._normalize_text(keywords)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _word_overlap_ratio(self, text_a: str, text_b: str) -> float:
        """Calculate word overlap ratio between two texts"""
        words_a = set(self._normalize_text(text_a).split())
        words_b = set(self._normalize_text(text_b).split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union) if union else 0.0

    def process(self, signals: List[Signal], db: Session, similarity_threshold: float = 0.6) -> List[Candidate]:
        """
        Process unprocessed signals into candidates.
        - Exact fingerprint match → merge into existing candidate
        - High word overlap with existing candidate → merge
        - Otherwise → create new candidate
        
        Returns list of new or updated Candidates.
        """
        updated_candidates = []
        existing_candidates = db.query(Candidate).filter(
            Candidate.status.in_(["pending", "validated", "early"])
        ).all()

        for signal in signals:
            if signal.is_processed:
                continue

            fp = self._fingerprint(signal.title, signal.keywords)

            # 1. Check exact fingerprint match
            candidate = db.query(Candidate).filter(Candidate.fingerprint == fp).first()

            # 2. If no exact match, check word overlap with recent candidates
            if not candidate:
                best_match = None
                best_score = 0.0
                for c in existing_candidates:
                    score = self._word_overlap_ratio(signal.title, c.title)
                    if score > best_score:
                        best_score = score
                        best_match = c
                if best_match and best_score >= similarity_threshold:
                    candidate = best_match

            if candidate:
                # Merge into existing candidate
                candidate.views_total += signal.views
                candidate.likes_total += signal.likes
                candidate.reshares_total += signal.reshares
                candidate.comments_total += signal.comments

                # Update platforms list
                current_platforms = set((candidate.platforms or "").split(","))
                current_platforms.discard("")
                current_platforms.add(signal.platform)
                candidate.platforms = ",".join(current_platforms)
                candidate.platform_count = len(current_platforms)

                # Append signal ID
                current_ids = set((candidate.source_signal_ids or "").split(","))
                current_ids.discard("")
                current_ids.add(str(signal.id))
                candidate.source_signal_ids = ",".join(current_ids)

                candidate.updated_at = datetime.now(timezone.utc)
            else:
                # Create new candidate
                candidate = Candidate(
                    fingerprint=fp,
                    title=signal.title,
                    content=signal.content,
                    keywords=signal.keywords,
                    url=signal.url,
                    media_url=signal.media_url,
                    platforms=signal.platform,
                    source_signal_ids=str(signal.id),
                    first_seen_at=signal.published_at or datetime.now(timezone.utc),
                    views_total=signal.views,
                    likes_total=signal.likes,
                    reshares_total=signal.reshares,
                    comments_total=signal.comments,
                    platform_count=1,
                    score=0.0,
                    status="pending",
                    created_at=datetime.now(timezone.utc),
                )
                db.add(candidate)
                existing_candidates.append(candidate)

            # Mark signal as processed
            signal.is_processed = True
            updated_candidates.append(candidate)

        if updated_candidates:
            db.commit()

        unique_candidates = {id(c): c for c in updated_candidates}
        print(f"[Deduplicator] Processed {len(signals)} signals → {len(unique_candidates)} candidates")
        return list(unique_candidates.values())
