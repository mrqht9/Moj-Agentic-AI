import asyncio
import logging
from pathlib import Path
import json
from datetime import datetime

from app.db.database import SessionLocal
from app.services.schedule_service import get_due_events, mark_ready_to_publish

logger = logging.getLogger(__name__)

OUTPUTS_DIR = Path(__file__).parent.parent.parent / "data" / "schedule_outputs"
TICK_INTERVAL = 30


async def scheduler_tick():
    """
    يعمل كل TICK_INTERVAL ثانية، يفحص الأحداث المجدولة التي حان وقتها
    ويغير حالتها إلى READY_TO_PUBLISH ويحفظ JSON في مجلد outputs.
    """
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Scheduler tick started")

    while True:
        try:
            db = SessionLocal()
            try:
                due = get_due_events(db)
                for event in due:
                    mark_ready_to_publish(db, event)
                    output = event.to_dict()
                    out_file = OUTPUTS_DIR / f"{event.schedule_event_id}.json"
                    out_file.write_text(
                        json.dumps(output, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    logger.info(
                        f"[Scheduler] {event.schedule_event_id} → READY_TO_PUBLISH "
                        f"| saved to {out_file}"
                    )
            finally:
                db.close()
        except Exception as e:
            logger.error(f"[Scheduler] tick error: {e}")

        await asyncio.sleep(TICK_INTERVAL)
