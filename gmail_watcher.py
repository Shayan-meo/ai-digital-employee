"""
Gmail Watcher — Real-time email detection using IMAP IDLE.
Koi polling nahi — Gmail se permanent connection, email aate hi turant detect hota hai.
Creates .md task files in /Needs_Action and reply drafts in /Pending_Approval.
Part of the Personal AI Employee vault pipeline (Silver Tier).
"""

import json
import logging
import time
import re
import imaplib
import email
from email.header import decode_header
from pathlib import Path
from datetime import datetime

from imapclient import IMAPClient
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ── Paths ──────────────────────────────────────────────────────────────────────
VAULT_ROOT       = Path(__file__).parent.resolve()
NEEDS_ACTION     = VAULT_ROOT / "Needs_Action"
PENDING_APPROVAL = VAULT_ROOT / "Pending_Approval"
LOG_DIR          = VAULT_ROOT / "Logs"
STATE_FILE       = VAULT_ROOT / ".gmail_watcher_state.json"
CREDS_FILE       = VAULT_ROOT / "gmail_credentials" / "credentials.json"

for d in [NEEDS_ACTION, PENDING_APPROVAL, LOG_DIR]:
    d.mkdir(exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────────────
log_file = LOG_DIR / f"gmail_watcher_{datetime.now().strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ── Sensitive keywords ─────────────────────────────────────────────────────────
SENSITIVE_KEYWORDS = ["reply", "respond", "send", "pay", "transfer", "invoice", "urgent"]

# ── IMAP IDLE timeout (refresh every 8 min — before Gmail's 10 min limit) ──────
IDLE_TIMEOUT = 480


# ── State management ───────────────────────────────────────────────────────────

def load_state():
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            return set(data.get("processed_ids", []))
        except (json.JSONDecodeError, KeyError):
            return set()
    return set()


def save_state(processed_ids):
    STATE_FILE.write_text(
        json.dumps({"processed_ids": list(processed_ids)}, indent=2),
        encoding="utf-8",
    )


# ── Gmail API (for fetching full email body) ───────────────────────────────────

def get_gmail_service():
    creds_data = json.loads(CREDS_FILE.read_text(encoding="utf-8"))
    creds = Credentials(
        token=None,
        refresh_token=creds_data["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds_data["client_id"],
        client_secret=creds_data["client_secret"],
        scopes=[
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
        ],
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def get_access_token():
    """Get fresh OAuth access token and email address for IMAP XOAUTH2 login."""
    creds_data = json.loads(CREDS_FILE.read_text(encoding="utf-8"))
    creds = Credentials(
        token=None,
        refresh_token=creds_data["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds_data["client_id"],
        client_secret=creds_data["client_secret"],
        scopes=[
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
        ],
    )
    creds.refresh(Request())

    # Get email address from Gmail API profile
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    profile = service.users().getProfile(userId="me").execute()
    email_address = profile.get("emailAddress", "")

    return creds.token, email_address


# ── Email helpers ──────────────────────────────────────────────────────────────

def get_header(headers, name):
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def decode_body(msg):
    import base64
    def extract(payload):
        mime = payload.get("mimeType", "")
        if mime == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        if mime.startswith("multipart/"):
            for part in payload.get("parts", []):
                result = extract(part)
                if result:
                    return result
        return ""
    return extract(msg.get("payload", {})) or "(No plain text body)"


def sanitize_filename(text):
    safe = re.sub(r'[<>:"/\\|?*]', '_', text)
    safe = safe.strip('. ')
    return safe[:80] if safe else "untitled"


# ── Draft reply ────────────────────────────────────────────────────────────────

def draft_reply(subject, sender, body):
    sender_name = sender.split("<")[0].strip() or sender
    return (
        f"Hi {sender_name},\n\n"
        f"Thank you for your email regarding \"{subject}\".\n\n"
        f"I have received your message and will get back to you shortly.\n\n"
        f"Best regards,\n"
        f"Shayan\n(AI Employee — reply pending human approval)"
    )


# ── Task file creation ─────────────────────────────────────────────────────────

def create_task_file(email_data):
    msg_id   = email_data["id"]
    subject  = email_data["subject"]
    sender   = email_data["sender"]
    date     = email_data["date"]
    body     = email_data["body"]

    safe_subject = sanitize_filename(subject)
    timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    is_sensitive = any(kw in (subject + body).lower() for kw in SENSITIVE_KEYWORDS)

    # Email task → Needs_Action
    task_path = NEEDS_ACTION / f"email_{timestamp}_{safe_subject}.md"
    task_path.write_text(
        f"# Email Task\n\n"
        f"## Metadata\n"
        f"- **From:** {sender}\n"
        f"- **Subject:** {subject}\n"
        f"- **Date:** {date}\n"
        f"- **Gmail ID:** {msg_id}\n"
        f"- **Sensitive:** {'Yes — reply draft in Pending_Approval' if is_sensitive else 'No'}\n\n"
        f"## Email Body\n{body}\n\n"
        f"## Action Required\n"
        f"{'Reply draft created in /Pending_Approval — review and approve to send.' if is_sensitive else 'Informational email — no reply needed.'}\n",
        encoding="utf-8",
    )
    logger.info(f"Created email task: Needs_Action/{task_path.name}")

    # Reply draft → Pending_Approval
    reply_text = draft_reply(subject, sender, body)
    reply_path = PENDING_APPROVAL / f"reply_{timestamp}_{safe_subject}.md"
    reply_path.write_text(
        f"# Email Reply Draft — Pending Approval\n\n"
        f"## Metadata\n"
        f"- **To:** {sender}\n"
        f"- **Subject:** Re: {subject}\n"
        f"- **Original Date:** {date}\n"
        f"- **Gmail ID:** {msg_id}\n"
        f"- **Created At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"## Instructions\n"
        f"1. Review the drafted reply below\n"
        f"2. Edit if needed\n"
        f"3. Move this file to `/Approved` to send, or delete to cancel\n\n"
        f"## Drafted Reply\n\n```\n{reply_text}\n```\n\n"
        f"## Original Email\n{body}\n",
        encoding="utf-8",
    )
    logger.info(f"Created reply draft: Pending_Approval/{reply_path.name}")


# ── Process new emails via Gmail API ──────────────────────────────────────────

def process_new_emails(service, processed_ids):
    """Fetch unread emails from Gmail API and create task files."""
    try:
        results = service.users().messages().list(
            userId="me", q="is:unread newer_than:1d", maxResults=10
        ).execute()
    except Exception as e:
        logger.error(f"Gmail API error: {e}")
        return

    messages = results.get("messages", [])
    new_count = 0

    for msg_ref in messages:
        msg_id = msg_ref["id"]
        if msg_id in processed_ids:
            continue

        try:
            msg     = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
            headers = msg.get("payload", {}).get("headers", [])
            email_data = {
                "id":      msg_id,
                "subject": get_header(headers, "Subject") or "(No Subject)",
                "sender":  get_header(headers, "From")    or "Unknown",
                "date":    get_header(headers, "Date")    or "Unknown",
                "body":    decode_body(msg),
            }
            logger.info(f"New email: {email_data['subject']} | From: {email_data['sender']}")
            create_task_file(email_data)
            processed_ids.add(msg_id)
            new_count += 1
        except Exception as e:
            logger.error(f"Failed to process email {msg_id}: {e}")

    save_state(processed_ids)
    if new_count:
        logger.info(f"{new_count} new email(s) processed.")


# ── IMAP IDLE loop ─────────────────────────────────────────────────────────────

def run_imap_idle():
    """Main loop — connects via IMAP IDLE, wakes up instantly on new email."""
    processed_ids = load_state()

    while True:
        try:
            token, email_address = get_access_token()
            service = get_gmail_service()

            logger.info(f"Connecting to Gmail IMAP as {email_address}...")
            client = IMAPClient("imap.gmail.com", ssl=True)
            client.oauth2_login(email_address, token)
            client.select_folder("INBOX")
            logger.info("Connected! Listening for new emails (IMAP IDLE)...")

            # Process any emails that arrived before we connected
            process_new_emails(service, processed_ids)

            while True:
                # Enter IDLE mode — wait up to IDLE_TIMEOUT seconds
                client.idle()
                responses = client.idle_check(timeout=IDLE_TIMEOUT)
                client.idle_done()

                if responses:
                    logger.info("New email signal received!")
                    # Small delay so Gmail API has the email ready
                    time.sleep(1)
                    # Refresh token + service in case it expired
                    service = get_gmail_service()
                    process_new_emails(service, processed_ids)
                else:
                    # Timeout — refresh IDLE connection (Gmail drops after 10 min)
                    logger.debug("IDLE timeout — refreshing connection...")

        except KeyboardInterrupt:
            logger.info("Gmail Watcher stopped by user.")
            try:
                client.idle_done()
                client.logout()
            except Exception:
                pass
            break

        except Exception as e:
            logger.error(f"Connection error: {e} — reconnecting in 2 seconds...")
            time.sleep(2)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    logger.info("=" * 60)
    logger.info("Gmail Watcher — IMAP IDLE mode (real-time, no polling)")
    logger.info(f"Vault root: {VAULT_ROOT}")
    logger.info("=" * 60)
    run_imap_idle()


if __name__ == "__main__":
    main()
