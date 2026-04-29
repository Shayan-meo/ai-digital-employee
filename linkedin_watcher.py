"""
LinkedIn Watcher — Monitors /Needs_Action for LinkedIn post tasks.
Automatically drafts and queues LinkedIn posts for business updates.
Part of the Personal AI Employee vault pipeline (Silver Tier).

Usage:
    python linkedin_watcher.py

Environment Variables (set in .env):
    LINKEDIN_EMAIL    — Your LinkedIn email
    LINKEDIN_PASSWORD — Your LinkedIn password
"""

import subprocess
import logging
import time
import os
from pathlib import Path
from datetime import datetime

# Resolve paths relative to this script's location
VAULT_ROOT = Path(__file__).parent.resolve()
NEEDS_ACTION = VAULT_ROOT / "Needs_Action"
PENDING_APPROVAL = VAULT_ROOT / "Pending_Approval"
DONE = VAULT_ROOT / "Done"
LOG_DIR = VAULT_ROOT / "Logs"

# Ensure directories exist
NEEDS_ACTION.mkdir(exist_ok=True)
PENDING_APPROVAL.mkdir(exist_ok=True)
DONE.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Configure logging
log_file = LOG_DIR / f"linkedin_watcher_{datetime.now().strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Poll interval in seconds (2 minutes)
POLL_INTERVAL = 120

# Keywords that identify a LinkedIn post task
LINKEDIN_KEYWORDS = ["linkedin", "post", "publish", "announcement", "update", "share"]


def call_claude_mcp(prompt):
    """Call claude CLI with a prompt (uses LinkedIn MCP) and return the text output."""
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(VAULT_ROOT),
        )
        if result.returncode != 0:
            logger.error(f"Claude CLI error: {result.stderr}")
            return None
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error("Claude CLI timed out")
        return None
    except FileNotFoundError:
        logger.error("Claude CLI not found — make sure 'claude' is on PATH")
        return None


def is_linkedin_task(content: str) -> bool:
    """Return True if the task file is a LinkedIn post request."""
    content_lower = content.lower()
    return any(kw in content_lower for kw in LINKEDIN_KEYWORDS)


def draft_linkedin_post(task_content: str) -> str:
    """Use Claude MCP to draft a LinkedIn post from the task content."""
    prompt = f"""Using the LinkedIn MCP tools available to you, draft a professional LinkedIn post based on the following task:

{task_content}

Write a compelling, professional LinkedIn post (150-300 words) that:
- Has an engaging opening line
- Shares the key update/announcement clearly
- Uses relevant hashtags (3-5)
- Ends with a call to action or question

Return ONLY the post text, ready to publish."""

    logger.info("Drafting LinkedIn post via Claude MCP...")
    post_text = call_claude_mcp(prompt)
    if not post_text:
        # Fallback: create a simple draft without MCP
        post_text = f"[AUTO-DRAFT — Review before posting]\n\n{task_content[:500]}\n\n#AI #Automation #Business"
    return post_text


def create_approval_request(source_file: Path, post_draft: str, original_content: str):
    """Create a Pending_Approval file for human review before posting."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    approval_filename = f"linkedin_post_{timestamp}_{source_file.stem}.md"
    approval_path = PENDING_APPROVAL / approval_filename

    approval_content = f"""# LinkedIn Post — Pending Approval

## Metadata
- **Source Task:** {source_file.name}
- **Created At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Action Required:** Review and approve LinkedIn post before publishing
- **Watcher:** LinkedIn Watcher (Silver Tier)

## Drafted Post
> To publish this post, move this file to `/Approved`
> To reject, delete this file or move to `/Done` with a rejection note

```
{post_draft}
```

## Original Task
{original_content}

## Instructions for Human
1. Review the drafted post above
2. Edit the post text if needed (modify the block between the ``` markers)
3. Move this file to `/Approved` to publish, or delete to cancel
"""

    approval_path.write_text(approval_content, encoding="utf-8")
    logger.info(f"Approval request created: {approval_filename}")
    return approval_path


def archive_task(source_file: Path, status: str, note: str):
    """Move processed task to /Done with completion metadata."""
    done_path = DONE / source_file.name
    # Handle name collisions
    if done_path.exists():
        stem = source_file.stem
        suffix = source_file.suffix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        done_path = DONE / f"{stem}_{timestamp}{suffix}"

    content = source_file.read_text(encoding="utf-8")
    content += f"""

---
## LinkedIn Watcher — Processing Complete
- **Status:** {status}
- **Processed At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Note:** {note}
"""
    done_path.write_text(content, encoding="utf-8")
    source_file.unlink()
    logger.info(f"Task archived to Done: {done_path.name}")


def poll_cycle():
    """Scan /Needs_Action for LinkedIn post tasks and process them."""
    processed = 0

    if not NEEDS_ACTION.exists():
        return 0

    for task_file in sorted(NEEDS_ACTION.glob("*.md")):
        try:
            content = task_file.read_text(encoding="utf-8")

            if not is_linkedin_task(content):
                continue

            logger.info(f"LinkedIn task detected: {task_file.name}")

            # Draft the post
            post_draft = draft_linkedin_post(content)

            # Route to Pending_Approval (always — posting is a sensitive action)
            create_approval_request(task_file, post_draft, content)

            # Archive original task
            archive_task(
                task_file,
                status="PENDING_APPROVAL",
                note="LinkedIn post drafted and sent to /Pending_Approval for human review",
            )

            logger.info(f"LinkedIn post queued for approval: {task_file.name}")
            processed += 1

        except Exception as e:
            logger.error(f"Error processing {task_file.name}: {e}")

    return processed


def run():
    """Main loop — polls /Needs_Action every POLL_INTERVAL seconds."""
    logger.info("LinkedIn Watcher started (Silver Tier)")
    logger.info(f"Watching: {NEEDS_ACTION}")
    logger.info(f"Poll interval: {POLL_INTERVAL}s")

    # Check credentials
    email = os.environ.get("LINKEDIN_EMAIL", "")
    password = os.environ.get("LINKEDIN_PASSWORD", "")
    if not email or not password:
        logger.warning(
            "LINKEDIN_EMAIL or LINKEDIN_PASSWORD not set in environment. "
            "Post drafting will work but MCP posting tools may not authenticate. "
            "Set these in your .env file."
        )

    while True:
        try:
            count = poll_cycle()
            if count:
                logger.info(f"Poll complete: {count} LinkedIn task(s) processed")
            else:
                logger.debug("Poll complete: no LinkedIn tasks found")
        except Exception as e:
            logger.error(f"Poll cycle error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run()
