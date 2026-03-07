"""
Trend Detector Scheduler
Orchestrates the full pipeline: Collect → Normalize → Dedup → Score → Validate → Classify
Uses APScheduler for periodic background tasks.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.trend_detector.models import Candidate, Watchlist
from app.trend_detector.config import (
    COLLECTOR_INTERVALS,
    WATCHLIST_CHECK_INTERVAL,
    WATCHLIST_MAX_CHECKS,
)

from app.trend_detector.collectors.reddit import RedditCollector
from app.trend_detector.collectors.google_trends import GoogleTrendsCollector
from app.trend_detector.collectors.x_collector import XCollector
from app.trend_detector.collectors.tiktok import TikTokCollector
from app.trend_detector.media.vision_analyzer import VisionAnalyzer
from app.trend_detector.pipeline.normalizer import Normalizer
from app.trend_detector.pipeline.deduplicator import Deduplicator
from app.trend_detector.pipeline.scoring import ScoringEngine
from app.trend_detector.pipeline.validator import XValidator
from app.trend_detector.classifier.classifier import Classifier


class TrendDetectorScheduler:
    """Main orchestrator for the trend detection pipeline"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.normalizer = Normalizer()
        self.deduplicator = Deduplicator()
        self.scoring_engine = ScoringEngine()
        self.validator = XValidator()
        self.classifier = Classifier()

        # Media analyzer
        self.vision_analyzer = VisionAnalyzer()

        # Collectors
        self.reddit_collector = RedditCollector()
        self.google_trends_collector = GoogleTrendsCollector()
        self.x_collector = XCollector()
        self.tiktok_collector = TikTokCollector()

        self._is_running = False

    def start(self):
        """Start the scheduler with all jobs"""
        if self._is_running:
            print("[TrendScheduler] Already running")
            return

        # Register all collectors
        collectors = [
            ("reddit", self.reddit_collector),
            ("google_trends", self.google_trends_collector),
            ("x", self.x_collector),
            ("tiktok", self.tiktok_collector),
        ]

        delay = 10
        for name, collector in collectors:
            if collector.is_configured():
                interval = COLLECTOR_INTERVALS.get(name, 30)
                self.scheduler.add_job(
                    self._run_collector_pipeline,
                    trigger=IntervalTrigger(minutes=interval),
                    args=[collector],
                    id=f"{name}_collector",
                    name=f"{name.upper()} Collector Pipeline",
                    replace_existing=True,
                    next_run_time=datetime.now(timezone.utc) + timedelta(seconds=delay),
                )
                print(f"[TrendScheduler] {name.upper()} collector scheduled every {interval}min")
                delay += 15  # Stagger start times
            else:
                print(f"[TrendScheduler] {name.upper()} collector not configured — skipped")

        # Watchlist re-check job
        self.scheduler.add_job(
            self._recheck_watchlist,
            trigger=IntervalTrigger(minutes=WATCHLIST_CHECK_INTERVAL),
            id="watchlist_recheck",
            name="Watchlist Re-checker",
            replace_existing=True,
        )
        print(f"[TrendScheduler] Watchlist re-check scheduled every {WATCHLIST_CHECK_INTERVAL}min")

        self.scheduler.start()
        self._is_running = True
        print("[TrendScheduler] Started successfully")

    def stop(self):
        """Stop the scheduler"""
        if self._is_running:
            self.scheduler.shutdown(wait=False)
            self._is_running = False
            print("[TrendScheduler] Stopped")

    async def _run_collector_pipeline(self, collector):
        """
        Full pipeline for a single collector:
        Collect → Normalize → Dedup → Score → Validate → Classify
        """
        db: Session = SessionLocal()
        try:
            collector_name = collector.platform.upper()
            print(f"\n{'='*60}")
            print(f"[TrendScheduler] Running {collector_name} pipeline — {datetime.now(timezone.utc).isoformat()}")
            print(f"{'='*60}")

            # 1. Collect raw signals
            raw_signals = await collector.collect()
            if not raw_signals:
                print(f"[TrendScheduler] No new signals from {collector_name}")
                return

            # 1.5 Media analysis for signals with media
            raw_signals = await self.vision_analyzer.process_signals(raw_signals)

            # 2. Normalize and persist signals
            new_signals = self.normalizer.process(raw_signals, db)
            if not new_signals:
                print(f"[TrendScheduler] All signals were duplicates")
                return

            # 3. Dedup and merge into candidates
            candidates = self.deduplicator.process(new_signals, db)
            if not candidates:
                print(f"[TrendScheduler] No new candidates after dedup")
                return

            # 4. Score candidates
            scored = self.scoring_engine.process(candidates, db)

            # 5. Validate against X
            hot_candidates = await self.validator.validate(scored, db)

            # 6. Classify HOT candidates
            if hot_candidates:
                await self.classifier.classify(hot_candidates, db)
                print(f"[TrendScheduler] Pipeline complete — {len(hot_candidates)} HOT trends detected")
            else:
                print(f"[TrendScheduler] Pipeline complete — no HOT trends this cycle")

        except Exception as e:
            print(f"[TrendScheduler] Pipeline error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()

    async def _recheck_watchlist(self):
        """
        Re-check EARLY signals on the watchlist.
        - If graduated to HOT → classify
        - If max checks reached → expire
        - Otherwise → update next_check_at with increasing interval
        """
        db: Session = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            due_entries = (
                db.query(Watchlist)
                .filter(
                    Watchlist.is_active == True,
                    Watchlist.next_check_at <= now,
                )
                .all()
            )

            if not due_entries:
                return

            print(f"[TrendScheduler] Re-checking {len(due_entries)} watchlist entries")

            for entry in due_entries:
                candidate = (
                    db.query(Candidate)
                    .filter(Candidate.id == entry.candidate_id)
                    .first()
                )

                if not candidate:
                    entry.is_active = False
                    continue

                entry.check_count += 1
                entry.last_checked_at = now

                # Max checks reached → expire
                if entry.check_count >= entry.max_checks:
                    entry.is_active = False
                    candidate.status = "expired"
                    print(f"[Watchlist] Candidate {candidate.id} expired after {entry.check_count} checks")
                    continue

                # Re-score the candidate
                self.scoring_engine.process([candidate], db)

                # Re-validate
                hot = await self.validator.validate([candidate], db)

                if hot:
                    # Graduated to HOT
                    entry.is_active = False
                    await self.classifier.classify(hot, db)
                    print(f"[Watchlist] Candidate {candidate.id} graduated to HOT!")
                else:
                    # Increasing interval: 15min * (check_count + 1)
                    interval_minutes = WATCHLIST_CHECK_INTERVAL * (entry.check_count + 1)
                    entry.next_check_at = now + timedelta(minutes=interval_minutes)

            db.commit()

        except Exception as e:
            print(f"[TrendScheduler] Watchlist error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()

    async def run_pipeline_once(self, platform: str = "reddit"):
        """
        Run the pipeline once manually (for testing / API trigger).
        Returns dict with results summary.
        """
        collectors = {
            "reddit": self.reddit_collector,
            "google_trends": self.google_trends_collector,
            "x": self.x_collector,
            "tiktok": self.tiktok_collector,
        }

        collector = collectors.get(platform)
        if not collector:
            return {"error": f"Unknown platform: {platform}"}

        if not collector.is_configured():
            return {"error": f"Platform '{platform}' not configured — add API keys to .env"}

        db: Session = SessionLocal()
        try:
            raw_signals = await collector.collect()
            raw_signals = await self.vision_analyzer.process_signals(raw_signals)
            new_signals = self.normalizer.process(raw_signals, db)
            candidates = self.deduplicator.process(new_signals, db)
            scored = self.scoring_engine.process(candidates, db) if candidates else []
            hot = await self.validator.validate(scored, db) if scored else []
            classified = await self.classifier.classify(hot, db) if hot else []

            return {
                "platform": platform,
                "raw_signals": len(raw_signals),
                "new_signals": len(new_signals),
                "candidates": len(candidates),
                "scored": len(scored),
                "hot": len(hot),
                "classified": len(classified),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        finally:
            db.close()


# Singleton instance
trend_scheduler = TrendDetectorScheduler()
