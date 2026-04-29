"""
WhatsApp AI Automation via Playwright + Groq Cloud AI
=====================================================
Persistent browser session — scan QR code only ONCE.
AI-powered auto-replies using Groq (free cloud LLM).

Features:
  - Persistent login using browser profile (no re-scan)
  - Send outgoing messages (from /Approved folder)
  - Detect incoming unread messages
  - AI auto-reply using Groq cloud API (no local GPU needed)
  - Conversation history per contact for context-aware replies
  - Watch mode for continuous operation

Requirements:
  pip install playwright groq python-dotenv
  GROQ_API_KEY in .env file (get free key at console.groq.com)

Usage:
  python whatsapp_playwright.py --setup                # First time — scan QR
  python whatsapp_playwright.py --watch                # Send approved messages
  python whatsapp_playwright.py --listen               # Detect incoming only
  python whatsapp_playwright.py --auto-reply           # AI replies (full mode)
  python whatsapp_playwright.py --auto-reply --model llama-3.3-70b-versatile

Config:
  - System prompt: edit ai_system_prompt.txt
  - Conversation history saved per contact in .whatsapp_chats/
"""

import argparse
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

load_dotenv(Path(__file__).parent / ".env")

# ─── Paths ────────────────────────────────────────────────────────────────────
VAULT        = Path(__file__).parent.resolve()
APPROVED     = VAULT / "Approved"
PENDING      = VAULT / "Pending_Approval"
DONE         = VAULT / "Done"
LOGS         = VAULT / "Logs"
PROFILE_DIR  = VAULT / ".whatsapp_profile"
STATE_FILE   = VAULT / ".whatsapp_state.json"
CHATS_DIR    = VAULT / ".whatsapp_chats"
PROMPT_FILE  = VAULT / "ai_system_prompt.txt"

for folder in (APPROVED, PENDING, DONE, LOGS, CHATS_DIR):
    folder.mkdir(exist_ok=True)

# ─── Logging ──────────────────────────────────────────────────────────────────
log_path = LOGS / f"whatsapp_{datetime.now():%Y-%m-%d}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    handlers=[
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("whatsapp")

POLL_SEC = 30
DEFAULT_MODEL = "llama-3.1-8b-instant"

# ─── Auto-reply whitelist (only these contacts get AI replies) ───────────────
# Add phone numbers (with or without +92) or contact names exactly as shown in WhatsApp
REPLY_WHITELIST = [
    "03278448829",
    "+923278448829",
    "923278448829",
    "3278448829",
]

# ─── Self-chat config ────────────────────────────────────────────────────────
# Your own name/number as it appears in WhatsApp (for self-chat monitoring)
SELF_CHAT_NAME = "Shayan meo"  # Your self-chat name in WhatsApp
LAST_SELF_MSG_FILE = CHATS_DIR / "_last_self_msg.txt"

# ─── Groq client ─────────────────────────────────────────────────────────────
import os
_groq_key = os.environ.get("GROQ_API_KEY")
_groq_client: Groq | None = Groq(api_key=_groq_key) if _groq_key else None


# ─── AI Reply (Groq) ─────────────────────────────────────────────────────────
def load_system_prompt() -> str:
    """Load custom system prompt or create default."""
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8").strip()

    default = (
        "You are a helpful personal AI assistant replying on WhatsApp on behalf of the user. "
        "Keep replies short, friendly, and natural — like a real person texting. "
        "Use simple language. Don't be overly formal. "
        "If you don't know something, say you'll check and get back. "
        "Reply in the same language the person messaged in (Urdu, English, Roman Urdu, etc). "
        "Never reveal you are an AI unless directly asked."
    )
    PROMPT_FILE.write_text(default, encoding="utf-8")
    log.info("Created default ai_system_prompt.txt — edit it to customize AI behavior.")
    return default


