# Skill: Approval Workflow

## Description
Handle human-in-the-loop approval for sensitive actions.

## Trigger
Sensitive task detected (payments, emails, social posts, account changes).

## Steps
1. Create approval request file in /Pending_Approval with full context
2. STOP and wait — do NOT proceed without approval
3. Human reviews the file
4. To approve: human moves file to /Approved
5. Approval watcher detects the file → creates execution task in /Needs_Action
6. Original approved file archived to /Done
7. Agent processes the approved task normally

## Safety Rules
- NEVER skip approval for sensitive actions
- NEVER send external emails without approval
- NEVER execute payments without approval
- When uncertain, route to /Pending_Approval
