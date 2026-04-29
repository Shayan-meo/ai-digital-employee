"""
Filesystem Watcher — Monitors /Inbox for new .md files.
When a .md file lands in /Inbox, moves it to /Needs_Action for processing.
Part of the Personal AI Employee vault pipeline (Silver Tier).
"""

import time
import shutil
import logging
from pathlib import Path
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Resolve paths relative to this script's location
VAULT_ROOT = Path(__file__).parent.resolve()
INBOX      = VAULT_ROOT / "Inbox"
NEEDS_ACTION = VAULT_ROOT / "Needs_Action"
LOG_DIR    = VAULT_ROOT / "Logs"

# Ensure directories exist
INBOX.mkdir(exist_ok=True)
NEEDS_ACTION.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Configure logging
log_file = LOG_DIR / f"filesystem_watcher_{datetime.now().strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class InboxHandler(FileSystemEventHandler):
    """Watches /Inbox and moves .md files to /Needs_Action."""

    def on_created(self, event):
        if event.is_directory:
            return

        try:
            source = Path(event.src_path)

            # Small delay to ensure file is fully written
            time.sleep(0.5)

            if not source.exists():
                return

            # Only process .md files
            if source.suffix.lower() != ".md":
                logger.info(f"Ignored non-.md file: {source.name}")
                return

            logger.info(f"New inbox file detected: {source.name}")

            # Resolve destination — avoid overwriting existing files
            dest = NEEDS_ACTION / source.name
            if dest.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dest = NEEDS_ACTION / f"{source.stem}_{timestamp}{source.suffix}"

            shutil.move(str(source), str(dest))
            logger.info(f"Moved {source.name} -> Needs_Action/{dest.name}")

            # Append move record to today's task log
            task_log = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}_task_log.md"
            with open(task_log, "a", encoding="utf-8") as f:
                f.write(
                    f"\n### Task: {source.name}\n"
                    f"- **Time:** {datetime.now().strftime('%H:%M:%S')}\n"
                    f"- **Pipeline:** Inbox -> Needs_Action/{dest.name}\n"
                    f"- **Status:** Queued for processing\n"
                )

        except Exception as e:
            logger.error(f"Error processing {event.src_path}: {e}")


def main():
    logger.info("Filesystem Watcher starting...")
    logger.info(f"Watching: {INBOX}")

    event_handler = InboxHandler()
    observer = Observer()
    observer.schedule(event_handler, str(INBOX), recursive=False)
    observer.start()

    logger.info("Filesystem Watcher running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutdown signal received. Stopping watcher...")
        observer.stop()

    observer.join()
    logger.info("Filesystem Watcher stopped.")


if __name__ == "__main__":
    main()
