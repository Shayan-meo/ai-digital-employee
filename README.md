# Personal AI Employee

> An autonomous AI agent that manages your personal and business affairs through a file-based vault system — powered by Claude Code.

**Hackathon:** Personal AI Employee Hackathon
**Tier:** Platinum 💎
**Built with:** Claude Code + MCP + Playwright + Odoo + Python + Cloud VM + Git Sync

---

## What It Does

This system acts as a **Digital Full-Time Employee** that:

- 📧 **Reads your Gmail** — fetches unread emails, creates task files, and drafts context-aware replies
- 💼 **Posts to LinkedIn** — drafts business updates and publishes them automatically after your approval
- 📋 **Processes tasks** — any file dropped in `/Inbox` gets a plan, gets executed, gets archived
- ✅ **Human-in-the-loop** — sensitive actions (emails, posts) always wait for your approval
- 📊 **Live Dashboard** — real-time vault status, pending approvals, system health
- 📈 **Weekly CEO Briefing** — auto-generated every Sunday night, ready Monday morning
- 🔄 **Self-healing** — if any watcher crashes, it auto-restarts (Ralph Wiggum persistence loop)

---

## Architecture

```
AI_Employee_Vault/
├── Inbox/                  # Drop zone — filesystem_watcher picks up files
├── Needs_Action/           # AI work queue — all watchers create tasks here
├── Plans/                  # Plan.md created for every task before execution
├── Pending_Approval/       # Sensitive actions wait here for human review
├── Approved/               # Move file here to approve → action executes
├── Done/                   # Completed tasks archive
├── Logs/                   # Full audit trail — all watcher + task logs
├── Briefings/              # Weekly CEO briefings
├── Dashboard.md            # Live status (auto-updated every 60s)
├── Company_Handbook.md     # AI rules and SOPs
├── Business_Goals.md       # Objectives and metrics
├── skills/                 # Agent Skills (SKILL.md files)
├── odoo/                   # Odoo Community 19 Docker setup
├── odoo_mcp_server.py      # Odoo MCP server (JSON-RPC)
├── ralph_wiggum_hook.py    # Stop hook for autonomous task loops
└── CLAUDE.md               # Agent skills and instructions
```

### Complete Pipeline

```
Email arrives
  └─► gmail_watcher.py
        ├─► /Needs_Action/email_*.md        (informational record)
        └─► /Pending_Approval/reply_*.md    (AI-drafted reply, awaits approval)
                  │
                  │  You move to /Approved
                  ▼
        approval_watcher.py ─► /Needs_Action/ ─► execute & send

File dropped in /Inbox
  └─► filesystem_watcher.py
        ├─► /Plans/<task>_plan.md
        └─► /Done/<task>.md

LinkedIn post requested
  └─► linkedin_watcher.py
        └─► /Pending_Approval/linkedin_post_*.md   (AI-drafted post)
                  │
                  │  You move to /Approved
                  ▼
        linkedin_playwright.py ─► Published on LinkedIn ✅

Every Sunday 22:00
  └─► ceo_briefing.py
        └─► /Briefings/CEO_Briefing_YYYY-MM-DD.md
```

---

## Watchers & Scripts

