"""
APScheduler setup — scheduled lifecycle jobs (Section 21.7).

Feature I wires the hourly POTENTIAL_MATCH timeout job.
Feature S will add remaining jobs (expiry reminders, etc.).
"""
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.database import SessionLocal
from app.services import verification_service

_scheduler: BackgroundScheduler | None = None


def _run_match_timeout_job() -> None:
    db = SessionLocal()
    try:
        count = verification_service.expire_stale_potential_matches(db)
        if count:
            print(f"[Scheduler] Expired {count} stale POTENTIAL_MATCH record(s)", flush=True)
    except Exception as exc:
        print(f"[Scheduler] match timeout job failed: {exc}", flush=True)
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        _run_match_timeout_job,
        trigger=IntervalTrigger(hours=1),
        id="expire_stale_potential_matches",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
    print("[Scheduler] APScheduler started — hourly POTENTIAL_MATCH timeout active", flush=True)
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
