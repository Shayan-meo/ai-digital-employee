# Skill: Email Triage

## Description
Process incoming emails — categorize, route to correct folder, and create task files.

## Trigger
Gmail watcher detects new unread email

## Steps
1. Read email metadata (From, Subject, Date, Body)
2. Check for sensitive keywords: reply, respond, send, pay, transfer, invoice, urgent
3. If sensitive → create task in /Pending_Approval with full email metadata
4. If informational → create task in /Needs_Action
5. Mark email as processed in .gmail_watcher_state.json
6. Log activity to Logs/gmail_watcher_YYYY-MM-DD.log

## Safety
NEVER auto-reply to emails. Always route through approval workflow.