def load_chat_history(contact: str) -> list[dict]:
    """Load conversation history for a contact."""
    safe = re.sub(r"[^\w\-]", "_", contact)[:40]
    path = CHATS_DIR / f"{safe}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def save_chat_history(contact: str, history: list[dict]):
    """Save conversation history. Keep last 20 messages for context."""
    safe = re.sub(r"[^\w\-]", "_", contact)[:40]
    path = CHATS_DIR / f"{safe}.json"
    history = history[-20:]
    path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def generate_ai_reply(contact: str, incoming_msg: str, model: str) -> str | None:
    """Send message to Groq and get AI reply."""
    if not _groq_client:
        log.error("GROQ_API_KEY not set! Add it to .env file.")
        return None

    system_prompt = load_system_prompt()
    history = load_chat_history(contact)

    history.append({"role": "user", "content": incoming_msg})

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)

    log.info("Asking Groq for reply to %s (model: %s)...", contact, model)

    try:
        resp = _groq_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=512,
            temperature=0.7,
        )
        reply = resp.choices[0].message.content.strip()

        if not reply:
            log.error("AI returned empty reply.")
            return None

        history.append({"role": "assistant", "content": reply})
        save_chat_history(contact, history)

        log.info("AI reply for %s: %s", contact, reply[:100])
        return reply

    except Exception as e:
        log.error("Groq error: %s", e)
        return None


# ─── Helpers ──────────────────────────────────────────────────────────────────
def parse_message_file(path: Path) -> dict | None:
    """Read a whatsapp_*.md and return {to, message} or None."""
    text = path.read_text(encoding="utf-8")
    to  = re.search(r"##\s*To\s*\n+(.+?)(?:\n##|\Z)", text, re.DOTALL)
    msg = re.search(r"##\s*Message\s*\n+(.+?)(?:\n##|\Z)", text, re.DOTALL)
    if not to or not msg:
        log.error("Cannot parse To/Message in %s", path.name)
        return None
    return {
        "to":      to.group(1).strip().splitlines()[0].strip(),
        "message": re.sub(r"^```.*?\n(.*?)```$", r"\1",
                          msg.group(1).strip(), flags=re.DOTALL).strip(),
    }


