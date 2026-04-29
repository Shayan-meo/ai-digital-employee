# Platinum Tier Demo Script

## Demo Flow: Email → Cloud Draft → Local Approve → Send

This script guides you through the Platinum Tier demo that satisfies the minimum passing gate.

---

## Prerequisites

- [ ] Cloud VM running with `cloud_watcher.py`
- [ ] Local machine with `local_agent.py`
- [ ] Git repository configured for sync
- [ ] Gmail MCP configured on Local
- [ ] Both agents can communicate (Git sync working)

---

## Demo Steps

### Step 1: Stop Local Agent (Simulate Offline)

```bash
# On Local machine
# Stop the local agent
Ctrl+C  # Stop local_agent.py

# Verify it's offline
python local\local_agent.py status
# Should show: "Local agent offline"
```

**Narration:** "First, we simulate the Local agent being offline. This could be because the user's laptop is closed, network is down, or they're in a meeting."

---

### Step 2: Send Test Email

Send an email to your Gmail address with:
- **Subject:** `Test Platinum Demo - Invoice Request`
- **Body:** `Hi, can you please send me the invoice for January? Thanks.`

**Narration:** "Now we send a test email. The Cloud agent, which runs 24/7 on the VM, will detect this email."

---

### Step 3: Cloud Detects Email

```bash
# On Cloud VM
cd ~/ai_employee_vault
pm2 logs cloud-watcher --lines 50
```

You should see:
```
[Cloud Watcher] Checking Gmail for new messages...
[Cloud Watcher] New email detected: Test Platinum Demo - Invoice Request
[Cloud Watcher] Creating draft in /Pending_Approval/email/
```

**Narration:** "The Cloud agent detected the email and created a draft reply. Notice it's draft-only - Cloud cannot send directly."

---

### Step 4: Cloud Creates Draft

Check the draft file:

```bash
# On Cloud VM
ls Pending_Approval/email/
cat Pending_Approval/email/EMAIL_*.md
```

You'll see a draft like:
```markdown
---
type: email_draft
from: sender@example.com
subject: Test Platinum Demo - Invoice Request
status: pending_approval
agent: cloud
---

# Email Draft (Cloud Agent)

## Suggested Reply (Draft - Requires Local Approval)

Dear Customer,

Thank you for your inquiry. Please find attached your invoice for January 2026.

Best regards,
[Your Name]

---
## Action Required
Move this file to `/Approved` to send the reply.
```

**Narration:** "The Cloud agent created a professional draft reply. But it requires Local approval before sending - this is the security boundary."

---

### Step 5: Cloud Pushes to Git

```bash
# On Cloud VM
cd ~/ai_employee_vault
git add -A
git commit -m "Draft created: Email invoice request"
git push origin main
```

**Narration:** "The Cloud agent pushes the draft to Git. This syncs the vault to the Local machine."

---

### Step 6: Start Local Agent (Back Online)

```bash
# On Local machine
python local\local_agent.py
```

You should see:
```
[Local Agent] Starting Approval Watcher
[Local Agent] Checking /Pending_Approval/
[Local Agent] Found 1 pending approval(s)
```

**Narration:** "The Local agent is back online. It immediately detects the pending approval from Git."

---

### Step 7: User Reviews Draft

On Local machine, open the draft:
```bash
notepad Pending_Approval\email\EMAIL_*.md
```

Review the draft reply.

**Narration:** "The user reviews the draft. They can edit it if needed, or approve as-is."

---

### Step 8: User Approves (Move to /Approved)

```bash
# On Local machine
move Pending_Approval\email\EMAIL_*.md Approved\
```

**Narration:** "The user approves by moving the file to /Approved. This triggers the Local agent to send the email."

---

### Step 9: Local Sends Email

Check Local agent logs:
```bash
# In local_agent.py terminal
# Should see:
[Local Agent] Claimed for local execution: EMAIL_*.md
[Local Agent] Sending email to sender@example.com
[Local Agent] Email sent successfully
[Local Agent] Task archived: EMAIL_*.md (Success: true)
```

