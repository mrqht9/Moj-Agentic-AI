import random
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import ScheduleEvent
from app.core.config import settings

logger = logging.getLogger(__name__)

KSA = ZoneInfo("Asia/Riyadh")
UTC = ZoneInfo("UTC")

TIME_WINDOWS = {
    "morning": (6, 11),
    "noon":    (11, 15),
    "evening": (15, 20),
    "night":   (20, 26),
}

MORNING_KEYWORDS = [
    "صباح", "صبح", "الفجر", "فجر", "بكرة", "بكير", "الصبح",
    "good morning", "morning",
]
NOON_KEYWORDS = [
    "ظهر", "الظهر", "الظهيرة", "منتصف النهار", "noon", "midday",
]
EVENING_KEYWORDS = [
    "مساء", "العصر", "عصر", "المغرب", "مغرب", "evening", "afternoon",
]
NIGHT_KEYWORDS = [
    "ليل", "الليل", "ليلة", "منتصف الليل", "سهر", "night", "midnight",
]

POSITIVE_KEYWORDS = [
    "سعيد", "سعيدة", "خير", "جميل", "رائع", "ممتاز", "مبارك",
    "تهنئة", "مبروك", "يسعد", "فرح", "فرحة", "بشرى", "نجاح",
    "happy", "great", "wonderful", "congrats", "blessed", "joy",
]
NEGATIVE_KEYWORDS = [
    "حزن", "حزين", "مؤلم", "صعب", "مشكلة", "ألم", "خسارة",
    "وفاة", "مصيبة", "كارثة", "sad", "pain", "loss", "difficult",
]
NEUTRAL_KEYWORDS = [
    "معلومة", "خبر", "تذكير", "تنبيه", "info", "news", "reminder",
]


def _detect_intent_time(content: str, category: str) -> str:
    text = (content + " " + category).lower()

    if any(k in text for k in MORNING_KEYWORDS):
        return "morning"
    if any(k in text for k in NOON_KEYWORDS):
        return "noon"
    if any(k in text for k in EVENING_KEYWORDS):
        return "evening"
    if any(k in text for k in NIGHT_KEYWORDS):
        return "night"
    return "default"


def _detect_mood(content: str, category: str) -> str:
    text = (content + " " + category).lower()

    if any(k in text for k in POSITIVE_KEYWORDS):
        return "positive"
    if any(k in text for k in NEGATIVE_KEYWORDS):
        return "negative"
    return "neutral"


def _pick_run_at(intent_time: str) -> datetime:
    now_ksa = datetime.now(KSA)

    if intent_time in TIME_WINDOWS:
        start_h, end_h = TIME_WINDOWS[intent_time]
        candidate_start = now_ksa.replace(hour=start_h % 24, minute=0, second=0, microsecond=0)
        candidate_end   = now_ksa.replace(hour=end_h % 24,   minute=0, second=0, microsecond=0)

        if end_h >= 24:
            candidate_end = candidate_end + timedelta(days=1)

        if candidate_end <= now_ksa:
            candidate_start += timedelta(days=1)
            candidate_end   += timedelta(days=1)

        if candidate_start < now_ksa:
            candidate_start = now_ksa + timedelta(minutes=5)

        window_seconds = int((candidate_end - candidate_start).total_seconds())
        if window_seconds <= 0:
            window_seconds = 3600
        offset = random.randint(0, window_seconds)
        run_at_ksa = candidate_start + timedelta(seconds=offset)
    else:
        offset = random.randint(0, 86400)
        run_at_ksa = now_ksa + timedelta(seconds=offset)

    run_at_utc = run_at_ksa.astimezone(UTC).replace(tzinfo=None)
    return run_at_utc


def _generate_event_id() -> str:
    import secrets
    token = secrets.token_hex(4).upper()
    return f"evt_{token}"


def create_schedule_event(
    db: Session,
    platform: str,
    username: str,
    category: str,
    content: str,
) -> ScheduleEvent:
    intent_time = _detect_intent_time(content, category)
    mood = _detect_mood(content, category)
    run_at = _pick_run_at(intent_time)
    event_id = _generate_event_id()

    event = ScheduleEvent(
        schedule_event_id=event_id,
        platform=platform,
        username=username,
        category=category,
        content=content,
        run_at=run_at,
        intent_time=intent_time,
        mood=mood,
        status="SCHEDULED",
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    logger.info(f"Created ScheduleEvent {event_id} run_at={run_at} intent={intent_time} mood={mood}")
    return event


def get_due_events(db: Session) -> list[ScheduleEvent]:
    now_utc = datetime.utcnow()
    return (
        db.query(ScheduleEvent)
        .filter(
            ScheduleEvent.status == "SCHEDULED",
            ScheduleEvent.run_at <= now_utc,
        )
        .all()
    )


def mark_ready_to_publish(db: Session, event: ScheduleEvent) -> ScheduleEvent:
    event.status = "READY_TO_PUBLISH"
    event.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(event)
    logger.info(f"ScheduleEvent {event.schedule_event_id} → READY_TO_PUBLISH")
    return event
