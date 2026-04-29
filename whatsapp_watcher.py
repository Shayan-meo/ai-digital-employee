"""
WhatsApp Watcher — Monitors /Needs_Action for WhatsApp message tasks.
Detects WhatsApp-related tasks and routes them to /Pending_Approval.
Part of the Personal AI Employee vault pipeline (Gold Tier).

Usage:
    python whatsapp_watcher.py
    python whatsapp_watcher.py --watch
"""

import argparse
import logging
import re
import time
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
VAULT_ROOT       = Path(__file__).parent.resolve()
NEEDS_ACTION     = VAULT_ROOT / "Needs_Action"
PENDING_APPROVAL = VAULT_ROOT / "Pending_Approval"
DONE             = VAULT_ROOT / "Done"
LOG_DIR          = VAULT_ROOT / "Logs"

for d in (NEEDS_ACTION, PENDING_APPROVAL, DONE, LOG_DIR):
    d.mkdir(exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────────────
log_file = LOG_DIR / f"whatsapp_watcher_{datetime.now().strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 60  # seconds

# ── WhatsApp task detection ────────────────────────────────────────────────────
WHATSAPP_KEYWORDS = ["whatsapp", "wa message", "send whatsapp", "whatsapp message"]


def is_whatsapp_task(content: str) -> bool:
    content_lower = content.lower()
    return any(kw in content_lower for kw in WHATSAPP_KEYWORDS)


def extract_recipient(content: str) -> str:
    """Try to extract a phone number or contact name from the task."""
    # Phone number pattern
    match = re.search(r"(\+?\d[\d\s\-]{8,15})", content)
    if match:
        return match.group(1).strip()
    # After "to:" or "recipient:"
    match = re.search(r"(?:to|recipient|send to|contact)\s*[:\-]\s*(.+)", content, re.IGNORECASE)
    if match:
        return match.group(1).strip().splitlines()[0].strip()
    return "(specify recipient)"


def extract_message(content: str) -> str:
    """Extract the message body from the task."""
    # Between ``` markers
    match = re.search(r"```\s*\n(.*?)\n```", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    # After "message:" header
    match = re.search(r"(?:message|body|text)\s*[:\-]\s*(.+?)(?:\n##|\Z)", content, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return "(specify message)"


# ── Approval file creator ──────────────────────────────────────────────────────
def create_approval_file(source_file: Path, recipient: str, message: str, original: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"whatsapp_{ts}_{source_file.stem}.md"
    path = PENDING_APPROVAL / filename

    content = f"""# WhatsApp Message — Pending Approval

## Metadata
- **Source Task:** {source_file.name}
- **Created At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Watcher:** WhatsApp Watcher (Gold Tier)

## Instructions
1. Review the message below
2. Edit recipient/message if needed
3. Move this file to `/Approved` to send, or delete to cancel

## To
{recipient}

## Message
```
{message}
```

## Original Task
{original}
"""
    path.write_text(content, encoding="utf-8")
    logger.info(f"Approval file created: Pending_Approval/{filename}")
    return path


def archive_task(source_file: Path):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    done_path = DONE / source_file.name
    if done_path.exists():
        done_path = DONE / f"{source_file.stem}_{ts}{source_file.suffix}"

    content = source_file.read_text(encoding="utf-8")
    content += f"""

---
## WhatsApp Watcher — Processing Complete
- **Processed At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Status:** Draft created in /Pending_Approval
"""
    done_path.write_text(content, encoding="utf-8")
    source_file.unlink()
    logger.info(f"Task archived: Done/{done_path.name}")


# ── Poll cycle ─────────────────────────────────────────────────────────────────
def poll_cycle() -> int:
    processed = 0
    for task_file in sorted(NEEDS_ACTION.glob("*.md")):
        try:
            if task_file.name.startswith(("email_", "approved_", "daily_summary_")):
                continue

            content = task_file.read_text(encoding="utf-8")
            if not is_whatsapp_task(content):
                continue

            logger.info(f"WhatsApp task detected: {task_file.name}")

            recipient = extract_recipient(content)
            message = extract_message(content)
            create_approval_file(task_file, recipient, message, content)
            archive_task(task_file)
            processed += 1

        except Exception as e:
            logger.error(f"Error processing {task_file.name}: {e}")

    return processed


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="WhatsApp Watcher (Gold Tier)")
    parser.add_argument("--watch", action="store_true", help="Watch continuously")
    args = parser.parse_args()

    logger.info("WhatsApp Watcher started (Gold Tier)")

    if args.watch:
        logger.info(f"Watch mode — polling every {POLL_INTERVAL}s")
        while True:
            try:
                count = poll_cycle()
                if count:
                    logger.info(f"Processed {count} WhatsApp task(s)")
            except Exception as e:
                logger.error(f"Poll error: {e}")
            time.sleep(POLL_INTERVAL)
    else:
        count = poll_cycle()
        logger.info(f"Done. Processed {count} task(s).")


if __name__ == "__main__":
    main()
