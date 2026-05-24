"""
Scheduler Tick — (مُبسّط بعد نقل النشر التلقائي إلى app/x server)

دور هذا الـ tick حالياً:
- يتعامل فقط مع منصات غير X (instagram, facebook, ...) — يمرّرها لنظام خارجي (n8n) عبر JSON
- تغريدات X يتولاها سيرفر app/x مباشرة عبر API /api/scheduled_post
- لو كان منصة X فقط، فهذا الـ tick فعلياً no-op

هذا الـ tick سيخدم منصات أخرى مستقبلاً (Instagram, TikTok scheduling, ...)
"""
import asyncio
import logging
from pathlib import Path
import json

from app.db.database import SessionLocal
from app.services.schedule_service import get_due_events, mark_ready_to_publish

logger = logging.getLogger(__name__)

OUTPUTS_DIR = Path(__file__).parent.parent.parent / "data" / "schedule_outputs"
TICK_INTERVAL = 30


async def scheduler_tick():
    """
    يعمل كل TICK_INTERVAL ثانية:
    - يفحص الأحداث المجدولة من منصات غير X
    - يحدّث حالتها إلى READY_TO_PUBLISH
    - يكتب JSON إلى مجلد outputs (لـ n8n أو نظام خارجي)

    ⚠️ تغريدات X لا تمر من هنا — سيرفر app/x يتولاها مباشرة عبر:
       POST /api/scheduled_post في app/x  (مع callback لإشعار الشات)
    """
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Scheduler tick started (non-X platforms handler)")

    while True:
        try:
            db = SessionLocal()
            try:
                due = get_due_events(db)
                for event in due:
                    # تخطّى تغريدات X — سيرفر app/x يتولاها
                    if event.platform == "x":
                        continue

                    mark_ready_to_publish(db, event)
                    output = event.to_dict()
                    out_file = OUTPUTS_DIR / f"{event.schedule_event_id}.json"
                    out_file.write_text(
                        json.dumps(output, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    logger.info(
                        f"[Scheduler] {event.schedule_event_id} ({event.platform}) "
                        f"→ READY_TO_PUBLISH | JSON: {out_file}"
                    )
            finally:
                db.close()
        except Exception as e:
            logger.error(f"[Scheduler] tick error: {e}")
            import traceback
            traceback.print_exc()

        await asyncio.sleep(TICK_INTERVAL)
