"""
Scheduler — Cron-style task scheduler for the AI Employee vault.
Runs periodic jobs: Gmail polling, daily dashboard summaries.
Part of the Silver Tier.

Usage:
    python scheduler.py
"""

import logging
import time
from pathlib import Path
from datetime import datetime

import schedule

# Resolve paths relative to this script's location
VAULT_ROOT = Path(__file__).parent.resolve()
NEEDS_ACTION = VAULT_ROOT / "Needs_Action"
LOG_DIR = VAULT_ROOT / "Logs"

# Ensure directories exist
NEEDS_ACTION.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Configure logging
log_file = LOG_DIR / f"scheduler_{datetime.now().strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def job_gmail_check():
    """Trigger a Gmail check cycle by importing and running gmail_watcher."""
    logger.info("Scheduled job: Gmail check")
    try:
        from gmail_watcher import poll_cycle
        count = poll_cycle()
        logger.info(f"Gmail check complete: {count} new email(s)")
    except Exception as e:
        logger.error(f"Gmail check failed: {e}")


def job_ceo_briefing():
    """Generate weekly CEO briefing every Sunday at 22:00."""
    logger.info("Scheduled job: CEO Briefing (Gold Tier)")
    try:
        from ceo_briefing import build_briefing
        path = build_briefing()
        logger.info(f"CEO Briefing generated: {path.name}")
    except Exception as e:
        logger.error(f"CEO Briefing failed: {e}")


def job_daily_summary():
    """Create a daily dashboard summary task in Needs_Action."""
    logger.info("Scheduled job: Daily summary")
    today = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Count files in each folder
    folders = {
        "Inbox": VAULT_ROOT / "Inbox",
        "Needs_Action": NEEDS_ACTION,
        "Pending_Approval": VAULT_ROOT / "Pending_Approval",
        "Approved": VAULT_ROOT / "Approved",
        "Done": VAULT_ROOT / "Done",
        "Plans": VAULT_ROOT / "Plans",
    }

    counts = {}
    for name, path in folders.items():
        if path.exists():
            counts[name] = len(list(path.iterdir()))
        else:
            counts[name] = 0

    summary_content = f"""# Daily Summary Task

## Date: {today}
## Source: Scheduler (auto-generated)
## Type: Dashboard Update

## Vault Status Snapshot
| Folder | File Count |
|--------|-----------|
"""
    for name, count in counts.items():
        summary_content += f"| {name} | {count} |\n"

    summary_content += f"""
## Action Required
Update Dashboard.md with today's status and any notable activity.
"""

    filename = f"daily_summary_{timestamp}.md"
    filepath = NEEDS_ACTION / filename
    filepath.write_text(summary_content, encoding="utf-8")
    logger.info(f"Created daily summary task: {filename}")


def main():
    logger.info("=" * 60)
    logger.info("Scheduler starting")
    logger.info(f"Vault root: {VAULT_ROOT}")
    logger.info("=" * 60)

    # Schedule jobs
    schedule.every(5).minutes.do(job_gmail_check)
    schedule.every().day.at("09:00").do(job_daily_summary)
    schedule.every().sunday.at("22:00").do(job_ceo_briefing)

    logger.info("Scheduled jobs:")
    logger.info("  - Gmail check: every 5 minutes")
    logger.info("  - Daily summary: every day at 09:00")
    logger.info("  - CEO Briefing: every Sunday at 22:00 (Gold Tier)")

    # Run daily summary immediately on start for demo
    logger.info("Running initial daily summary...")
    job_daily_summary()

    logger.info("Scheduler running. Press Ctrl+C to stop.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user.")


if __name__ == "__main__":
    main()
