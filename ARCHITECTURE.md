# Architecture & Lessons Learned — Personal AI Employee (Gold Tier)

> Hackathon 0: Building Autonomous FTEs in 2026
> Author: Shayan | Date: 2026-03-03

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    AI EMPLOYEE VAULT                         │
│                                                             │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  SENSES  │───▶│    BRAIN     │───▶│      HANDS       │  │
│  │ Watchers │    │ Claude Code  │    │   MCP Servers     │  │
│  │ (11)     │    │ + Ralph Loop │    │   + Playwright    │  │
│  └──────────┘    └──────────────┘    └──────────────────┘  │
│       │                │                      │             │
│       ▼                ▼                      ▼             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              OBSIDIAN VAULT (Memory/GUI)             │   │
│  │  /Inbox → /Needs_Action → /Plans → /Done            │   │
│  │  /Pending_Approval → /Approved → (execute)          │   │
│  │  /Logs  /Briefings  /Dashboard.md                   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Core Design Principle
**Perception → Reasoning → Action** — The AI Employee follows a 3-phase loop:
1. **Perceive**: Watchers detect events (email, file drop, social media)
2. **Reason**: Claude Code reads tasks, creates plans, decides actions
3. **Act**: MCP servers and Playwright scripts execute approved actions

---

## 2. Component Inventory

### 2A. Watchers (The Senses) — 11 Scripts

| Watcher | Script | Monitors | Output |
|---------|--------|----------|--------|
| Filesystem | `filesystem_watcher.py` | `/Inbox` folder | Moves `.md` → `/Needs_Action` |
| Gmail | `gmail_watcher.py` | Gmail IMAP IDLE | Creates email tasks + reply drafts |
| Approval | `approval_watcher.py` | `/Approved` folder | Sends emails / creates execution tasks |
| LinkedIn | `linkedin_watcher.py` | `/Needs_Action` | Drafts LinkedIn posts → `/Pending_Approval` |
| Social Media | `social_media_watcher.py` | `/Needs_Action` | Detects Twitter/FB/IG tasks → drafts |
| WhatsApp | `whatsapp_watcher.py` | `/Needs_Action` | Routes WhatsApp tasks → `/Pending_Approval` |
| Dashboard | `dashboard_updater.py` | All folders | Auto-updates `Dashboard.md` every 60s |
| Scheduler | `scheduler.py` | Cron schedule | Gmail poll (5min), daily summary (09:00), CEO briefing (Sunday 22:00) |
| LinkedIn Poster | `linkedin_playwright.py` | `/Approved` | Publishes approved LinkedIn posts |
| Facebook Poster | `facebook_playwright.py` | `/Approved` | Publishes approved Facebook posts |
| WhatsApp Sender | `whatsapp_playwright.py` | `/Approved` | Sends approved WhatsApp messages + AI auto-reply |

### 2B. MCP Servers (The Hands) — 3 Servers

| Server | Protocol | Tools | Purpose |
|--------|----------|-------|---------|
| Gmail MCP | OAuth2 + Gmail API | Send/draft/search emails | Email communication |
| LinkedIn MCP | Playwright browser | Post to LinkedIn feed | Social media publishing |
| Odoo MCP | JSON-RPC (`odoo_mcp_server.py`) | 7 tools (invoices, partners, products, balance summary, search) | Accounting & ERP |

### 2C. Orchestrator & Persistence

| Component | Script | Role |
|-----------|--------|------|
| Orchestrator | `run_all.py` | Launches all 11 watchers with guardian threads |
| Ralph Wiggum | `ralph_wiggum_hook.py` | Stop hook — keeps Claude iterating until tasks complete |
| Auto-restart | Built into `run_all.py` | Up to 10 consecutive restarts per watcher, incident reports on failure |

### 2D. Agent Skills — 6 Skills in `/skills/`

| Skill | File | Description |
|-------|------|-------------|
| Process Task | `process_task.md` | Standard task processing workflow |
| Email Triage | `email_triage.md` | Email classification and routing |
| Social Media Post | `social_media_post.md` | Cross-platform posting (LinkedIn, FB, IG, Twitter) |
| CEO Briefing | `ceo_briefing.md` | Weekly executive briefing with accounting audit |
| Odoo Accounting | `odoo_accounting.md` | Odoo ERP integration via MCP |
| Approval Workflow | `approval_workflow.md` | Human-in-the-loop approval system |

---

## 3. Vault Folder Structure (11 Folders)

```
AI_Employee_Vault/
├── Inbox/               → Drop zone — filesystem watcher moves files out
├── Needs_Action/        → Processing queue — agent's primary work queue
├── Plans/               → Agent plans before executing tasks
├── Pending_Approval/    → Tasks requiring human sign-off (sensitive actions)
├── Approved/            → Human-approved tasks ready for execution
├── Done/                → Completed tasks archive
├── Logs/                → Audit trail (daily task logs, watcher logs, incident reports)
├── Briefings/           → CEO reports and weekly summaries
├── skills/              → Agent Skill definitions (.md files)
├── Media/               → Images for social media posts
├── odoo/                → Odoo Docker configuration
├── gmail_credentials/   → OAuth credentials (gitignored)
├── Dashboard.md         → Real-time system status (auto-updated)
├── Company_Handbook.md  → SOPs and rules (canonical)
├── Business_Goals.md    → Current objectives and metrics
└── CLAUDE.md            → Agent instructions for Claude Code
```