def archive(path: Path, status: str, note: str):
    """Move task file to /Done with result metadata."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = DONE / f"wa_{ts}_{path.name}"
    body = path.read_text(encoding="utf-8")
    body += f"\n\n---\n- **Status:** {status}\n- **Time:** {datetime.now():%Y-%m-%d %H:%M}\n- **Note:** {note}\n"
    dest.write_text(body, encoding="utf-8")
    path.unlink()
    log.info("Archived → Done/%s", dest.name)


# ─── State management ─────────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_checked": None, "processed": {}}


def save_state(state: dict):
    state["last_checked"] = datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


# ─── WhatsApp Controller ─────────────────────────────────────────────────────
class WhatsApp:
    """Controls WhatsApp Web through a persistent Chromium profile."""

    def __init__(self):
        self.pw   = None
        self.ctx  = None
        self.page = None

    # ── Browser lifecycle ─────────────────────────────────────────────────
    def open(self):
        """Launch Chromium with persistent profile — keeps session alive."""
        PROFILE_DIR.mkdir(exist_ok=True)
        self.pw  = sync_playwright().start()
        self.ctx = self.pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 800},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-default-apps",
                "--disable-sync",
            ],
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        self.ctx.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
        log.info("Browser opened with persistent profile.")

    def close(self):
        """Shut down — profile stays on disk for next run."""
        if self.ctx:
            self.ctx.close()
        if self.pw:
            self.pw.stop()
        log.info("Browser closed. Profile saved.")

    # ── Login detection ───────────────────────────────────────────────────
    def _is_logged_in(self) -> bool:
        for sel in (
            "#pane-side",
            '[data-testid="chat-list"]',
            '[data-testid="chatlist-header"]',
            'div[aria-label="Chat list"]',
        ):
            try:
                if self.page.locator(sel).first.is_visible(timeout=2000):
                    return True
            except Exception:
                continue
        return False

    def wait_login(self, max_seconds: int = 180) -> bool:
        """Go to WhatsApp Web and wait for saved session to load."""
        self.page.goto("https://web.whatsapp.com",
                       timeout=200_000, wait_until="domcontentloaded")
        rounds = max_seconds // 5
        for i in range(rounds):
            self.page.wait_for_timeout(5000)
            if self._is_logged_in():
                log.info("Logged in from saved profile.")
                return True
            log.info("Waiting for login... %d/%ds", (i + 1) * 5, max_seconds)
        log.error("Login not detected within %ds.", max_seconds)
        self.page.screenshot(path=str(LOGS / "wa_login_fail.png"))
        return False

    def setup_qr(self) -> bool:
        """First-time QR scan. Profile is auto-saved by Chromium."""
        self.page.goto("https://web.whatsapp.com",
                       timeout=120_000, wait_until="domcontentloaded")
        self.page.wait_for_timeout(5000)

        if self._is_logged_in():
            log.info("Already logged in — no QR needed!")
            return True

        log.info(">>> Scan the QR code on screen (10 min timeout) <<<")

        for i in range(200):
            time.sleep(3)
            if self._is_logged_in():
                log.info("QR scanned! Session saved in browser profile.")
                return True
            if i and i % 10 == 0:
                log.info("Still waiting for QR... %ds", i * 3)

        log.error("QR scan timed out.")
        return False

    # ── Send a message ────────────────────────────────────────────────────
    def send(self, to: str, message: str) -> bool:
        """Send message to a phone number or contact name."""
        log.info("Sending to: %s", to)
        try:
            if re.match(r"^\+?[\d\s\-]+$", to):
                num = re.sub(r"[\s\-\(\)\+]", "", to)
                # Convert Pakistani local number (03xx) to international (923xx)
                if num.startswith("03") and len(num) == 11:
                    num = "92" + num[1:]
                elif num.startswith("3") and len(num) == 10:
                    num = "92" + num

                log.info("Opening chat via URL: phone=%s", num)
                self.page.goto(
                    f"https://web.whatsapp.com/send?phone={num}",
                    timeout=240_000, wait_until="domcontentloaded",
                )
                self.page.wait_for_timeout(18000)

                # Check if "Phone number shared via url is invalid" popup appeared
                try:
                    invalid = self.page.locator("div:has-text('Phone number shared via url is invalid')").first
                    if invalid.is_visible(timeout=2000):
                        log.error("Invalid phone number: %s", num)
                        return False
                except Exception:
                    pass

                # Wait for compose box to appear (means chat loaded)
                try:
                    self.page.locator(
                        '[data-testid="conversation-compose-box-input"], '
                        'div[contenteditable="true"][data-tab="10"], '
                        'footer div[contenteditable="true"]'
                    ).first.wait_for(timeout=120_000, state="visible")
                    log.info("Chat opened for %s", num)
                except Exception:
                    log.warning("Compose box not found, trying anyway...")
            else:
                self._search_and_open_chat(to)

            self._type_and_send(message)
            log.info("Message sent to %s", to)
            return True

        except PWTimeout:
            log.error("Timeout sending to %s", to)
            self.page.screenshot(path=str(LOGS / "wa_send_fail.png"))
            return False
        except Exception as e:
            log.error("Error sending to %s: %s", to, e)
            return False

    def _search_and_open_chat(self, name: str):
        """Open a chat by searching for contact name."""
        # First go back to main chat list
        try:
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(500)
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(500)
        except Exception:
            pass

        # Try multiple search button selectors
        search_selectors = [
            '[data-testid="chat-list-search"]',
            '[title="Search or start new chat"]',
            'button[aria-label="Search or start new chat"]',
            '[data-testid="search-input"]',
            'div[contenteditable="true"][data-tab="3"]',
            'p.selectable-text[data-tab="3"]',
        ]
        clicked = False
        for sel in search_selectors:
            try:
                el = self.page.locator(sel).first
                el.click(timeout=5000)
                clicked = True
                log.info("Search opened via: %s", sel)
                break
            except Exception:
                continue

        if not clicked:
            # Fallback: use Ctrl+F or click on top search area
            try:
                self.page.keyboard.press("Control+f")
                self.page.wait_for_timeout(1000)
                clicked = True
                log.info("Search opened via Ctrl+F")
            except Exception:
                pass

        if not clicked:
            raise Exception("Could not open search")

        self.page.wait_for_timeout(1000)

        # Find and fill search box
        box_selectors = [
            '[data-testid="search-input"]',
            'div[contenteditable="true"][data-tab="3"]',
            'p.selectable-text[data-tab="3"]',
            'div[contenteditable="true"][role="textbox"]',
        ]
        box = None
        for sel in box_selectors:
            try:
                el = self.page.locator(sel).first
                el.wait_for(timeout=3000, state="visible")
                box = el
                log.info("Search box found: %s", sel)
                break
            except Exception:
                continue

        if not box:
            raise Exception("Could not find search box")

        box.click()
        self.page.wait_for_timeout(300)
        self.page.keyboard.type(name, delay=50)
        self.page.wait_for_timeout(3000)

        # Click first search result
        result_selectors = [
            '[data-testid="cell-frame-container"]',
            'div[role="listitem"]',
            'div[role="row"] span[title]',
        ]
        for sel in result_selectors:
            try:
                self.page.locator(sel).first.click(timeout=8000)
                log.info("Chat opened via: %s", sel)
                break
            except Exception:
                continue

        self.page.wait_for_timeout(2000)

    def _type_and_send(self, message: str):
        """Type text into the compose box and press send."""
        compose_selectors = [
            '[data-testid="conversation-compose-box-input"]',
            'div[contenteditable="true"][data-tab="10"]',
            'div[contenteditable="true"][title="Type a message"]',
            'footer div[contenteditable="true"]',
            'div[contenteditable="true"][role="textbox"]',
            '#main footer div[contenteditable="true"]',
            'p.selectable-text[data-tab="10"]',
        ]
        compose = None
        for sel in compose_selectors:
            try:
                el = self.page.locator(sel).first
                el.wait_for(timeout=15000, state="visible")
                compose = el
                log.info("Compose box found: %s", sel)
                break
            except Exception:
                continue

        if not compose:
            # Debug: check what's on the page
            try:
                debug = self.page.evaluate("""() => {
                    const edits = document.querySelectorAll('[contenteditable="true"]');
                    return Array.from(edits).map((e,i) =>
                        i + ': tag=' + e.tagName + ' tab=' + e.getAttribute('data-tab') +
                        ' role=' + e.getAttribute('role') + ' title=' + e.getAttribute('title') +
                        ' class=' + e.className.substring(0,50)
                    ).join('\\n');
                }""")
                log.error("Compose box NOT found. Editable elements:\n%s", debug)
            except Exception:
                pass
            raise Exception("Could not find compose box")

        compose.click()
        self.page.wait_for_timeout(800)

        lines = message.split("\n")
        for i, line in enumerate(lines):
            self.page.keyboard.type(line, delay=30)
            if i < len(lines) - 1:
                self.page.keyboard.press("Shift+Enter")

        self.page.wait_for_timeout(1000)

        # Try send button (increased timeouts for OBS/heavy load)
        send_selectors = [
            '[data-testid="send"]',
            'button[aria-label="Send"]',
            'span[data-icon="send"]',
        ]
        sent = False
        for sel in send_selectors:
            try:
                self.page.locator(sel).first.click(timeout=15000)
                sent = True
                log.info("Send clicked: %s", sel)
                break
            except Exception:
                continue

        if not sent:
            # Fallback: Enter key
            log.info("Send button not found, pressing Enter")
            self.page.keyboard.press("Enter")

        # Wait for message to actually deliver
        log.info("Waiting for message delivery...")
        self.page.wait_for_timeout(5000)

        # Verify: check if compose box is empty (message was sent)
        for attempt in range(15):
            try:
                compose_text = self.page.evaluate("""() => {
                    const boxes = document.querySelectorAll('[data-testid="conversation-compose-box-input"], div[contenteditable="true"][data-tab="10"], footer div[contenteditable="true"]');
                    for (const b of boxes) {
                        const t = b.textContent.trim();
                        if (t) return t;
                    }
                    return '';
                }""")
                if not compose_text:
                    log.info("Message delivered (compose box empty).")
                    break
            except Exception:
                pass
            log.info("Delivery check %d/15...", attempt + 1)
            self.page.wait_for_timeout(3000)
        else:
            # Compose box still has text — message typed but not sent
            # Try send button ONE more time
            log.warning("Compose box still has text — retrying send...")
            for sel in send_selectors:
                try:
                    self.page.locator(sel).first.click(timeout=10000)
                    log.info("Retry send clicked: %s", sel)
                    self.page.wait_for_timeout(5000)
                    break
                except Exception:
                    continue
            else:
                self.page.keyboard.press("Enter")
                self.page.wait_for_timeout(5000)

        # Extra wait to ensure network delivery
        self.page.wait_for_timeout(5000)

    # ── Incoming messages ─────────────────────────────────────────────────
    def check_incoming(self, ai_model: str | None = None) -> int:
        """Find unread chats, optionally auto-reply with AI."""
        log.info("Scanning for unread messages...")
        state = load_state()
        processed = state.get("processed", {})
        found = 0

        url = self.page.url
        if "web.whatsapp.com" not in url:
            self.page.goto("https://web.whatsapp.com",
                           timeout=30_000, wait_until="domcontentloaded")

        # Wait for chat list
        for attempt in range(6):
            self.page.wait_for_timeout(5000)
            if self._is_logged_in():
                break
            log.info("Waiting for chat list... %d/6", attempt + 1)
        else:
            log.error("Not logged in — cannot check messages.")
            return 0

        # Debug: dump all unread-related elements
        try:
            debug_info = self.page.evaluate("""() => {
                const results = [];
                // Check for unread badge spans
                const badges = document.querySelectorAll('span[aria-label*="unread"], span[data-testid="icon-unread-count"]');
                results.push('badges found: ' + badges.length);
                badges.forEach((b, i) => {
                    results.push('  badge ' + i + ': tag=' + b.tagName + ' aria=' + b.getAttribute('aria-label') + ' testid=' + b.getAttribute('data-testid') + ' text=' + b.textContent);
                    // Find parent listitem
                    let p = b.closest('[role="listitem"], [role="row"], div[data-testid]');
                    if (p) results.push('    parent: role=' + p.getAttribute('role') + ' testid=' + p.getAttribute('data-testid'));
                });
                // Check chat list structure
                const listitems = document.querySelectorAll('[role="listitem"]');
                results.push('listitem count: ' + listitems.length);
                const rows = document.querySelectorAll('[role="row"]');
                results.push('row count: ' + rows.length);
                // Check for green unread dot or number badge
                const allSpans = document.querySelectorAll('span');
                let unreadSpans = 0;
                allSpans.forEach(s => {
                    const bg = window.getComputedStyle(s).backgroundColor;
                    const text = s.textContent.trim();
                    if (text.match(/^\\d+$/) && text !== '' && bg.includes('25a')) {
                        unreadSpans++;
                        if (unreadSpans <= 5) results.push('  green-badge: text=' + text + ' bg=' + bg);
                    }
                });
                results.push('green badge spans: ' + unreadSpans);
                return results.join('\\n');
            }""")
            log.info("DEBUG unread scan:\n%s", debug_info)
        except Exception as e:
            log.warning("Debug scan failed: %s", e)

        # Find unread chats — try many selector patterns
        unread = None
        count = 0
        selectors = (
            # Standard patterns
            'div[role="listitem"]:has(span[aria-label*="unread message"])',
            'div[role="listitem"]:has(span[aria-label*="unread"])',
            'div[role="listitem"]:has(span[data-testid="icon-unread-count"])',
            # Row-based patterns (newer WhatsApp Web)
            'div[role="row"]:has(span[aria-label*="unread message"])',
            'div[role="row"]:has(span[aria-label*="unread"])',
            'div[role="row"]:has(span[data-testid="icon-unread-count"])',
            # Generic container patterns
            '[data-testid="cell-frame-container"]:has(span[aria-label*="unread"])',
            '[data-testid="cell-frame-container"]:has(span[data-testid="icon-unread-count"])',
            # Chat list item with any unread indicator
            'div[role="listitem"]:has([data-icon="unread-count"])',
            'div[role="row"]:has([data-icon="unread-count"])',
        )
        for sel in selectors:
            try:
                loc = self.page.locator(sel)
                c = loc.count()
                if c > 0:
                    unread = loc
                    count = c
                    log.info("Unread matched: %s (%d chats)", sel, c)
                    break
            except Exception:
                continue

        if count == 0:
            log.info("No unread messages detected (tried %d selectors).", len(selectors))
            save_state(state)
            return 0

        # Collect unread chat info via JS to avoid stale elements
        try:
            unread_chats = self.page.evaluate("""(selector) => {
                const rows = document.querySelectorAll(selector);
                const results = [];
                for (let i = 0; i < rows.length && i < 15; i++) {
                    const titleEl = rows[i].querySelector('span[title]');
                    const name = titleEl ? titleEl.getAttribute('title') : 'Unknown';
                    results.push(name);
                }
                return results;
            }""", unread.first.evaluate("el => { const s = el.closest('[role]'); return s ? s.tagName : ''; }") and f'{selectors[0].split(":has")[0]}:has(span[aria-label*="unread"])' if False else
                # Use the matched selector
                next(s for s in selectors if self.page.locator(s).count() > 0)
            )
        except Exception:
            unread_chats = []

        # Process max 5 chats per cycle to avoid timeouts
        max_process = min(count, 5)
        for i in range(max_process):
            try:
                # Re-locate each time (DOM changes after clicking)
                loc = self.page.locator(next(s for s in selectors if self.page.locator(s).count() > 0))
                if loc.count() == 0:
                    log.info("No more unread chats to process.")
                    break

                chat = loc.first  # Always click the first unread

                # Sender name
                sender = "Unknown"
                try:
                    sender = chat.locator("span[title]").first.get_attribute("title", timeout=3000) or "Unknown"
                except Exception:
                    pass

                # Preview text
                preview = ""
                try:
                    for prev_sel in ("span[title].x1iyjqo2", "span.x1rg5ohu._ao3e", "span[title] ~ span"):
                        try:
                            preview = chat.locator(prev_sel).first.inner_text(timeout=1500)
                            if preview:
                                break
                        except Exception:
                            continue
                except Exception:
                    pass

                # Skip already processed
                if processed.get(sender) == preview and preview:
                    log.info("Already processed: %s", sender)
                    break

                # Open chat — try scroll into view + click
                try:
                    chat.scroll_into_view_if_needed(timeout=3000)
                    chat.click(timeout=8000)
                except Exception:
                    # Fallback: JS click
                    try:
                        chat.evaluate("el => el.click()")
                    except Exception as e:
                        log.error("Cannot click chat %s: %s", sender, e)
                        break
                self.page.wait_for_timeout(2000)

                # Read header name
                header = sender
                try:
                    header = self.page.locator("#main header span[title]").first.get_attribute("title", timeout=3000) or sender
                except Exception:
                    pass

                # Get last incoming message text
                msgs = self.page.locator("div.message-in div.copyable-text")
                msg_text = ""
                n = msgs.count()
                if n > 0:
                    try:
                        msg_text = msgs.nth(n - 1).locator("span.selectable-text").first.inner_text(timeout=3000)
                    except Exception:
                        msg_text = preview or "(could not read)"
                else:
                    msg_text = preview or "(could not read)"

                processed[sender] = preview or msg_text[:50]

                # ── AI Auto-Reply (whitelist only) ───────────────────
                reply_sent = ""
                is_whitelisted = any(w in header or w in sender for w in REPLY_WHITELIST)
                if ai_model and not is_whitelisted:
                    log.info("SKIPPED AI reply for %s (not in whitelist)", sender)
                if ai_model and is_whitelisted:
                    ai_reply = generate_ai_reply(header, msg_text, ai_model)
                    if ai_reply:
                        log.info("AI replying to %s: %s", sender, ai_reply[:80])
                        try:
                            self._type_and_send(ai_reply)
                            reply_sent = ai_reply
                            log.info("AI reply sent to %s", sender)
                        except Exception as e:
                            log.error("Failed to send AI reply to %s: %s", sender, e)

                # ── Create task file ──────────────────────────────────
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe = re.sub(r"[^\w\-]", "_", sender)[:30]
                task_path = PENDING / f"whatsapp_in_{ts}_{safe}.md"

                ai_note = ""
                if reply_sent:
                    ai_note = f"\n## AI Auto-Reply Sent\n{reply_sent}\n"

                task_path.write_text(f"""# Incoming WhatsApp Message

