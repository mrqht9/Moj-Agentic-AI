"""
Normalizer
Takes raw signal dicts from collectors and persists them as Signal rows in DB.
"""
from typing import List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.trend_detector.models import Signal


class Normalizer:
    """Normalize raw collector output into Signal DB rows"""

    def process(self, raw_signals: List[Dict[str, Any]], db: Session) -> List[Signal]:
        """
        Persist raw signals into the td_signals table.
        Skips signals that already exist (by platform + source_id).
        Returns list of newly created Signal objects.
        """
        new_signals = []

        for raw in raw_signals:
            platform = raw.get("platform", "unknown")
            source_id = raw.get("source_id", "")

            # Skip if already ingested
            existing = (
                db.query(Signal)
                .filter(Signal.platform == platform, Signal.source_id == source_id)
                .first()
            )
            if existing:
                continue

            signal = Signal(
                platform=platform,
                source_id=source_id,
                title=(raw.get("title") or "")[:1000],
                content=raw.get("content"),
                url=raw.get("url"),
                media_url=raw.get("media_url"),
                media_text=raw.get("media_text"),
                keywords=raw.get("keywords"),
                author=raw.get("author"),
                published_at=raw.get("published_at"),
                views=raw.get("views", 0),
                likes=raw.get("likes", 0),
                reshares=raw.get("reshares", 0),
                comments=raw.get("comments", 0),
                has_media=raw.get("has_media", False),
                raw_data=raw.get("raw_data"),
                is_processed=False,
                created_at=datetime.now(timezone.utc),
            )
            db.add(signal)
            new_signals.append(signal)

        if new_signals:
            db.commit()
            for s in new_signals:
                db.refresh(s)

        print(f"[Normalizer] Ingested {len(new_signals)} new signals (skipped {len(raw_signals) - len(new_signals)} duplicates)")
        return new_signals
