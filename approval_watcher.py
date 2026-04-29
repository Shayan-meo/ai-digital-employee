"""
Approval Watcher — Monitors /Approved folder for human-approved tasks.
- If file starts with 'reply_': sends the email via Gmail API, then moves to /Done
- All other files: creates an execution task in /Needs_Action
Part of the Personal AI Employee vault pipeline (Silver Tier).
"""

import time
import json
import shutil
import logging
import re
from pathlib import Path
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64

# ── Paths ──────────────────────────────────────────────────────────────────────
VAULT_ROOT       = Path(__file__).parent.resolve()
APPROVED         = VAULT_ROOT / "Approved"
NEEDS_ACTION     = VAULT_ROOT / "Needs_Action"
DONE             = VAULT_ROOT / "Done"
LOG_DIR          = VAULT_ROOT / "Logs"
CREDS_FILE       = VAULT_ROOT / "gmail_credentials" / "credentials.json"

for d in [APPROVED, NEEDS_ACTION, DONE, LOG_DIR]:
    d.mkdir(exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────────────
log_file = LOG_DIR / f"approval_watcher_{datetime.now().strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ── Gmail API ──────────────────────────────────────────────────────────────────

def get_gmail_service():
    creds_data = json.loads(CREDS_FILE.read_text(encoding="utf-8"))
    creds = Credentials(
        token=None,
        refresh_token=creds_data["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds_data["client_id"],
        client_secret=creds_data["client_secret"],
        scopes=["https://mail.google.com/"],
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def send_email(service, to: str, subject: str, body: str, thread_id: str = None):
    """Send an email via Gmail API. Returns message id."""
    mime = MIMEText(body, "plain")
    mime["To"]      = to
    mime["Subject"] = subject

    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    message = {"raw": raw}
    if thread_id:
        message["threadId"] = thread_id

    sent = service.users().messages().send(userId="me", body=message).execute()
    return sent.get("id")


# ── Reply file parser ──────────────────────────────────────────────────────────

def parse_reply_file(content: str):
    """Extract To, Subject, Gmail ID, and reply body from a reply draft .md file."""

    def get_field(label):
        m = re.search(rf"\*\*{label}:\*\*\s*(.+)", content)
        return m.group(1).strip() if m else ""

    to       = get_field("To")
    subject  = get_field("Subject")
    gmail_id = get_field("Gmail ID")

    # Extract text inside the ```...``` block
    body_match = re.search(r"## Drafted Reply\s*```\s*(.*?)```", content, re.DOTALL)
    body = body_match.group(1).strip() if body_match else ""

    return to, subject, body, gmail_id


# ── Handler ────────────────────────────────────────────────────────────────────

class ApprovalHandler(FileSystemEventHandler):

    def on_created(self, event):
        if event.is_directory:
            return

        source = Path(event.src_path)
        time.sleep(0.5)  # wait for file to be fully written

        if not source.exists():
            return

        logger.info(f"Approved file detected: {source.name}")

        try:
            if source.name.startswith("reply_"):
                self._handle_reply(source)
            elif any(p in source.name for p in (
                "facebook_post_", "linkedin_post_", "whatsapp_", "instagram_post_", "twitter_post_"
            )):
                # Social media / messaging files are handled by their own playwright watchers
                # Leave them in /Approved — do not move or re-queue
                logger.info(f"Social/messaging file — leaving for dedicated watcher: {source.name}")
            else:
                self._handle_generic(source)
        except Exception as e:
            logger.error(f"Error processing {source.name}: {e}")

    # ── Reply email sending ────────────────────────────────────────────────────

    def _handle_reply(self, source: Path):
        content  = source.read_text(encoding="utf-8")
        to, subject, body, gmail_id = parse_reply_file(content)

        if not to or not body:
            logger.error(f"Could not parse reply file — missing To or body: {source.name}")
            return

        logger.info(f"Sending email to: {to} | Subject: {subject}")

        try:
            service   = get_gmail_service()

            # Get thread_id from original email so reply is in same thread
            thread_id = None
            if gmail_id:
                try:
                    orig = service.users().messages().get(
                        userId="me", id=gmail_id, format="minimal"
                    ).execute()
                    thread_id = orig.get("threadId")
                except Exception:
                    pass

            sent_id = send_email(service, to, subject, body, thread_id)
            logger.info(f"Email sent successfully! Message ID: {sent_id}")

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return

        # Log the action
        self._write_log(source.name, f"Email sent to {to} | Subject: {subject}")

        # Move to Done
        self._move_to_done(source, prefix="sent_email_")
        logger.info(f"Reply file archived to /Done")

    # ── Generic approved task ──────────────────────────────────────────────────

    def _handle_generic(self, source: Path):
        content   = source.read_text(encoding="utf-8")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        task_filename = f"approved_{timestamp}_{source.stem}.md"
        task_path     = NEEDS_ACTION / task_filename
        task_path.write_text(
            f"# Approved Task — Ready for Execution\n\n"
            f"## Approval Metadata\n"
            f"- **Original File:** {source.name}\n"
            f"- **Approved At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- **Status:** HUMAN APPROVED — Safe to execute\n\n"
            f"## Original Content\n{content}\n\n"
            f"## Instructions\n"
            f"This task has been reviewed and approved by a human.\n"
            f"Execute the requested action as described above.\n",
            encoding="utf-8",
        )
        logger.info(f"Created execution task: Needs_Action/{task_filename}")
        self._write_log(source.name, f"Generic approved task queued -> Needs_Action/{task_filename}")
        self._move_to_done(source, prefix="approved_")

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _move_to_done(self, source: Path, prefix: str = ""):
        dest = DONE / f"{prefix}{source.name}"
        if dest.exists():
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = DONE / f"{prefix}{ts}_{source.name}"
        shutil.move(str(source), str(dest))

    def _write_log(self, filename: str, note: str):
        task_log = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}_task_log.md"
        with open(task_log, "a", encoding="utf-8") as f:
            f.write(
                f"\n### Approved: {filename}\n"
                f"- **Time:** {datetime.now().strftime('%H:%M:%S')}\n"
                f"- **Action:** {note}\n"
            )


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    logger.info("=" * 60)
    logger.info("Approval Watcher starting")
    logger.info(f"Vault root: {VAULT_ROOT}")
    logger.info(f"Watching:   {APPROVED}")
    logger.info("=" * 60)

    observer = Observer()
    observer.schedule(ApprovalHandler(), str(APPROVED), recursive=False)
    observer.start()

    logger.info("Approval Watcher running. Move reply files to /Approved to send.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Approval Watcher stopped by user.")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
