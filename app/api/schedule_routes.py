from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.schedule_service import create_schedule_event

router = APIRouter(prefix="/api", tags=["schedule"])

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
