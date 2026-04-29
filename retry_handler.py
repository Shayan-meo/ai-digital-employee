"""
Retry Handler — Gold/Platinum Tier
Exponential backoff retry utility + /Queue fallback for graceful degradation.

Features:
- Exponential backoff: 1s → 2s → 4s → 8s → ... → max 60s
- Max retry limit (default 5)
- On final failure: queue task to /Queue for later processing
- Queue processor: periodically retries queued tasks
- Shared utility — all watchers and agents import this

Usage:
    from retry_handler import retry_with_backoff, queue_failed_task, process_queue

    # Wrap any unreliable function
    result = retry_with_backoff(lambda: call_gmail_api(), task_name="gmail_fetch")

    # Or use as decorator
    @retryable(max_retries=3)
    def send_email():
        ...

    # Process queued tasks (run via scheduler)
    python retry_handler.py --process-queue
"""

import argparse
import json
import logging
import shutil
import time
import traceback
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable

VAULT_ROOT = Path(__file__).parent.resolve()
QUEUE_DIR = VAULT_ROOT / "Queue"
LOGS_DIR = VAULT_ROOT / "Logs"
NEEDS_ACTION = VAULT_ROOT / "Needs_Action"

QUEUE_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("retry_handler")
if not logger.handlers:
    log_file = LOGS_DIR / f"retry_handler_{datetime.now().strftime('%Y-%m-%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_MAX_RETRIES = 5
DEFAULT_BASE_DELAY = 1.0    # seconds
DEFAULT_MAX_DELAY = 60.0    # seconds cap
DEFAULT_BACKOFF_FACTOR = 2.0


# ── Core retry function ──────────────────────────────────────────────────────
def retry_with_backoff(
    func: Callable,
    task_name: str = "unknown",
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    queue_on_failure: bool = True,
    task_file: Path | None = None,
) -> Any:
    """
    Execute func with exponential backoff retries.
    On final failure, optionally queue the task for later processing.

    Returns: func result on success, None on failure.
    """
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            result = func()
            if attempt > 1:
                logger.info(f"[{task_name}] Succeeded on attempt {attempt}/{max_retries}")
            return result
        except Exception as e:
            last_error = e
            delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)

            logger.warning(
                f"[{task_name}] Attempt {attempt}/{max_retries} failed: {e}. "
                f"Retrying in {delay:.1f}s..."
            )

            if attempt < max_retries:
                time.sleep(delay)

    # All retries exhausted
    logger.error(
        f"[{task_name}] All {max_retries} retries failed. Last error: {last_error}"
    )

    if queue_on_failure:
        queue_failed_task(
            task_name=task_name,
            error=str(last_error),
            task_file=task_file,
            retries_exhausted=max_retries,
        )

    return None