## From
{header}

## Message Received
{msg_text}

## Time
{datetime.now():%Y-%m-%d %H:%M:%S}
{ai_note}
## Suggested Action
Review this message. To reply manually, fill in below and move to /Approved.

## To
{header}

## Message
(Write your reply here)
""", encoding="utf-8")

                log.info("Task created: %s (AI replied: %s)", task_path.name, bool(reply_sent))
                found += 1

                # Log
                log_entry = LOGS / f"{datetime.now():%Y-%m-%d}_task_log.md"
                with open(log_entry, "a", encoding="utf-8") as f:
                    f.write(f"- {datetime.now():%H:%M} | WhatsApp IN from **{sender}**: {msg_text[:80]}")
                    if reply_sent:
                        f.write(f" → AI replied: {reply_sent[:60]}")
                    f.write("\n")

            except Exception as e:
                log.error("Error on unread chat #%d: %s", i, e)

        state["processed"] = processed
        save_state(state)
        log.info("Scan done. %d new message(s).", found)
        return found

    # ── Self-chat monitor ────────────────────────────────────────────────
    def _open_self_chat(self) -> bool:
        """Open the self-chat ('Shayan meo') reliably."""
        # Check if already in self-chat
        try:
            header = self.page.locator("#main header span[title]").first
            current = header.get_attribute("title", timeout=2000) or ""
            if SELF_CHAT_NAME.lower() in current.lower():
                return True
        except Exception:
            pass

        # Method 1: Direct phone URL (self-message)
        try:
            self.page.goto(
                f"https://web.whatsapp.com/send?phone=923278448829&text=",
                timeout=20_000, wait_until="domcontentloaded",
            )
            self.page.wait_for_timeout(5000)
            # Check if chat opened
            try:
                header = self.page.locator("#main header span[title]").first
                name = header.get_attribute("title", timeout=3000) or ""
                if name:
                    log.info("Self-chat opened via direct URL: %s", name)
                    return True
            except Exception:
                pass
        except Exception:
            pass

        # Method 2: Search
        try:
            self.page.goto("https://web.whatsapp.com",
                           timeout=20_000, wait_until="domcontentloaded")
            self.page.wait_for_timeout(5000)
            self._search_and_open_chat(SELF_CHAT_NAME)
            return True
        except Exception as e:
            log.error("Could not open self-chat: %s", e)
            return False

    def check_self_chat(self, ai_model: str | None = None) -> int:
        """Monitor self-chat for new messages and AI-reply."""
        if not ai_model:
            return 0

        log.info("Checking self-chat '%s'...", SELF_CHAT_NAME)

        if not self._open_self_chat():
            return 0

        # Read last message via JavaScript (most reliable)
        try:
            last_msg = self.page.evaluate("""() => {
                // Junk patterns to ignore (WhatsApp UI elements, not real messages)
                const junk = ['msg-dblcheck', 'msg-check', 'msg-time', 'read', 'tail-in',
                              'tail-out', 'status-', 'emoji', 'icon-', 'pending'];

                function isJunk(text) {
                    if (!text || text.length < 2) return true;
                    const t = text.toLowerCase().trim();
                    if (junk.some(j => t === j || t.startsWith(j))) return true;
                    // Pure timestamps like "12:30" or "12:30 PM"
                    if (/^\\d{1,2}:\\d{2}(\\s*(am|pm))?$/i.test(t)) return true;
                    return false;
                }

                // Best: copyable-text contains actual message content
                const msgs = document.querySelectorAll('#main div.copyable-text span.selectable-text');
                for (let i = msgs.length - 1; i >= 0; i--) {
                    const t = msgs[i].innerText.trim();
                    if (!isJunk(t)) return t;
                }

                // Fallback: any selectable-text with dir attribute
                const spans = document.querySelectorAll('#main span.selectable-text[dir]');
                for (let i = spans.length - 1; i >= 0; i--) {
                    const t = spans[i].innerText.trim();
                    if (!isJunk(t)) return t;
                }

                return '';
            }""")

            if not last_msg:
                # Debug: what's visible in #main
                try:
                    debug = self.page.evaluate("""() => {
                        const main = document.querySelector('#main');
                        if (!main) return 'NO #main found!';
                        const spans = main.querySelectorAll('span');
                        const texts = [];
                        spans.forEach((s, i) => {
                            const t = s.textContent.trim();
                            if (t && t.length > 2 && i < 30) texts.push(i + ': ' + t.substring(0,60));
                        });
                        return 'spans in #main: ' + spans.length + '\\n' + texts.join('\\n');
                    }""")
                    log.info("Self-chat debug:\n%s", debug)
                except Exception:
                    pass
                log.info("Self-chat: no messages visible.")
                return 0

            log.info("Self-chat last msg: %s", last_msg[:80])
        except Exception as e:
            log.error("Could not read self-chat: %s", e)
            return 0

        # Load previous last message
        prev_msg = ""
        if LAST_SELF_MSG_FILE.exists():
            prev_msg = LAST_SELF_MSG_FILE.read_text(encoding="utf-8").strip()

        # Same message = nothing new
        if last_msg == prev_msg:
            log.info("Self-chat: no new messages.")
            return 0

        # Save current message
        LAST_SELF_MSG_FILE.write_text(last_msg, encoding="utf-8")

        # Don't reply to AI's own replies
        history = load_chat_history("self_chat")
        if history and history[-1].get("role") == "assistant":
            ai_last = history[-1].get("content", "")
            if ai_last == last_msg or last_msg in ai_last or ai_last in last_msg:
                log.info("Self-chat: last message is AI's own reply, skipping.")
                return 0

        # Generate and send AI reply
        log.info("Self-chat: NEW message! Generating AI reply...")
        ai_reply = generate_ai_reply("self_chat", last_msg, ai_model)
        if ai_reply:
            try:
                self._type_and_send(ai_reply)
                LAST_SELF_MSG_FILE.write_text(ai_reply, encoding="utf-8")
                log.info("Self-chat: AI REPLIED: %s", ai_reply[:80])
                return 1
            except Exception as e:
                log.error("Self-chat: send failed: %s", e)
        return 0


# ─── Process approved outgoing messages ───────────────────────────────────────
def process_outgoing(wa: WhatsApp) -> int:
    """Send all whatsapp_*.md files from /Approved."""
    files = sorted(APPROVED.glob("*whatsapp_*.md"))
    if not files:
        return 0
    sent = 0
    for f in files:
        data = parse_message_file(f)
        if not data:
            archive(f, "ERROR", "Cannot parse file")
            continue
        if wa.send(data["to"], data["message"]):
            archive(f, "SENT", f"Delivered to {data['to']}")
            sent += 1
        else:
            archive(f, "FAILED", f"Could not send to {data['to']}")
    return sent


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="WhatsApp AI Automation")
    ap.add_argument("--setup",      action="store_true", help="First-time QR scan")
    ap.add_argument("--watch",      action="store_true", help="Watch /Approved for outgoing")
    ap.add_argument("--listen",     action="store_true", help="Detect incoming messages")
    ap.add_argument("--auto-reply", action="store_true", help="AI auto-reply (implies --listen --watch)")
    ap.add_argument("--model",      default=DEFAULT_MODEL, help=f"Groq model name (default: {DEFAULT_MODEL})")
    args = ap.parse_args()

    if args.auto_reply:
        args.listen = True
        args.watch = True

    ai_model = args.model if args.auto_reply else None

    # Verify Groq API key if auto-reply
    if ai_model and not _groq_client:
        log.error("GROQ_API_KEY not set! Add it to .env: GROQ_API_KEY=gsk_...")
        return

    wa = WhatsApp()

    try:
        wa.open()

        if args.setup:
            if not wa.setup_qr():
                return
            log.info("Setup done! Profile saved.")
            if not (args.watch or args.listen):
                return
        else:
            if not wa.wait_login():
                log.error("Not logged in. Run: python whatsapp_playwright.py --setup")
                return

        log.info("WhatsApp ready.")

        if ai_model:
            log.info("AI Auto-Reply ON | Model: %s", ai_model)
            log.info("System prompt: ai_system_prompt.txt")
            log.info("Chat histories: .whatsapp_chats/")

        if args.watch or args.listen:
            mode = []
            if args.watch:
                mode.append("send")
            if args.listen:
                mode.append("receive")
            if ai_model:
                mode.append("AI-reply")
            log.info("Mode: %s | Polling every %ds", " + ".join(mode), POLL_SEC)

            while True:
                # FIRST: Send any pending outgoing messages from /Approved
                if args.watch:
                    sent = process_outgoing(wa)
                    if sent:
                        log.info("Sent %d outgoing message(s).", sent)
                # THEN: Monitor self-chat for AI replies
                if ai_model:
                    wa.check_self_chat(ai_model=ai_model)
                elif args.listen:
                    wa.check_incoming(ai_model=None)
                time.sleep(POLL_SEC)
        else:
            sent = process_outgoing(wa)
            log.info("Done. %d message(s) sent.", sent)

    except KeyboardInterrupt:
        log.info("Stopped by user.")
    finally:
        wa.close()


if __name__ == "__main__":
    main()
