"""
APScheduler setup — scheduled lifecycle jobs (Section 21.7, Feature S).
"""
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.database import SessionLocal
from app.services import lifecycle_service, matching_service, return_service
from app.services import drop_off_lifecycle_service, token_service, redemption_service

_scheduler: BackgroundScheduler | None = None


def _run_hourly_lifecycle_job() -> None:
    db = SessionLocal()
    try:
        expired_items = lifecycle_service.expire_items_past_deadline(db)
        expired_matches = matching_service.expire_stale_potential_matches(db)
        drop_off_counts = drop_off_lifecycle_service.process_drop_off_lifecycle(db)
        if expired_items or expired_matches or any(drop_off_counts.values()):
            db.commit()
            print(
                f"[Scheduler] Hourly: expired_items={expired_items}, "
                f"stale_matches={expired_matches}, drop_off={drop_off_counts}",
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
        archived_returns = lifecycle_service.archive_completed_returns(db)
        disputes_closed = lifecycle_service.close_expired_dispute_windows(db)
        queued = lifecycle_service.queue_eligible_items_for_deletion(db)
        resumed = lifecycle_service.resume_paused_matches_on_resolved_disputes(db)
        return_reminders = return_service.process_return_reminders(db)
        escrow_warnings = token_service.warn_expiring_escrows(db)
        expired_escrows = token_service.expire_stale_escrows(db)
        redemption_warnings = redemption_service.warn_expiring_redemption_codes(db)
        expired_redemptions = redemption_service.expire_stale_redemption_codes(db)
        if any(
            (
                reminders,
                archived_returns,
                disputes_closed,
                queued,
                resumed,
                return_reminders,
                escrow_warnings,
                expired_escrows,
                redemption_warnings,
                expired_redemptions,
            )
        ):
            db.commit()
            print(
                "[Scheduler] Daily: "
                f"expiry_reminders={reminders}, archived_returns={archived_returns}, "
                f"dispute_status_fixes={disputes_closed}, deletion_queued={queued}, "
                f"matches_resumed={resumed}, return_reminders={return_reminders}, "
                f"escrow_warnings={escrow_warnings}, expired_escrows={expired_escrows}, "
                f"redemption_warnings={redemption_warnings}, expired_redemptions={expired_redemptions}",
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
        "[Scheduler] APScheduler started — hourly item/match expiry + drop-off lifecycle, "
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
    from app.services import matching_service

    model = matching_service.load_sentence_model_at_startup()
    app.state.model = model
    matching_service.set_app_sentence_model(model)
    start_scheduler()
    yield
    stop_scheduler()