# ── Decorator version ─────────────────────────────────────────────────────────
def retryable(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    queue_on_failure: bool = True,
):
    """Decorator: wrap a function with exponential backoff retry logic."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return retry_with_backoff(
                func=lambda: func(*args, **kwargs),
                task_name=func.__name__,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                queue_on_failure=queue_on_failure,
            )
        return wrapper
    return decorator


# ── Queue management ──────────────────────────────────────────────────────────
def queue_failed_task(
    task_name: str,
    error: str,
    task_file: Path | None = None,
    retries_exhausted: int = 0,
):
    """Queue a failed task to /Queue for later retry."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    queue_entry = {
        "task_name": task_name,
        "queued_at": datetime.now().isoformat(),
        "error": error,
        "retries_exhausted": retries_exhausted,
        "original_file": str(task_file) if task_file else None,
        "status": "queued",
        "retry_count": 0,
    }

    queue_file = QUEUE_DIR / f"queued_{ts}_{task_name}.json"
    queue_file.write_text(json.dumps(queue_entry, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"[{task_name}] Queued for later retry: {queue_file.name}")

    # If there's an original task file, copy it to Queue as well
    if task_file and task_file.exists():
        backup = QUEUE_DIR / f"queued_{ts}_{task_file.name}"
        shutil.copy2(task_file, backup)
        logger.info(f"[{task_name}] Task file backed up: {backup.name}")

    # Log to audit
    try:
        from audit_logger import audit_log
        audit_log("queue", "retry_handler", {
            "task_name": task_name,
            "error": error,
            "retries": retries_exhausted,
        }, "queued", f"Task queued after {retries_exhausted} failed retries")
    except ImportError:
        pass

    return queue_file


def process_queue(max_per_run: int = 10) -> dict:
    """
    Process queued tasks — move them back to /Needs_Action for reprocessing.
    Run this periodically via scheduler.

    Returns: {"processed": N, "failed": N, "remaining": N}
    """
    queue_files = sorted(QUEUE_DIR.glob("queued_*.json"))
    stats = {"processed": 0, "failed": 0, "remaining": 0}

    if not queue_files:
        logger.info("Queue is empty — nothing to process.")
        return stats

    logger.info(f"Processing queue: {len(queue_files)} item(s)")

    for qf in queue_files[:max_per_run]:
        try:
            entry = json.loads(qf.read_text(encoding="utf-8"))
            task_name = entry.get("task_name", "unknown")
            original_file = entry.get("original_file")

            # If original task file was backed up, move it to Needs_Action
            if original_file:
                backup_candidates = list(QUEUE_DIR.glob(f"queued_*_{Path(original_file).name}"))
                for backup in backup_candidates:
                    if backup.suffix != ".json":
                        dest = NEEDS_ACTION / backup.name.split("_", 3)[-1]  # strip prefix
                        shutil.move(str(backup), str(dest))
                        logger.info(f"[{task_name}] Moved back to Needs_Action: {dest.name}")

            # Update entry status
            entry["status"] = "requeued"
            entry["retry_count"] = entry.get("retry_count", 0) + 1
            entry["requeued_at"] = datetime.now().isoformat()

            # Archive the queue entry
            done_file = QUEUE_DIR / f"done_{qf.name}"
            done_file.write_text(json.dumps(entry, indent=2), encoding="utf-8")
            qf.unlink()

            stats["processed"] += 1
            logger.info(f"[{task_name}] Requeued for processing (attempt #{entry['retry_count']})")

        except Exception as e:
            logger.error(f"Failed to process queue item {qf.name}: {e}")
            stats["failed"] += 1

    stats["remaining"] = len(queue_files) - stats["processed"] - stats["failed"]
    logger.info(f"Queue processing done: {stats}")

    # Audit log
    try:
        from audit_logger import audit_log
        audit_log("queue_process", "retry_handler", stats, "success",
                  f"Processed {stats['processed']} queued tasks")
    except ImportError:
        pass

    return stats


def get_queue_status() -> dict:
    """Get current queue status for Dashboard."""
    queue_files = list(QUEUE_DIR.glob("queued_*.json"))
    entries = []
    for qf in queue_files:
        try:
            entry = json.loads(qf.read_text(encoding="utf-8"))
            entries.append({
                "task": entry.get("task_name"),
                "queued_at": entry.get("queued_at"),
                "error": entry.get("error", "")[:100],
                "retries": entry.get("retry_count", 0),
            })
        except Exception:
            pass

    return {
        "queue_size": len(queue_files),
        "tasks": entries,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Retry Handler & Queue Processor")
    parser.add_argument("--process-queue", action="store_true", help="Process queued tasks")
    parser.add_argument("--status", action="store_true", help="Show queue status")
    parser.add_argument("--test", action="store_true", help="Test retry logic")
    args = parser.parse_args()

    if args.process_queue:
        result = process_queue()
        print(json.dumps(result, indent=2))

    elif args.status:
        status = get_queue_status()
        print(json.dumps(status, indent=2))

    elif args.test:
        # Demo: function that fails 3 times then succeeds
        counter = {"n": 0}
        def flaky_api():
            counter["n"] += 1
            if counter["n"] < 4:
                raise ConnectionError(f"API timeout (attempt {counter['n']})")
            return {"status": "ok", "data": "success"}

        result = retry_with_backoff(flaky_api, task_name="test_api", max_retries=5, base_delay=0.5)
        print(f"Result: {result}")

        # Demo: function that always fails → gets queued
        def always_fails():
            raise TimeoutError("Service unavailable")

        result = retry_with_backoff(always_fails, task_name="dead_service", max_retries=3, base_delay=0.5)
        print(f"Result (should be None): {result}")
        print(f"Queue status: {json.dumps(get_queue_status(), indent=2)}")

    else:
        parser.print_help()
