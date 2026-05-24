from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import ScheduleEvent
from app.services.schedule_service import create_schedule_event
from app.services.memory_service import memory_service

router = APIRouter(prefix="/api", tags=["schedule"])
KSA = timezone(timedelta(hours=3))

ALLOWED_PLATFORMS = {"x", "instagram", "facebook", "linkedin", "tiktok"}


class ScheduleEventInput(BaseModel):
    platform: str
    username: str
    category: str
    content: str

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        if v.lower() not in ALLOWED_PLATFORMS:
            raise ValueError(f"platform must be one of {ALLOWED_PLATFORMS}")
        return v.lower()

    @field_validator("username", "category", "content")
    @classmethod
    def not_empty(cls, v: str, info) -> str:
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return v.strip()


@router.post("/schedule-event")
async def schedule_event(
    payload: ScheduleEventInput,
    db: Session = Depends(get_db),
):
    """
    استقبال JSON للمنشور وإنشاء ScheduleEvent مجدول بناءً على نية المحتوى.
    """
    try:
        event = create_schedule_event(
            db=db,
            platform=payload.platform,
            username=payload.username,
            category=payload.category,
            content=payload.content,
        )
        return event.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────── Webhook من سيرفر app/x ───────────────────
class ScheduleCallbackInput(BaseModel):
    """نموذج payload الذي يرسله سيرفر app/x عند إكمال أو فشل نشر تغريدة مجدولة."""
    event_id: str
    cookie_label: str
    content: str
    success: bool
    tweet_url: Optional[str] = None
    error: Optional[str] = None
    callback_payload: Optional[Dict[str, Any]] = None
    fired_at: Optional[str] = None


@router.post("/webhooks/schedule_callback")
async def schedule_callback(
    payload: ScheduleCallbackInput,
    db: Session = Depends(get_db),
):
    """
    Webhook يستقبل نتيجة نشر تغريدة مجدولة من سيرفر app/x.
    يحدّث الـ ScheduleEvent المحلي ويرسل إشعاراً في محادثة المستخدم.
    """
    event = db.query(ScheduleEvent).filter(
        ScheduleEvent.schedule_event_id == payload.event_id
    ).first()

    if not event:
        # ما عندنا تتبع محلي — رد فقط
        return {"ok": True, "message": "no local event found"}

    # حدّث حالة الحدث المحلي
    if payload.success:
        event.status = "PUBLISHED"
        event.tweet_url = payload.tweet_url
        event.error_message = None
        event.published_at = datetime.utcnow()
    else:
        event.status = "FAILED"
        event.error_message = (payload.error or "خطأ غير معروف")[:500]
    db.commit()

    # ابعث إشعاراً في الـ conversation لو متوفر
    conversation_id = event.conversation_id
    if conversation_id:
        run_at_ksa = event.run_at.replace(tzinfo=timezone.utc).astimezone(KSA)
        time_str = run_at_ksa.strftime("%I:%M %p")

        if payload.success:
            msg = (
                f"🔔 **إشعار: تم نشر تغريدتك المجدولة**\n\n"
                f"📝 {event.content[:120]}{'...' if len(event.content) > 120 else ''}\n"
                f"👤 الحساب: @{event.username}\n"
                f"🕐 الوقت: {time_str}\n"
                f"🆔 المعرّف: {event.schedule_event_id}"
            )
            if payload.tweet_url:
                msg += f"\n🔗 الرابط: {payload.tweet_url}"
        else:
            msg = (
                f"⚠️ **إشعار: فشل نشر تغريدتك المجدولة**\n\n"
                f"📝 {event.content[:120]}{'...' if len(event.content) > 120 else ''}\n"
                f"👤 الحساب: @{event.username}\n"
                f"🆔 المعرّف: {event.schedule_event_id}\n"
                f"❌ السبب: {(payload.error or 'غير معروف')[:200]}"
            )

        try:
            memory_service.add_message(
                db=db,
                conversation_id=conversation_id,
                role="assistant",
                content=msg,
                intent="schedule_notification",
                agent="Scheduler",
            )
            db.commit()
        except Exception as e:
            print(f"[Webhook] Failed to notify chat: {e}")

    return {
        "ok": True,
        "event_id": payload.event_id,
        "status": event.status,
        "notified_chat": bool(conversation_id),
    }