| Script | Purpose | Tier |
|--------|---------|------|
| `filesystem_watcher.py` | Watches `/Inbox`, runs full pipeline (Plan → Done) | Bronze |
| `gmail_watcher.py` | Polls Gmail every 5 min, creates tasks + reply drafts | Silver |
| `approval_watcher.py` | Watches `/Approved`, triggers execution of approved tasks | Silver |
| `linkedin_watcher.py` | Detects LinkedIn post tasks, drafts posts via Claude | Silver |
| `linkedin_playwright.py` | Publishes approved posts to LinkedIn via Playwright | Silver |
| `scheduler.py` | Cron jobs: Gmail (5 min), daily summary (09:00), CEO briefing (Sun 22:00) | Silver/Gold |
| `dashboard_updater.py` | Updates Dashboard.md every 60s with live vault stats | Silver |
| `social_media_watcher.py` | Detects Twitter/Facebook/Instagram tasks, drafts platform-specific posts | Gold |
| `ceo_briefing.py` | Generates weekly CEO briefing with AI executive summary | Gold |
| `run_all.py` | Orchestrator — starts all watchers + Ralph Wiggum auto-restart loop | Gold |
| `odoo_mcp_server.py` | Odoo MCP server — accounting via JSON-RPC | Gold |
| `ralph_wiggum_hook.py` | Stop hook — keeps agent iterating until task queue empty | Gold |
| `post_everywhere.py` | Universal dispatcher — posts to all social platforms | Gold |
| `facebook_playwright.py` | Publishes approved posts to Facebook via Playwright | Gold |
| `instagram_playwright.py` | Publishes approved posts to Instagram via Playwright | Gold |
| `twitter_playwright.py` | Publishes approved tweets to Twitter/X via Playwright | Gold |

---

## Setup

### 1. Prerequisites

```bash
# Python 3.11+
pip install -r requirements.txt
python -m playwright install chromium
```

### 2. Claude Code

```bash
npm install -g @anthropic/claude-code
```

### 3. Odoo Community (Accounting)

```bash
cd odoo
docker compose up -d
# Access at http://localhost:8069 (admin/admin)
# Create a database named "odoo" on first run
```

### 4. Environment Variables

Create a `.env` file in the vault root (never commit this):

```env
# LinkedIn (Playwright automation)
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password
```

### 4. Gmail MCP

Configure `.mcp.json` with your Gmail OAuth credentials:

```json
{
  "mcpServers": {
    "gmail": {
      "command": "cmd",
      "args": ["/c", "npx", "-y", "@gongrzhe/server-gmail-autoauth-mcp"],
      "env": {
        "GMAIL_OAUTH_PATH": "path/to/client_secret.json",
        "GMAIL_CREDENTIALS_PATH": "path/to/credentials.json"
      }
    }
  }
}
```

