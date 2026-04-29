"""
Flask API Backend for ERP Dashboard
Serves Odoo data to the React frontend.
Includes WhatsApp send via Playwright subprocess.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from odoo_client import OdooClient
import traceback
import subprocess
import sys
import threading
import time
import os
import io

# Fix SSL certificate path for google-auth / requests
import certifi
import ssl
import urllib3
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
os.environ["SSL_CERT_FILE"] = certifi.where()
# Disable SSL warnings for unstable connections
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Fix Windows console encoding for Unicode characters
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import json
import base64
from pathlib import Path
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import google.auth.transport.requests
from googleapiclient.discovery import build

app = Flask(__name__)
CORS(app)

VAULT_ROOT = Path(__file__).parent.parent.parent.resolve()  # D:\AI_Employee_Vault
WHATSAPP_SCRIPT = VAULT_ROOT / "whatsapp_playwright.py"

# ── WhatsApp job tracking ──
_wa_jobs = {}  # job_id -> {status, phone, message, result, started, finished}
_wa_lock = threading.Lock()
_wa_busy = False  # Only ONE WhatsApp job at a time (single browser profile)
_wa_proc = None   # Current subprocess reference for cleanup

client = OdooClient()


@app.route("/api/health")
def health():
    try:
        result = client.test_connection()
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/dashboard-stats")
def dashboard_stats():
    try:
        products = client.get_products()
        partners = client.get_partners()
        all_partners = client.get_all_partners()
        invoices = client.get_invoices()

        # Category breakdown from products
        category_counts = {}
        for p in products:
            cat = p.get("categ_id")
            cat_name = cat[1] if cat else "Uncategorized"
            category_counts[cat_name] = category_counts.get(cat_name, 0) + 1

        category_breakdown = [{"name": k, "value": v} for k, v in category_counts.items()]

        # Top products by price
        top_products = sorted(products, key=lambda x: x.get("list_price", 0), reverse=True)[:10]
        top_products_chart = [{"name": p["name"][:25], "price": p.get("list_price", 0)} for p in top_products]

        # Revenue from posted invoices
        total_revenue = sum(i.get("amount_total", 0) for i in invoices
                          if i.get("move_type") == "out_invoice" and i.get("state") == "posted")

        # Sale orders count
        try:
            orders = client.get_sale_orders()
            total_orders = len(orders)
        except Exception:
            total_orders = len(invoices)

        return jsonify({
            "total_products": len(products),
            "total_customers": len(partners),
            "total_partners": len(all_partners),
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "total_invoices": len(invoices),
            "category_breakdown": category_breakdown,
            "top_products": top_products_chart,
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/products")
def products():
    try:
        data = client.get_products()
        # Flatten categ_id
        for p in data:
            cat = p.get("categ_id")
            p["category"] = cat[1] if cat else "Uncategorized"
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/partners")
def partners():
    try:
        data = client.get_all_partners()
        for p in data:
            country = p.get("country_id")
            p["country"] = country[1] if country else ""
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/invoices")
def invoices():
    try:
        data = client.get_invoices()
        for i in data:
            partner = i.get("partner_id")
            i["partner_name"] = partner[1] if partner else "N/A"
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/categories")
def categories():
    try:
        data = client.get_categories()
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/accounting/summary")
def accounting_summary():
    try:
        data = client.get_accounting_summary()
        return jsonify(data)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── WhatsApp Endpoints ──────────────────────────────────────────────────────

WA_HELPER_SCRIPT = Path(__file__).parent / "wa_send_helper.py"


def _run_whatsapp_send(job_id, phone, message):
    """Run whatsapp send in a background thread via helper script."""
    global _wa_busy, _wa_proc

    with _wa_lock:
        _wa_jobs[job_id]["status"] = "running"

    try:
        proc = subprocess.Popen(
            [sys.executable, str(WA_HELPER_SCRIPT), phone, message],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            cwd=str(VAULT_ROOT),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0,
        )
        _wa_proc = proc

        # Wait with timeout (600s to handle OBS recording / heavy CPU load)
        try:
            stdout, stderr = proc.communicate(timeout=600)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            with _wa_lock:
                _wa_jobs[job_id]["status"] = "error"
                _wa_jobs[job_id]["result"] = "Timed out after 600s"
                _wa_jobs[job_id]["finished"] = time.time()
            return
        finally:
            _wa_proc = None

        stdout = (stdout or "").strip()
        stderr = (stderr or "").strip()
        all_output = stdout + "\n" + stderr
        last_stdout_line = stdout.split("\n")[-1] if stdout else ""

        with _wa_lock:
            if "SENT_OK" in last_stdout_line:
                _wa_jobs[job_id]["status"] = "sent"
                _wa_jobs[job_id]["result"] = "Message delivered successfully"
            elif "SEND_FAILED" in last_stdout_line:
                _wa_jobs[job_id]["status"] = "error"
                _wa_jobs[job_id]["result"] = "WhatsApp opened but message could not be sent. Check if number is valid."
            elif "LOGIN_FAILED" in last_stdout_line:
                _wa_jobs[job_id]["status"] = "error"
                _wa_jobs[job_id]["result"] = "WhatsApp not logged in. Run: python whatsapp_playwright.py --setup"
            else:
                error_line = last_stdout_line or (stderr.split("\n")[-1] if stderr else "Unknown error")
                _wa_jobs[job_id]["status"] = "error"
                _wa_jobs[job_id]["result"] = error_line[:200]
            _wa_jobs[job_id]["finished"] = time.time()
            _wa_jobs[job_id]["debug"] = all_output[-500:]

    except Exception as e:
        with _wa_lock:
            _wa_jobs[job_id]["status"] = "error"
            _wa_jobs[job_id]["result"] = str(e)
            _wa_jobs[job_id]["finished"] = time.time()
    finally:
        with _wa_lock:
            _wa_busy = False


@app.route("/api/whatsapp/send", methods=["POST"])
def whatsapp_send():
    """Start a WhatsApp send job in the background. Only ONE at a time."""
    global _wa_busy

    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    phone = (data.get("phone") or "").strip()
    message = (data.get("message") or "").strip()

    if not phone or not message:
        return jsonify({"error": "Both 'phone' and 'message' are required"}), 400

    if not WHATSAPP_SCRIPT.exists():
        return jsonify({"error": "whatsapp_playwright.py not found"}), 500

    # Block concurrent sends — one browser profile = one job at a time
    with _wa_lock:
        if _wa_busy:
            return jsonify({"error": "Another message is being sent. Please wait."}), 429
        _wa_busy = True

    job_id = f"wa_{int(time.time()*1000)}"
    with _wa_lock:
        _wa_jobs[job_id] = {
            "status": "queued",
            "phone": phone,
            "message": message,
            "result": None,
            "started": time.time(),
            "finished": None,
        }

    t = threading.Thread(target=_run_whatsapp_send, args=(job_id, phone, message), daemon=True)
    t.start()

    return jsonify({"job_id": job_id, "status": "queued"}), 202


@app.route("/api/whatsapp/status/<job_id>")
def whatsapp_status(job_id):
    """Check the status of a WhatsApp send job."""
    with _wa_lock:
        job = _wa_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/whatsapp/history")
def whatsapp_history():
    """Return recent WhatsApp send jobs."""
    with _wa_lock:
        jobs = sorted(_wa_jobs.values(), key=lambda j: j["started"], reverse=True)[:20]
    return jsonify(jobs)


@app.route("/api/whatsapp/clear-history", methods=["POST"])
def whatsapp_clear_history():
    """Clear all WhatsApp send history."""
    with _wa_lock:
        _wa_jobs.clear()
    return jsonify({"status": "cleared"})


# ── Gmail Endpoints ───────────────────────────────────────────────────────

GMAIL_CREDS_FILE = VAULT_ROOT / "gmail_credentials" / "credentials.json"
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.send"]


def _make_retry_session(timeout=30):
    """Create a requests session with automatic retries and explicit timeouts."""
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504],
                  allowed_methods=["GET", "POST"], raise_on_status=False)
    adapter = HTTPAdapter(max_retries=retry, pool_connections=1, pool_maxsize=1)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    # Set default timeout so requests don't hang under high CPU load (e.g. OBS recording)
    session.timeout = timeout
    return session


def get_gmail_service():
    """Load OAuth creds, refresh if needed, return Gmail API service."""
    import httplib2
    with open(GMAIL_CREDS_FILE) as f:
        cred_data = json.load(f)
    creds = Credentials(
        token=None,
        refresh_token=cred_data["refresh_token"],
        client_id=cred_data["client_id"],
        client_secret=cred_data["client_secret"],
        token_uri="https://oauth2.googleapis.com/token",
    )
    # Use retry session with explicit timeout for token refresh
    retry_session = _make_retry_session(timeout=30)
    for attempt in range(3):
        try:
            creds.refresh(Request(session=retry_session))
            # Build Gmail service with httplib2 timeout (prevents hang under high CPU load)
            http = httplib2.Http(timeout=30)
            http = google.auth.transport.requests.AuthorizedSession(creds)
            return build("gmail", "v1", credentials=creds, cache_discovery=False,
                         num_retries=2)
        except Exception as e:
            err = str(e)
            if attempt < 2 and ("SSL" in err or "EOF" in err or "Max retries" in err
                                or "Connection aborted" in err or "10054" in err
                                or "ConnectionReset" in err or "timed out" in err
                                or "Timeout" in err):
                wait = (attempt + 1) * 2
                print(f"[Gmail] Network error, retry {attempt+1}/3 in {wait}s: {err[:80]}", flush=True)
                time.sleep(wait)
                continue
            raise


def _decode_email_body(payload):
    """Extract readable text body from Gmail message payload."""
    mime_type = payload.get("mimeType", "")

    # Simple single-part email
    if mime_type.startswith("text/"):
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        return ""

    # Multipart — search parts recursively
    parts = payload.get("parts", [])
    # Prefer text/plain, fallback to text/html
    for preferred in ("text/plain", "text/html"):
        for part in parts:
            if part.get("mimeType") == preferred:
                data = part.get("body", {}).get("data", "")
                if data:
                    text = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                    if preferred == "text/html":
                        # Strip HTML tags for clean display
                        import re
                        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
                        text = re.sub(r"<[^>]+>", "", text)
                        text = re.sub(r"&nbsp;", " ", text)
                        text = re.sub(r"&amp;", "&", text)
                        text = re.sub(r"&lt;", "<", text)
                        text = re.sub(r"&gt;", ">", text)
                        text = re.sub(r"\n{3,}", "\n\n", text)
                    return text.strip()
            # Check nested multipart
            if part.get("mimeType", "").startswith("multipart/"):
                result = _decode_email_body(part)
                if result:
                    return result

    return ""


def _parse_email_headers(msg):
    """Extract subject, from, date, body from Gmail message."""
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    body = _decode_email_body(msg.get("payload", {}))
    return {
        "id": msg["id"],
        "threadId": msg.get("threadId"),
        "messageId": headers.get("message-id", ""),
        "subject": headers.get("subject", "(no subject)"),
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "date": headers.get("date", ""),
        "snippet": msg.get("snippet", ""),
        "body": body or msg.get("snippet", ""),
    }


@app.route("/api/gmail/unread")
def gmail_unread():
    """Fetch 25 latest unread emails with full body."""
    try:
        service = get_gmail_service()
        result = service.users().messages().list(
            userId="me", q="is:unread", maxResults=25
        ).execute()
        messages = result.get("messages", [])
        emails = []
        for m in messages:
            msg = service.users().messages().get(
                userId="me", id=m["id"], format="full"
            ).execute()
            emails.append({**_parse_email_headers(msg), "unread": True})
        return jsonify(emails)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/gmail/latest")
def gmail_latest():
    """Fetch 25 latest emails with full body and unread flag."""
    try:
        service = get_gmail_service()
        result = service.users().messages().list(
            userId="me", maxResults=25
        ).execute()
        messages = result.get("messages", [])
        emails = []
        for m in messages:
            msg = service.users().messages().get(
                userId="me", id=m["id"], format="full"
            ).execute()
            labels = msg.get("labelIds", [])
            emails.append({**_parse_email_headers(msg), "unread": "UNREAD" in labels})
        return jsonify(emails)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/gmail/send", methods=["POST"])
def gmail_send():
    """Send an email via Gmail API with timeout protection."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400
        to = (data.get("to") or "").strip()
        subject = (data.get("subject") or "").strip()
        message_text = (data.get("message") or "").strip()
        if not to or not subject or not message_text:
            return jsonify({"error": "'to', 'subject', and 'message' are required"}), 400

        mime = MIMEText(message_text)
        mime["to"] = to
        mime["subject"] = subject
        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()

        # Use thread with timeout to prevent hang under high CPU load (OBS etc.)
        import concurrent.futures
        def _do_send():
            service = get_gmail_service()
            return service.users().messages().send(
                userId="me", body={"raw": raw}
            ).execute()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_do_send)
            sent = future.result(timeout=60)  # 60s hard timeout

        return jsonify({"status": "sent", "id": sent["id"]})
    except concurrent.futures.TimeoutError:
        return jsonify({"error": "Email send timed out — system may be under heavy load. Try again."}), 504
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/gmail/reply", methods=["POST"])
def gmail_reply():
    """Reply to an email in the same thread, with timeout protection."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400
        to = (data.get("to") or "").strip()
        subject = (data.get("subject") or "").strip()
        message_text = (data.get("message") or "").strip()
        thread_id = (data.get("threadId") or "").strip()
        message_id = (data.get("messageId") or "").strip()
        if not to or not subject or not message_text:
            return jsonify({"error": "'to', 'subject', and 'message' are required"}), 400

        mime = MIMEText(message_text)
        mime["to"] = to
        mime["subject"] = subject
        if message_id:
            mime["In-Reply-To"] = message_id
            mime["References"] = message_id
        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()

        email_body = {"raw": raw}
        if thread_id:
            email_body["threadId"] = thread_id

        # Use thread with timeout to prevent hang under high CPU load (OBS etc.)
        import concurrent.futures
        def _do_reply():
            service = get_gmail_service()
            return service.users().messages().send(
                userId="me", body=email_body
            ).execute()

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_do_reply)
            sent = future.result(timeout=60)  # 60s hard timeout

        return jsonify({"status": "sent", "id": sent["id"]})
    except concurrent.futures.TimeoutError:
        return jsonify({"error": "Email reply timed out — system may be under heavy load. Try again."}), 504
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── Social Media Posting ──────────────────────────────────────────────────

SOCIAL_HELPER = Path(__file__).parent / "social_post_helper.py"
SOCIAL_TEMP_DIR = Path(__file__).parent / "_social_tmp"
SOCIAL_TEMP_DIR.mkdir(exist_ok=True)

VALID_PLATFORMS = {"twitter", "facebook", "linkedin", "instagram"}


def _run_social_post(platform, text, image_path):
    """
    Post to a single platform via social_post_helper.py subprocess.
    Text is passed via a temp file to avoid any shell/quote injection issues.
    All helper output (stderr) is piped to Flask's terminal for live debugging.
    """
    if platform not in VALID_PLATFORMS:
        return {"success": False, "message": f"Unknown platform: {platform}"}

    if not SOCIAL_HELPER.exists():
        return {"success": False, "message": "social_post_helper.py not found"}

    # Write text to temp file — avoids quoting hell
    import uuid
    text_file = SOCIAL_TEMP_DIR / f"post_{uuid.uuid4().hex[:8]}.txt"
    text_file.write_text(text, encoding="utf-8")

    cmd = [sys.executable, str(SOCIAL_HELPER), platform, str(text_file)]
    if image_path:
        cmd.append(str(image_path))

    print(f"\n{'='*60}", flush=True)
    print(f"[SOCIAL] Posting to {platform.upper()}...", flush=True)
    print(f"[SOCIAL] Text: {text[:80]}{'...' if len(text) > 80 else ''}", flush=True)
    print(f"[SOCIAL] Image: {image_path or '(none)'}", flush=True)
    print(f"[SOCIAL] Cmd: {' '.join(cmd)}", flush=True)
    print(f"{'='*60}", flush=True)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=480,
            cwd=str(VAULT_ROOT),
        )

        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()

        # Print ALL helper output to Flask terminal for debugging
        if stderr:
            for line in stderr.split("\n"):
                print(f"  [{platform.upper()}] {line}", flush=True)
        if stdout:
            print(f"  [{platform.upper()}] stdout: {stdout}", flush=True)

        # Parse result from last stdout line: RESULT:OK:msg | RESULT:FAILED:msg | RESULT:ERROR:msg
        last_line = stdout.split("\n")[-1] if stdout else ""

        if last_line.startswith("RESULT:OK:"):
            msg = last_line[len("RESULT:OK:"):]
            print(f"  [{platform.upper()}] >>> SUCCESS: {msg}", flush=True)
            return {"success": True, "message": "Posted successfully"}
        elif last_line.startswith("RESULT:FAILED:"):
            msg = last_line[len("RESULT:FAILED:"):]
            reason = msg if msg != "POST_FAILED" else "Post action returned false — check selectors"
            if msg == "LOGIN_FAILED":
                reason = "Login failed — session expired or credentials wrong"
            print(f"  [{platform.upper()}] >>> FAILED: {reason}", flush=True)
            return {"success": False, "message": reason}
        elif last_line.startswith("RESULT:ERROR:"):
            msg = last_line[len("RESULT:ERROR:"):]
            print(f"  [{platform.upper()}] >>> ERROR: {msg}", flush=True)
            return {"success": False, "message": msg[:300]}
        else:
            # Unexpected output — grab last stderr line as error detail
            err_detail = stderr.split("\n")[-1] if stderr else "No output from helper"
            print(f"  [{platform.upper()}] >>> UNEXPECTED: {err_detail}", flush=True)
            return {"success": False, "message": err_detail[:300] or "Unknown error"}

    except subprocess.TimeoutExpired:
        print(f"  [{platform.upper()}] >>> TIMEOUT after 300s", flush=True)
        return {"success": False, "message": "Timed out after 300s"}
    except Exception as e:
        print(f"  [{platform.upper()}] >>> EXCEPTION: {e}", flush=True)
        return {"success": False, "message": str(e)}
    finally:
        # Cleanup temp file
        try:
            text_file.unlink(missing_ok=True)
        except Exception:
            pass


@app.route("/api/social/post", methods=["POST"])
def social_post():
    """Post to selected social media platforms. Accepts multipart/form-data.
    Requires 'confirmed' flag to be 'true' (LIVE MODE guard).
    """
    text = (request.form.get("text") or "").strip()
    platforms_str = (request.form.get("platforms") or "").strip()
    confirmed = (request.form.get("confirmed") or "").strip().lower()

    print(f"\n[API] /api/social/post called", flush=True)
    print(f"[API]   text={text[:50]}{'...' if len(text) > 50 else ''}", flush=True)
    print(f"[API]   platforms={platforms_str}", flush=True)
    print(f"[API]   confirmed={confirmed}", flush=True)

    if not text:
        return jsonify({"error": "'text' is required"}), 400
    if not platforms_str:
        return jsonify({"error": "'platforms' is required"}), 400
    if confirmed != "true":
        return jsonify({"error": "LIVE MODE not enabled — toggle confirmation first"}), 400

    platforms = [p.strip().lower() for p in platforms_str.split(",") if p.strip()]

    # Handle image upload
    image_path = None
    if "image" in request.files:
        img_file = request.files["image"]
        if img_file.filename:
            uploads_dir = VAULT_ROOT / "Media" / "uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            save_path = uploads_dir / img_file.filename
            img_file.save(str(save_path))
            image_path = str(save_path)
            print(f"[API]   image saved: {save_path}", flush=True)

    # Instagram fallback: use .ig_resized.jpg if no image uploaded
    if "instagram" in platforms and not image_path:
        fallback = VAULT_ROOT / ".ig_resized.jpg"
        if fallback.exists():
            image_path = str(fallback)
            print(f"[API]   Instagram fallback image: {fallback}", flush=True)
        else:
            return jsonify({"error": "Instagram requires an image and no fallback found"}), 400

    results = {}
    for platform in platforms:
        results[platform] = _run_social_post(platform, text, image_path)
        print(f"[API]   {platform} => {results[platform]}", flush=True)

    print(f"[API] All done. Results: {results}\n", flush=True)
    return jsonify({"results": results})


if __name__ == "__main__":
    print("ERP Dashboard API starting on http://localhost:5001")
    # use_reloader=False is CRITICAL — reloader forks process and kills
    # the in-memory _wa_jobs dict, breaking WhatsApp background jobs
    app.run(host="0.0.0.0", port=5001, debug=True, use_reloader=False)