**Narration:** "The Local agent executed the send action using Gmail MCP. The email is now sent!"

---

### Step 10: Task Moved to /Done

```bash
# On Local machine
ls Done\email\
cat Done\email\EMAIL_*.md
```

You'll see:
```markdown
---
**Completed:** 2026-03-04T12:34:56
**Status:** SUCCESS
```

**Narration:** "The completed task is archived in /Done with a success status."

---

### Step 11: Local Pushes to Git

```bash
# On Local machine
git add -A
git commit -m "Email sent: Invoice request reply"
git push origin main
```

**Narration:** "The Local agent pushes the completion status to Git."

---

### Step 12: Cloud Pulls and Sees Completion

```bash
# On Cloud VM
git pull origin main
pm2 logs cloud-watcher --lines 20
```

You should see:
```
[Cloud Watcher] Pulled from Git
[Cloud Watcher] Task completed: EMAIL_*.md → Done/
```

**Narration:** "The Cloud agent pulls the update and sees the task is complete. The loop is closed!"

---

## Demo Complete! ✅

### Summary

1. ✅ Email arrived while Local was OFFLINE
2. ✅ Cloud drafted reply + wrote approval file
3. ✅ Local came ONLINE, user approved
4. ✅ Local executed send via MCP
5. ✅ Task logged and moved to /Done
6. ✅ Cloud pulled and saw completion

---

## Demo Video Recording Tips

### Recording Setup
- Use OBS Studio or similar screen recording software
- Record both Cloud VM terminal and Local machine terminal
- Show timestamps clearly

### Video Structure (5-10 minutes)

| Section | Duration | Content |
|---------|----------|---------|
| Intro | 1 min | Explain Platinum Tier architecture |
| Setup | 1 min | Show Cloud VM + Local machine |
| Demo | 5 min | Run through all 12 steps |
| Summary | 1 min | Highlight key features |
| Q&A | 2 min | Address potential questions |

### Key Points to Emphasize

1. **Security Boundary**: Cloud can only draft, Local must approve
2. **24/7 Operation**: Cloud runs continuously on VM
3. **Git Sync**: Decentralized communication, no central server
4. **Claim-by-Move**: Prevents double-work between agents
5. **Audit Trail**: All actions logged in vault

---

## Troubleshooting

### Cloud Watcher Not Detecting Email
```bash
# Check Gmail API credentials
cat cloud/.env | grep GMAIL

# Check watcher logs
pm2 logs cloud-watcher
```

### Git Sync Failing
```bash
# On both machines
git status
git pull --rebase
git push
```

### Local Agent Not Detecting Approval
```bash
# Check folder structure
ls Pending_Approval\email\

# Restart local agent
Ctrl+C
python local\local_agent.py
```

### Email Not Sending
```bash
# Check Gmail MCP
cat .env | grep GMAIL

# Check logs
cat Logs\local_agent_*.log
```

---

## Submission Checklist

- [ ] Demo video recorded (5-10 minutes)
- [ ] Video uploaded to YouTube/Google Drive
- [ ] GitHub repository updated with Platinum code
- [ ] README.md updated with Platinum architecture
- [ ] Security disclosure completed
- [ ] Hackathon form submitted: https://forms.gle/JR9T1SJq5rmQyGkGA

---

## Next Steps After Demo

1. **Production Hardening**
   - Add retry logic for failed sends
   - Implement rate limiting
   - Add monitoring alerts

2. **Scale**
   - Add more Cloud agents (specialized by domain)
   - Implement load balancing
   - Add database for state persistence

3. **Security**
   - Add 2FA for approvals
   - Implement encryption at rest
   - Add intrusion detection

4. **Features**
   - Add voice notifications
   - Implement mobile app for approvals
   - Add analytics dashboard

---

## Questions?

For hackathon submission and support, refer to the official hackathon portal.
