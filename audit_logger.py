"""
JSON Audit Logger — Gold Tier
Logs every action to /Logs/YYYY-MM-DD.json with structured schema.
Retains logs for 90 days, auto-cleans older files.

Schema per entry:
{
    "timestamp": "ISO 8601",
    "action_type": "post | email | approval | task | watcher | login | error",
    "actor": "system | gmail_watcher | linkedin_playwright | scheduler | ...",
    "parameters": { ... },
    "result": "success | failure | queued | pending_approval",
    "details": "human-readable summary"
}

Usage:
    from audit_logger import audit_log
    audit_log("post", "linkedin_playwright", {"platform": "linkedin", "chars": 500}, "success", "Posted to LinkedIn")
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock

VAULT_ROOT = Path(__file__).parent.resolve()
LOGS_DIR = VAULT_ROOT / "Logs"
LOGS_DIR.mkdir(exist_ok=True)

RETENTION_DAYS = 90
_write_lock = Lock()


def _get_log_file() -> Path:
    return LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.json"


def _load_entries(log_file: Path) -> list:
    if log_file.exists():
        try:
            data = json.loads(log_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return []


def audit_log(
    action_type: str,
    actor: str,
    parameters: dict | None = None,
    result: str = "success",
    details: str = "",
):
    """Append a structured audit log entry to today's JSON log file."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action_type": action_type,
        "actor": actor,
        "parameters": parameters or {},
        "result": result,
        "details": details,
    }

    log_file = _get_log_file()

    with _write_lock:
        entries = _load_entries(log_file)
        entries.append(entry)
        log_file.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")

    return entry


def cleanup_old_logs():
    """Remove JSON log files older than RETENTION_DAYS."""
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    removed = 0
    for f in LOGS_DIR.glob("*.json"):
        try:
            date_str = f.stem  # e.g., "2026-01-15"
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if file_date < cutoff:
                f.unlink()
                removed += 1
        except (ValueError, OSError):
            continue
    return removed


def get_today_summary() -> dict:
    """Get summary stats from today's audit log."""
    log_file = _get_log_file()
    entries = _load_entries(log_file)

    summary = {
        "total_actions": len(entries),
        "by_type": {},
        "by_result": {},
        "by_actor": {},
    }
    for e in entries:
        t = e.get("action_type", "unknown")
        r = e.get("result", "unknown")
        a = e.get("actor", "unknown")
        summary["by_type"][t] = summary["by_type"].get(t, 0) + 1
        summary["by_result"][r] = summary["by_result"].get(r, 0) + 1
        summary["by_actor"][a] = summary["by_actor"].get(a, 0) + 1

    return summary


def get_week_entries(days: int = 7) -> list:
    """Get all audit entries from the last N days."""
    all_entries = []
    for i in range(days):
        day = datetime.now() - timedelta(days=i)
        log_file = LOGS_DIR / f"{day.strftime('%Y-%m-%d')}.json"
        all_entries.extend(_load_entries(log_file))
    return all_entries


if __name__ == "__main__":
    # Demo / test
    audit_log("test", "audit_logger", {"test": True}, "success", "Audit logger test entry")
    audit_log("post", "linkedin_playwright", {"platform": "linkedin", "chars": 707}, "success", "Posted AI article to LinkedIn")
    audit_log("email", "gmail_watcher", {"from": "client@example.com", "subject": "Invoice"}, "queued", "Routed to Pending_Approval")

    print(f"Today's log: {_get_log_file()}")
    print(json.dumps(get_today_summary(), indent=2))

    cleaned = cleanup_old_logs()
    print(f"Cleaned {cleaned} old log files (>{RETENTION_DAYS} days)")
