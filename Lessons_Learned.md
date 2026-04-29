# Lessons Learned — AI Employee Vault

**Project:** Personal AI Employee (Hackathon Gold Tier)
**Author:** Muhammad Shayan
**Last Updated:** 2026-03-09

---

## 1. Playwright Browser Automation — Social Media

### Challenge
Each social media platform (LinkedIn, Twitter, Instagram, Facebook) has different DOM structures, login flows, and anti-bot measures. A single generic automation approach does not work.

### What We Learned
- **LinkedIn** rebuilds its DOM after image upload. The editor (``.ql-editor``) disappears and must be re-found. LinkedIn also shows an image crop/edit screen with a "Done" or "Next" button that must be clicked before returning to the composer.
- **Twitter/X** has multi-step challenge-based login (email → username → password → verification). A static login script fails — dynamic challenge detection was required.
- **Instagram** requires mobile viewport emulation and works most reliably through the mobile web interface.
- **Facebook** frequently changes selectors; multiple fallback selectors per action are essential.
- **`set_input_files()` freezes Playwright** on LinkedIn — `page.expect_file_chooser()` context manager is the correct approach for file upload dialogs.

### Best Practice
- Always use multiple CSS selectors per UI element (3-7 fallbacks)
- Add retry loops with increasing wait times (not just timeouts)
- Save debug screenshots at each critical step for post-mortem analysis
- Use `force=True` on click actions as fallback when normal clicks fail

---

## 2. Odoo Community Integration via JSON-RPC

### Challenge
Integrating Odoo 19 Community Edition with our vault system required bridging two very different architectures — a file-based Obsidian vault and a database-driven ERP.

### What We Learned
- Odoo's JSON-RPC API requires exact model names (e.g., `account.move` for invoices, `account.payment` for payments). Field names differ between Odoo versions.
- **Draft-only approach is critical** for HITL (Human-in-the-Loop) safety: MCP server creates invoices/payments in draft state, human approves in Odoo UI before posting.
- Docker deployment (Odoo + PostgreSQL) is the cleanest local setup — avoids Python dependency conflicts with the vault's own Python environment.
- Session authentication (`/web/session/authenticate`) must happen before every RPC batch — sessions expire.

### Best Practice
- Always create financial records as drafts — never auto-post
- Keep MCP server stateless (authenticate per request batch)
- Map vault task IDs to Odoo record IDs for traceability

---

## 3. Ralph Wiggum Loop (Stop-Hook Pattern)

### Challenge
Getting Claude Code to autonomously process multiple tasks without stopping after each one.

### What We Learned
- The stop-hook intercepts Claude's stop event and checks `/Needs_Action` for remaining tasks. If tasks remain, it re-injects a prompt to continue.
- **Max iterations (10) are essential** — without a cap, the loop can run indefinitely on edge cases (e.g., a task that keeps failing and never moves to `/Done`).
- The `TASK_COMPLETE` promise marker gives Claude an explicit way to signal "I'm done" rather than relying solely on folder state.
- State file (`.ralph_wiggum_state.json`) persists iteration count across hook invocations.

### Best Practice
- Always set a max iteration limit
- Use both file-based (folder check) and promise-based (TASK_COMPLETE) completion detection
- Log every iteration for debugging infinite-loop scenarios

---

## 4. MCP Server Architecture

### Challenge
Configuring multiple MCP servers (Gmail, Odoo, Social Media) to work together through Claude Code.

### What We Learned
- Each MCP server should be single-responsibility: one for email actions, one for Odoo/accounting, one for social media.
- MCP servers must be registered in `.claude/mcp.json` with proper environment variables.
- Error handling in MCP servers is critical — a crashed MCP server blocks all tools that depend on it.
- For browser-based MCP (Playwright), headless mode is faster but headed mode is necessary for debugging and for platforms requiring visual verification (CAPTCHAs).

