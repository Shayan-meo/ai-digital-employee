# Skill: Process Task

## Description
Process a task file from /Needs_Action — read it, create a plan, execute it, and move to /Done.

## Trigger
New .md file appears in /Needs_Action

## Steps
1. Read the task file from /Needs_Action
2. Analyze the content and determine task type (simple vs sensitive)
3. Create a plan file in /Plans/<task_name>_plan.md
4. If sensitive (payments, emails, account changes): move to /Pending_Approval and STOP
5. If simple: execute the task immediately
6. Move original file from /Needs_Action to /Done
7. Append completion metadata (timestamp, status, summary)
8. Log the action in /Logs/YYYY-MM-DD_task_log.md
9. Update Dashboard.md

## Completion
Output TASK_COMPLETE when the task queue is empty.