---

## 4. Data Flow Diagrams

### 4A. Email Pipeline
```
Gmail → IMAP IDLE → gmail_watcher.py
  │
  ├─ Sensitive (reply/pay/invoice/urgent)
  │    ├─ Email task → /Needs_Action
  │    └─ Reply draft → /Pending_Approval
  │         │
  │         ▼ (human moves to /Approved)
  │    approval_watcher.py → Gmail API → Send email → /Done
  │
  └─ Non-sensitive (newsletters, info)
       └─ Email task → /Needs_Action → Agent processes → /Done
```

### 4B. Social Media Pipeline
```
Task file in /Needs_Action
  │
  ├─ social_media_watcher.py detects platform keywords
  │    ├─ Twitter? → Draft tweet → /Pending_Approval
  │    ├─ Facebook? → Draft post → /Pending_Approval
  │    └─ Instagram? → Draft caption → /Pending_Approval
  │
  ▼ (human reviews, moves to /Approved)
  │
  ├─ twitter_playwright.py → Posts tweet → /Done
  ├─ facebook_playwright.py → Posts to timeline → /Done
  ├─ instagram_playwright.py → Posts with image → /Done
  └─ linkedin_playwright.py → Posts to feed → /Done
```

### 4C. Accounting Pipeline
```
Claude Code → odoo_mcp_server.py (stdio)
  │
  ├─ odoo_get_invoices → Fetch from Odoo
  ├─ odoo_get_balance_summary → Receivable/Payable/Net
  ├─ odoo_create_invoice → Draft invoice (requires approval to post)
  │
  └─ ceo_briefing.py (Sunday 22:00)
       ├─ Pulls accounting summary from Odoo
       ├─ Scans vault (done tasks, pending, backlog)
       ├─ Generates AI executive summary via Claude CLI
       └─ Saves to /Briefings/CEO_Briefing_YYYY-MM-DD.md
```

### 4D. WhatsApp Pipeline
```
whatsapp_playwright.py (persistent Chromium profile)
  │
  ├─ --watch: Sends approved messages from /Approved
  ├─ --listen: Detects unread → creates tasks in /Pending_Approval
  ├─ --auto-reply: AI replies via Groq Cloud (whitelist-only)
  │    ├─ Conversation history saved per contact (.whatsapp_chats/)
  │    └─ Custom system prompt (ai_system_prompt.txt)
  │
  └─ --setup: First-time QR scan (session saved in .whatsapp_profile/)
```

---

## 5. Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Brain | Claude Code (Sonnet) | Reasoning engine, file I/O, task processing |
| Memory | Obsidian (local Markdown) | Privacy-first, human-readable, version-controllable |
| Watchers | Python (watchdog, imapclient, schedule) | Lightweight, always-on monitoring |
| Browser Automation | Playwright (Chromium) | Social media posting, WhatsApp Web |
| Email | Gmail API + OAuth2 + IMAP IDLE | Real-time email detection, send/receive |
| Accounting | Odoo Community 19 (Docker) + JSON-RPC | Self-hosted ERP, free, full API |
| AI Auto-Reply | Groq Cloud (Llama 3.1 8B) | Free, fast, good for WhatsApp replies |
| Image Processing | Pillow (PIL) | Instagram image resize to 1080x1080 |
| Orchestration | `run_all.py` + threading | Guardian threads, auto-restart, incident reports |
| Persistence | Ralph Wiggum Stop Hook | Keeps Claude iterating until tasks complete |

---

## 6. Safety & Human-in-the-Loop

### Sensitive Action Detection
Keywords that trigger approval workflow:
`reply`, `respond`, `send`, `pay`, `transfer`, `invoice`, `urgent`

### Approval Flow
```
Sensitive action detected
  → File created in /Pending_Approval
  → Human reviews in Obsidian
  → Moves to /Approved (or deletes to reject)
  → Approval watcher executes the action
  → Archived to /Done with audit trail
```

### Safety Rules (from Company_Handbook.md)
1. NEVER send external emails without human approval
2. NEVER execute payments without approval
3. NEVER delete user files — only move between vault folders
4. NEVER access systems outside the vault without instruction
5. Always log actions to `/Logs` for audit trail
6. When uncertain → create request in `/Pending_Approval`

---

## 7. Lessons Learned

### What Worked Well

1. **File-based architecture is surprisingly powerful.** Using `.md` files as the communication protocol between watchers, Claude, and humans made everything debuggable and transparent. You can literally open Obsidian and see the entire system state.

