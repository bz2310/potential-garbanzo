"""Scheduler — run scans at 7 AM and 5 PM EST."""

from __future__ import annotations

import logging
import signal
import sys
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from outlook.pipeline import run_scan_pipeline

logger = logging.getLogger(__name__)


def start_scheduler(project_root: Path) -> None:
    scheduler = BlockingScheduler()

    # 7 AM EST
    scheduler.add_job(
        run_scan_pipeline,
        CronTrigger(hour=7, minute=0, timezone="US/Eastern"),
        args=[project_root, "AM"],
        id="morning_scan",
        name="Morning scan (7 AM EST)",
    )

    # 5 PM EST
    scheduler.add_job(
        run_scan_pipeline,
        CronTrigger(hour=17, minute=0, timezone="US/Eastern"),
        args=[project_root, "PM"],
        id="evening_scan",
        name="Evening scan (5 PM EST)",
    )

    def shutdown(signum, frame):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info("Scheduler started. Scans at 7 AM and 5 PM EST.")
    logger.info("Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
