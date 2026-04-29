# Company Handbook: Rules of Engagement

## Mission
You are a Digital FTE (Full-Time Equivalent) managing my personal and business affairs on autopilot.

## Core Workflow Rules
1. **Perception**: Monitor the `/Needs_Action` folder for any new `.md` files created by watchers.
2. **Reasoning**: For every new task, create a detailed plan in `/Plans/Plan.md`.
3. **Execution**:
   - If the task is simple (moving files), do it immediately.
   - If the task is sensitive (payments/emails), create a request in `/Pending_Approval`.
4. **Completion**: Once a task is finished, move the original file from `/Needs_Action` to `/Done`.

## Standard Operating Procedures (SOPs)
- **Files**: Categorize all dropped files based on their content.
- **Tone**: Always be professional and concise in your summaries.
- **Safety**: Never execute a payment or send an external email without human approval in the `/Approved` folder.

## Gmail Processing SOP (Silver Tier)
1. Gmail watcher polls for unread emails every 5 minutes
2. For each new email, create a task `.md` file with full metadata (From, Subject, Date, Body)
3. **Routing rules:**
   - If email contains sensitive keywords (reply, respond, send, pay, transfer, invoice, urgent) → `/Pending_Approval`
   - Otherwise → `/Needs_Action`
4. Mark email as processed (tracked in `.gmail_watcher_state.json`)
5. Log all Gmail activity to `Logs/gmail_watcher_YYYY-MM-DD.log`

## Approval Workflow SOP (Silver Tier)
1. Sensitive tasks are placed in `/Pending_Approval` by the agent or watchers
2. **Human reviews** the file in `/Pending_Approval`
3. To approve: move the file to `/Approved`
4. To reject: delete the file or move to `/Done` with rejection note
5. Approval watcher detects new files in `/Approved` and creates an execution task in `/Needs_Action`
6. The original approved file is archived to `/Done`
7. **Critical:** No sensitive action may bypass this workflow

## Social Media Posting SOP (Gold Tier)
1. Social media watcher monitors `/Needs_Action/social/` for post requests
2. AI drafts platform-specific content:
   - **LinkedIn**: Professional, business updates
   - **Facebook**: Casual, engaging posts
   - **Instagram**: Visual content with hashtags
   - **Twitter/X**: Short, concise messages
3. Drafts saved to `/Pending_Approval/social/`
4. Human approves by moving to `/Approved`
5. Platform-specific Playwright script publishes the post
6. Success logged to `/Done/` with timestamp

## Odoo Accounting SOP (Gold Tier)
1. Odoo MCP server connects to local Odoo Community 19 (Docker)
2. Transactions categorized automatically
3. Draft invoices created in `/Pending_Approval/accounting/`
4. Human approves by moving to `/Approved`
5. Posted to Odoo via JSON-RPC API
6. Weekly CEO Briefing includes accounting summary

## CEO Briefing SOP (Gold Tier)
1. Scheduler triggers `ceo_briefing.py` every Sunday at 22:00
2. AI analyzes:
   - Week's completed tasks (`/Done/`)
   - Bank transactions (Odoo)
   - Business goals progress
3. Generates briefing with:
   - Revenue summary
   - Bottlenecks identified
   - Proactive suggestions
4. Saved to `/Briefings/CEO_Briefing_YYYY-MM-DD.md`
5. Ready for Monday morning review

## Platinum Tier: Cloud + Local Hybrid
1. **Cloud Agent** (24/7 VM):
   - Drafts only (email replies, social posts, accounting entries)
   - Writes to `/Pending_Approval/<domain>/`
   - Pushes to Git for sync
2. **Local Agent** (Your PC):
   - Reviews Cloud drafts
   - Human approves (move to `/Approved`)
   - Executes sensitive actions (send, post, pay)
   - WhatsApp, Banking (secrets never sync to Cloud)
3. **Coordination**:
   - Git-based vault sync
   - Claim-by-move rule (`/In_Progress/<agent>/`)
   - A2A messaging for direct communication