2. **IMAP IDLE >> polling for Gmail.** Switching from 5-minute polling to IMAP IDLE made email detection near-instant. Gmail pushes notifications, no wasted API calls.

3. **Playwright persistent sessions save hours.** Saving browser state (cookies, localStorage) means you only login once per platform. Subsequent runs skip authentication entirely.

4. **Ralph Wiggum pattern is essential.** Without the stop hook, Claude processes one task and quits. With it, Claude keeps working through the entire `/Needs_Action` queue autonomously.

5. **Guardian threads in the orchestrator** prevent cascading failures. One watcher crashing doesn't take down the whole system. Auto-restart with backoff and incident reports made the system self-healing.

6. **Agent Skills as `.md` files** make the AI's capabilities explicit and editable. Want to change how email triage works? Edit `skills/email_triage.md`. No code changes needed.

### Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| Twitter blocks automated clicks (overlay div) | JS `document.querySelector` direct click + overlay `pointerEvents: none` hack |
| WhatsApp Web QR expires frequently | Persistent Chromium profile (`launch_persistent_context`) — QR scan once, reuse forever |
| Instagram requires image for every post | Auto-resize with Pillow (center crop to 1080x1080), fallback to `/Media` folder |
| Gmail OAuth token expiration | Auto-refresh via `google.auth.transport.requests.Request()` before each API call |
| Odoo connection drops | Error handling in MCP server returns `{"error": ...}` gracefully, CEO briefing continues without accounting data |
| Multiple watchers writing to same log | Each watcher has its own dated log file (`gmail_watcher_2026-03-03.log`) |
| Race conditions in file moves | 0.5s delay after `on_created` event + unique timestamp filenames to avoid overwrites |

### What I'd Do Differently

1. **Start with the orchestrator earlier.** I built individual watchers first and integrated later. Building `run_all.py` first would have caught integration issues sooner.

2. **Use a proper message queue instead of file polling.** For production, Redis or SQLite would be more reliable than scanning folders every 30-60 seconds. But for the hackathon, file-based is simpler and more visible.

3. **Add health check endpoints.** Currently you have to read logs to know if a watcher is alive. A simple HTTP health endpoint per watcher would enable better monitoring.

4. **Centralize the `.env` loading.** Every Playwright script has its own `load_env()` function. A shared `config.py` would reduce duplication.

5. **Better error screenshots.** Playwright screenshots on failure are saved but not surfaced to the dashboard. Auto-linking debug screenshots in `Dashboard.md` would speed up troubleshooting.

---

## 8. Metrics & Results

| Metric | Value |
|--------|-------|
| Total Python scripts | 17 |
| Total watchers | 11 |
| MCP servers | 3 (Gmail, LinkedIn, Odoo) |
| Agent Skills | 6 |
| Vault folders | 11 |
| Social platforms integrated | 5 (LinkedIn, Twitter, Facebook, Instagram, WhatsApp) |
| Completed tasks | 9+ |
| Plans created | 7 |
| CEO Briefings generated | 2 |
| Days of audit logs | 6+ (Feb 25 — Mar 3) |
| Lines of Python | ~4,500+ |
| Dependencies | 9 (watchdog, imapclient, google-auth, google-api-python-client, schedule, playwright, groq, python-dotenv, Pillow) |

---

## 9. File Reference

### Core Scripts
| File | Lines | Purpose |
|------|-------|---------|
| `run_all.py` | 305 | Orchestrator with Ralph Wiggum persistence loop |
| `gmail_watcher.py` | 310 | IMAP IDLE real-time email detection |
| `approval_watcher.py` | 237 | Approved task executor (emails + generic) |
| `whatsapp_playwright.py` | 1017 | WhatsApp automation + Groq AI auto-reply |
| `odoo_mcp_server.py` | 398 | Odoo accounting MCP server (7 tools) |
| `ceo_briefing.py` | 377 | Weekly CEO briefing with Odoo + Claude AI |
| `facebook_playwright.py` | 425 | Facebook posting automation |
| `instagram_playwright.py` | 525 | Instagram posting with image resize |
| `twitter_playwright.py` | 516 | Twitter/X posting (multi-strategy click) |
| `linkedin_playwright.py` | 384 | LinkedIn posting automation |
| `post_everywhere.py` | 385 | Multi-platform post orchestrator |
| `social_media_watcher.py` | 250 | Social media task detection + drafting |
| `dashboard_updater.py` | 299 | Live dashboard generation |
| `scheduler.py` | 138 | Cron-style job scheduling |
| `filesystem_watcher.py` | 108 | Inbox file monitoring |
| `linkedin_watcher.py` | 231 | LinkedIn task detection + drafting |
| `ralph_wiggum_hook.py` | 121 | Stop hook for autonomous loops |
| `whatsapp_watcher.py` | 155 | WhatsApp task detection + routing |

---

_Generated on 2026-03-03 by AI Employee (Gold Tier)_
