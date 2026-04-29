"""
Gmail Test — Read latest emails, generate Claude reply, send with approval.
Usage:
    python gmail_test.py                # Read latest 5 unread emails
    python gmail_test.py --reply N      # Generate Claude reply for email #N and send
"""

import argparse
import base64
import json
import os
import re
from email.mime.text import MIMEText
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

VAULT = Path(__file__).parent.resolve()
CREDS_FILE = VAULT / "gmail_credentials" / "credentials.json"


def get_gmail_service():
    creds_data = json.loads(CREDS_FILE.read_text(encoding="utf-8"))
    creds = Credentials(
        token=None,
        refresh_token=creds_data["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds_data["client_id"],
        client_secret=creds_data["client_secret"],
        scopes=["https://www.googleapis.com/auth/gmail.modify"],
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def decode_body(msg):
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


def get_header(headers, name):
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def fetch_emails(service, count=5):
    results = service.users().messages().list(
        userId="me", q="is:unread", maxResults=count
    ).execute()
    messages = results.get("messages", [])
    emails = []
    for msg_ref in messages:
        msg = service.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute()
        headers = msg.get("payload", {}).get("headers", [])
        emails.append({
            "id": msg_ref["id"],
            "thread_id": msg.get("threadId", ""),
            "subject": get_header(headers, "Subject") or "(No Subject)",
            "from": get_header(headers, "From") or "Unknown",
            "date": get_header(headers, "Date") or "Unknown",
            "body": decode_body(msg),
        })
    return emails


def generate_reply_with_claude(email_data):
    """Generate a smart reply using Claude API."""
    from anthropic import Anthropic

    env_path = VAULT / ".env"
    api_key = ""
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                api_key = line.split("=", 1)[1].strip()

    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not api_key:
        return "ERROR: ANTHROPIC_API_KEY not found in .env or environment"

    client = Anthropic(api_key=api_key)

    prompt = f"""You are replying to an email on behalf of Muhammad Shayan. Write a professional, friendly reply.

From: {email_data['from']}
Subject: {email_data['subject']}
Date: {email_data['date']}

Email Body:
{email_data['body'][:3000]}

Write a concise, professional reply. Sign off as "Shayan". Do NOT include subject line, just the reply body."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def send_email(service, to, subject, body, thread_id=None):
    mime = MIMEText(body, "plain")
    mime["To"] = to
    mime["Subject"] = subject
    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
    message = {"raw": raw}
    if thread_id:
        message["threadId"] = thread_id
    sent = service.users().messages().send(userId="me", body=message).execute()
    return sent.get("id")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reply", type=int, help="Reply to email number N (1-based)")
    ap.add_argument("--count", type=int, default=5, help="Number of emails to fetch")
    args = ap.parse_args()

    print("Connecting to Gmail...")
    service = get_gmail_service()
    emails = fetch_emails(service, args.count)

    if not emails:
        print("No unread emails found!")
        return

    print(f"\n{'='*60}")
    print(f"  UNREAD EMAILS ({len(emails)})")
    print(f"{'='*60}\n")

    for i, e in enumerate(emails, 1):
        print(f"  [{i}] From: {e['from']}")
        print(f"      Subject: {e['subject']}")
        print(f"      Date: {e['date']}")
        print(f"      Body: {e['body'][:100].strip()}...")
        print()

    if args.reply:
        idx = args.reply - 1
        if idx < 0 or idx >= len(emails):
            print(f"Invalid email number. Choose 1-{len(emails)}")
            return

        target = emails[idx]
        print(f"{'='*60}")
        print(f"  GENERATING CLAUDE REPLY for email #{args.reply}")
        print(f"{'='*60}\n")
        print(f"  To: {target['from']}")
        print(f"  Subject: Re: {target['subject']}\n")

        reply_text = generate_reply_with_claude(target)
        print(f"  --- Generated Reply ---\n")
        print(f"{reply_text}\n")
        print(f"  --- End Reply ---\n")

        # Extract email address from "Name <email>" format
        to_email = target["from"]
        match = re.search(r"<(.+?)>", to_email)
        if match:
            to_email = match.group(1)

        confirm = input("Send this reply? (yes/no): ").strip().lower()
        if confirm in ("yes", "y"):
            msg_id = send_email(
                service,
                to_email,
                f"Re: {target['subject']}",
                reply_text,
                target.get("thread_id"),
            )
            print(f"\nEmail sent! Message ID: {msg_id}")
        else:
            print("Reply cancelled.")
    else:
        print("To reply to an email, run:")
        print("  python gmail_test.py --reply 1")


if __name__ == "__main__":
    main()