### Best Practice
- Keep MCP servers independent — failure in one shouldn't affect others
- Use environment variables for credentials, never hardcode
- Implement health checks and graceful shutdown

---

## 5. File-Based Orchestration

### Challenge
Managing complex multi-step workflows using only markdown files and folder movements.

### What We Learned
- The folder pipeline (`/Inbox → /Needs_Action → /Plans → /Pending_Approval → /Approved → /Done`) is surprisingly robust for task management.
- **Naming conventions matter**: `linkedin_post_*.md`, `email_task_*.md` — watchers rely on glob patterns to find their files.
- Race conditions can occur when multiple watchers process the same file. File locking or atomic moves help prevent this.
- Appending metadata (timestamps, status, result) to completed task files creates a self-documenting audit trail.

### Best Practice
- Use consistent file naming: `{type}_{source}_{timestamp}.md`
- Append (never overwrite) completion metadata to task files
- Keep `/Needs_Action` as the single source of truth for pending work

---

## 6. Error Recovery and Graceful Degradation

### Challenge
External APIs (Gmail, social media platforms) are unreliable — network timeouts, rate limits, authentication failures happen regularly.

### What We Learned
- **Exponential backoff** is essential for API retries (1s → 2s → 4s → 8s → max 60s).
- When an API is completely down, tasks should be queued locally (`/Queue` folder) rather than failing permanently.
- The `/Queue` folder acts as a dead-letter queue — a scheduled job periodically retries queued tasks.
- Logging every failure with full context (error type, parameters, retry count) makes debugging 10x faster.

### Best Practice
- Implement `retry_handler.py` as a shared utility for all watchers
- Queue failed tasks rather than discarding them
- Set maximum retry limits to prevent infinite retry loops

---

## 7. Cross-Domain Integration

### Challenge
Making personal (Gmail, WhatsApp, Bank) and business (Social Media, Odoo, Tasks) systems work together seamlessly.

### What We Learned
- A WhatsApp message from a client can trigger a chain: check bank for payment → update Odoo invoice → create social media thank-you post. This requires watchers to create follow-up tasks for other watchers.
- The vault's folder structure naturally supports cross-domain flows — a task file can contain instructions for multiple systems.
- `post_everywhere.py` as a universal poster simplified social media — instead of calling each platform separately, one script handles all.

### Best Practice
- Design tasks as self-contained units with all needed context in the markdown file
- Use a coordinator pattern: one task can spawn follow-up tasks in `/Needs_Action`
- Keep the `Dashboard.md` updated as the single status view across all domains

---

## 8. Security and HITL Workflow

### Challenge
Preventing the AI from taking irreversible actions (sending emails, making payments) without human review.

### What We Learned
- The `/Pending_Approval → /Approved` workflow is the most important safety mechanism.
- Keyword detection for sensitive actions (reply, send, pay, transfer, invoice) works well for routing to approval.
- **Never auto-reply to emails** — even if the intent seems clear, always route through approval.
- Session files (`.linkedin_session`, Gmail tokens) should be treated as secrets — never log or commit them.

### Best Practice
- Default to requiring approval when uncertain
- Log approval decisions for audit trail
- Rotate and protect session/credential files

---

## Summary of Key Takeaways

| # | Lesson | Impact |
|---|--------|--------|
| 1 | Use `expect_file_chooser()` not `set_input_files()` for Playwright uploads | Fixed LinkedIn DOM freeze |
| 2 | Multiple fallback CSS selectors per UI element | 90%+ reliability across platforms |
| 3 | Draft-only for financial records in Odoo | HITL safety guaranteed |
| 4 | Ralph Wiggum loop with max iterations | Autonomous multi-task processing |
| 5 | File-based orchestration with consistent naming | Robust, debuggable workflow |
| 6 | Exponential backoff + local queue for failures | Zero task loss on API downtime |
| 7 | Cross-domain tasks spawn follow-up tasks | Seamless integration |
| 8 | Always route sensitive actions through approval | Human stays in control |
