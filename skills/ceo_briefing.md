# Skill: CEO Briefing

## Description
Generate weekly CEO briefing with business and accounting audit.

## Trigger
Every Sunday at 22:00 (scheduled by scheduler.py), or on-demand.

## Steps
1. Scan vault: /Done (completed tasks), /Pending_Approval, /Needs_Action (backlog)
2. Read task logs from past 7 days
3. Query Odoo for accounting data (invoices, receivables, payables)
4. Generate AI executive summary via Claude CLI
5. Save briefing to /Briefings/CEO_Briefing_YYYY-MM-DD.md

## Sections
- Weekly Highlights
- Bottlenecks / Blockers
- Action Required (items needing CEO decision)
- Accounting Summary (from Odoo)
- System Health
- Recommended Focus

## Output
Markdown file in /Briefings ready for Monday morning review.
