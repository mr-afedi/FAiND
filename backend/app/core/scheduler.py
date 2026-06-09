"""
APScheduler setup — scheduled lifecycle jobs (Section 21.7, Feature S).
"""
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.database import SessionLocal
from app.services import lifecycle_service, return_service, verification_service

_scheduler: BackgroundScheduler | None = None


def _run_hourly_lifecycle_job() -> None:
    db = SessionLocal()
    try:
        expired_items = lifecycle_service.expire_items_past_deadline(db)
        expired_matches = verification_service.expire_stale_potential_matches(db)
        if expired_items or expired_matches:
            print(
                f"[Scheduler] Hourly: expired_items={expired_items}, "
                f"stale_matches={expired_matches}",
                flush=True,
            )
    except Exception as exc:
        print(f"[Scheduler] hourly lifecycle job failed: {exc}", flush=True)
        db.rollback()
    finally:
        db.close()


def _run_daily_midnight_lifecycle_job() -> None:
    db = SessionLocal()
    try:
        reminders = lifecycle_service.send_expiry_reminders(db)
        tipping_closed = lifecycle_service.close_expired_tipping_windows(db)
        disputes_closed = lifecycle_service.close_expired_dispute_windows(db)
        queued = lifecycle_service.queue_eligible_items_for_deletion(db)
        resumed = lifecycle_service.resume_paused_matches_on_resolved_disputes(db)
        return_reminders = return_service.process_return_reminders(db)
        if any(
            (
                reminders,
                tipping_closed,
                disputes_closed,
                queued,
                resumed,
                return_reminders,
            )
        ):
            print(
                "[Scheduler] Daily: "
                f"expiry_reminders={reminders}, tipping_archived={tipping_closed}, "
                f"dispute_status_fixes={disputes_closed}, deletion_queued={queued}, "
                f"matches_resumed={resumed}, return_reminders={return_reminders}",
                flush=True,
            )
    except Exception as exc:
        print(f"[Scheduler] daily lifecycle job failed: {exc}", flush=True)
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        _run_hourly_lifecycle_job,
        trigger=IntervalTrigger(hours=1),
        id="hourly_lifecycle",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_daily_midnight_lifecycle_job,
        trigger=CronTrigger(hour=0, minute=0),
        id="daily_midnight_lifecycle",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    print(
        "[Scheduler] APScheduler started — hourly item/match expiry, "
        "daily midnight lifecycle (reminders, windows, deletion queue)",
        flush=True,
    )
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


@asynccontextmanager
async def scheduler_lifespan(app):
    start_scheduler()
    yield
    stop_scheduler()