Follow [Google OAuth setup guide](https://developers.google.com/gmail/api/quickstart/python) to generate credentials.

### 5. LinkedIn Session (First Time)

```bash
python linkedin_playwright.py --test-login
```

Browser will open, log in once — session is saved for future use.

---

## Running the System

### Start Everything

```bash
python run_all.py
```

This launches all 7 watchers simultaneously with auto-restart on crash.

### Individual Scripts

```bash
python filesystem_watcher.py      # Watch /Inbox only
python gmail_watcher.py           # Poll Gmail only
python linkedin_playwright.py --watch  # Watch /Approved for posts
python ceo_briefing.py            # Generate CEO briefing now
python dashboard_updater.py       # Update Dashboard.md once
```

---

## How to Use

### Process a Task
Drop any file into `/Inbox` → AI creates a plan → executes → archives to `/Done`

### Approve an Email Reply
1. Check `/Pending_Approval/reply_*.md`
2. Review/edit the drafted reply
3. Move file to `/Approved` → reply executes

### Approve a LinkedIn Post
1. Check `/Pending_Approval/linkedin_post_*.md`
2. Review/edit the post text
3. Move file to `/Approved` → post publishes to LinkedIn

### Request a LinkedIn Post Manually
Create a `.md` file in `/Needs_Action` with the word "linkedin" or "post" in the content → `linkedin_watcher.py` will draft and queue it.

### View System Status
Open `Dashboard.md` — auto-refreshed every 60 seconds showing:
- Emails pending reply
- LinkedIn posts scheduled
- Active task queue
- Vault health

---

## Safety & Security

| Rule | Implementation |
|------|---------------|
| No auto-send emails | All replies go to `/Pending_Approval` first |
| No auto-post | All LinkedIn posts require manual `/Approved` move |
| No file deletion | Files only move between folders, never deleted |
| Audit trail | Every action logged to `/Logs/YYYY-MM-DD_task_log.md` |
| Credential safety | `.env` in `.gitignore`, never committed |
| Rate limiting | Gmail polls max every 5 minutes |

---

## Hackathon Tier Checklist

### Bronze ✅
- [x] Vault with 7+ folders
- [x] Dashboard.md + Company_Handbook.md
- [x] Claude Code vault access
- [x] Filesystem watcher running
- [x] Claude reasoning loop (Plan.md per task)
- [x] Tasks processed and archived

### Silver ✅
- [x] Gmail watcher + reply drafting
- [x] LinkedIn watcher + post drafting
- [x] Playwright LinkedIn posting
- [x] Human-in-the-loop approval workflow
- [x] MCP servers (Gmail + LinkedIn)
- [x] Cron scheduling (scheduler.py)
- [x] Live Dashboard with email/social stats
- [x] Agent Skills in CLAUDE.md

### Gold 🥇 ✅
- [x] Full cross-domain integration (Personal + Business)
- [x] Odoo Community 19 accounting (Docker + JSON-RPC MCP server)
- [x] Facebook + Instagram integration (Playwright)
- [x] Twitter/X integration (Playwright)
- [x] 3 MCP servers (Gmail, LinkedIn, Odoo)
- [x] Weekly Business & Accounting Audit with CEO Briefing
- [x] Error recovery + graceful degradation (auto-restart, incident reports)
- [x] Comprehensive audit logging
- [x] Ralph Wiggum stop hook for autonomous multi-step task completion
- [x] Architecture documentation + lessons learned
- [x] 6 Agent Skills (skills/ folder)

---

## Tech Stack

| Technology | Use |
|-----------|-----|
| Claude Code | AI reasoning, plan generation, reply drafting |
| Python 3.13+ | All watcher scripts |
| Playwright | Social media browser automation (LinkedIn, FB, Insta, Twitter) |
| Odoo Community 19 | Self-hosted ERP/accounting (Docker) |
| watchdog | Filesystem event monitoring |
| schedule | Cron-style job scheduling |
| Gmail MCP | Gmail read/send via `@gongrzhe/server-gmail-autoauth-mcp` |
| LinkedIn MCP | LinkedIn via `adhikasp/mcp-linkedin` |
| Odoo MCP | Accounting via custom `odoo_mcp_server.py` (JSON-RPC) |

---

## Agent Skills

| Skill | File | Trigger |
|-------|------|---------|
| Process Task | `skills/process_task.md` | New file in /Needs_Action |
| Email Triage | `skills/email_triage.md` | New Gmail detected |
| Social Media Post | `skills/social_media_post.md` | Post request or daily summary |
| CEO Briefing | `skills/ceo_briefing.md` | Sunday 22:00 schedule |
| Odoo Accounting | `skills/odoo_accounting.md` | Accounting queries/invoices |
| Approval Workflow | `skills/approval_workflow.md` | Sensitive action detected |

---

## Lessons Learned

1. **File-based architecture is powerful** — Simple .md files as the protocol between watchers, agent, and human makes debugging trivial and everything auditable.

2. **Watchers solve the "lazy agent" problem** — Without watchers, the AI just waits. Lightweight Python scripts that monitor folders/APIs wake the agent proactively.

3. **Human-in-the-loop is essential** — The /Pending_Approval -> /Approved workflow prevents irreversible damage while allowing autonomous operation for safe tasks.

4. **Ralph Wiggum persistence** — The stop hook that re-injects prompts when tasks remain is the key to true autonomous multi-step execution.

5. **MCP servers are the "hands"** — They bridge Claude's reasoning with real-world actions (email, accounting, social media).

6. **Docker simplifies Odoo** — Running Odoo in Docker avoids dependency hell and makes setup reproducible across machines.

7. **Error recovery is non-negotiable** — Auto-restart with max retries and incident reports ensures the system stays up even when individual watchers crash.

8. **Agent Skills formalize knowledge** — Converting AI functionality into structured SKILL.md files makes the agent's capabilities explicit and teachable.

---

## License

MIT — Built for the Personal AI Employee Hackathon 0 by Panaversity.
