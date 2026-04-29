# Platinum Tier Implementation Plan

## Overview
Transform the AI Employee from local-only to a **Cloud + Local hybrid system** that runs 24/7 with proper work-zone specialization.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLOUD VM (24/7)                          │
│                    (Oracle Cloud Free Tier)                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Gmail Watcher  │  │  Social Watcher │  │  Cloud Agent    │ │
│  │  (Email Triage) │  │  (Draft Posts)  │  │  (Claude Code)  │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘ │
│           │                    │                    │           │
│           └────────────────────┼────────────────────┘           │
│                                │                                │
│                    ┌───────────▼───────────┐                    │
│                    │   /Updates/ Folder    │                    │
│                    │   (Cloud → Local)     │                    │
│                    └───────────┬───────────┘                    │
│                                │                                │
│                    ┌───────────▼───────────┐                    │
│                    │   Git Sync (Push)     │                    │
│                    └───────────┬───────────┘                    │
└────────────────────────────────┼────────────────────────────────┘
                                 │
                          (Git Push/Pull)
                                 │
┌────────────────────────────────┼────────────────────────────────┐
│                    LOCAL MACHINE (Your PC)                      │
├────────────────────────────────┼────────────────────────────────┤
│                    ┌───────────▼───────────┐                    │
│                    │   Git Sync (Pull)     │                    │
│                    └───────────┬───────────┘                    │
│                                │                                │
│                    ┌───────────▼───────────┐                    │
│                    │   /Updates/ Folder    │                    │
│                    │   (Merge to Dashboard)│                    │
│                    └───────────┬───────────┘                    │
│                                │                                │
│           ┌────────────────────┼────────────────────┐           │
│           │                    │                    │           │
│  ┌────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐ │
│  │ Approval Agent  │  │  WhatsApp MCP   │  │  Banking MCP    │ │
│  │  (Human Review) │  │  (Send Messages)│  │  (Payments)     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Work-Zone Specialization

### Cloud Agent Responsibilities
| Domain | Actions | Restrictions |
|--------|---------|--------------|
| **Email** | Read, categorize, draft replies | Cannot send (draft-only) |
| **Social Media** | Create post drafts, schedule | Cannot publish (requires Local approval) |
| **Odoo Accounting** | Create draft invoices, categorize transactions | Cannot post payments (requires Local approval) |
| **Monitoring** | 24/7 watchers, health checks | - |

### Local Agent Responsibilities
| Domain | Actions | Restrictions |
|--------|---------|--------------|
| **Approvals** | Review Cloud drafts, approve/reject | - |
| **WhatsApp** | Send approved messages | Requires WhatsApp session (never syncs to Cloud) |
| **Banking/Payments** | Execute payments | Requires banking credentials (never sync to Cloud) |
| **Dashboard** | Merge Cloud updates, display status | Single-writer rule |

---

## Implementation Phases

### Phase 1: Git-Based Vault Sync
- [ ] Create `/cloud/` directory structure
- [ ] Setup Git repository for vault sync
- [ ] Configure `.gitignore` for secrets
- [ ] Implement `/Updates/` folder for Cloud→Local communication
- [ ] Implement claim-by-move rule with `/In_Progress/<agent>/`

### Phase 2: Cloud VM Deployment
- [ ] Create Oracle Cloud Free Tier VM (or AWS Free Tier)
- [ ] Install Docker, Python, Node.js on VM
- [ ] Deploy Odoo Community on VM with HTTPS
- [ ] Setup Cloud Agent watchers (Gmail, Social)
- [ ] Configure PM2 for process management

### Phase 3: Security & Coordination
- [ ] Implement secrets management (never sync)
- [ ] Create agent coordination protocol
- [ ] Setup health monitoring & auto-restart
- [ ] Implement graceful degradation

### Phase 4: Platinum Demo
- [ ] Demo: Email arrives → Cloud drafts → Local approves → Send
- [ ] Record demo video
- [ ] Update documentation

---

## Security Rules

### NEVER Sync to Cloud
```
.env
gmail_credentials/
*.session (WhatsApp, Instagram, LinkedIn, Facebook, Twitter)
banking credentials
odoo_mcp_server.py (Local config)
```

### Git-Only Sync
```
*.md (all markdown files)
*.json (config only, no secrets)
*.py (scripts)
```

---

## Folder Structure (Platinum)

```
AI_Employee_Vault/
├── .git/                          # Git sync enabled
├── .env                           # NEVER sync (.gitignore)
├── .gitignore                     # Security rules
│
├── Inbox/                         # Sync to Cloud
├── Needs_Action/                  # Sync to Cloud
│   └── <domain>/                  # Domain-specific subfolders
├── In_Progress/                   # Claim-by-move coordination
│   ├── cloud/                     # Cloud agent claims
│   └── local/                     # Local agent claims
├── Pending_Approval/              # Cloud drafts → Local approval
├── Approved/                      # Local approves
├── Done/                          # Sync to Cloud (audit)
├── Plans/                         # Sync to Cloud
├── Updates/                       # Cloud→Local communication
├── Signals/                       # Alternative: Cloud signals
│
├── cloud/                         # Cloud-specific config
│   ├── .env                       # Cloud secrets (different from Local)
│   ├── cloud_watcher.py
│   └── cloud_mcp_config.json
│
├── local/                         # Local-specific config
│   ├── .env                       # Local secrets (never sync)
│   ├── approval_watcher.py
│   └── local_mcp_config.json
│
└── Logs/                          # Sync to Cloud (audit trail)
```

---

## Claim-by-Move Rule

```
1. Cloud agent sees task in /Needs_Action/email.md
2. Cloud moves to /In_Progress/cloud/email.md
3. Other agents MUST ignore this file
4. Cloud processes, creates draft in /Pending_Approval/
5. Local reviews, moves to /Approved/
6. Local moves to /In_Progress/local/email.md
7. Local executes send via MCP
8. Move to /Done/
```

---

## Cloud VM Setup (Oracle Cloud Free Tier)

### VM Specifications
- **Shape**: VM.Standard.A1.Flex (ARM, 4 OCPU, 24GB RAM - Free)
- **OS**: Ubuntu 22.04 LTS
- **Storage**: 200GB block volume (Free)

### Installation Steps
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Python 3.13
sudo apt install -y python3.13 python3.13-venv python3-pip

# Install Node.js 24 LTS
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt install -y nodejs

# Install PM2
sudo npm install -g pm2

# Clone vault repo
git clone <your-repo> ~/ai_employee_vault
cd ~/ai_employee_vault

# Setup Odoo (Docker)
docker run -d -p 8069:8069 --name odoo -e ODOO_ADMIN_PASSWORD=admin odoo:19.0

# Start watchers with PM2
pm2 start cloud_watcher.py --interpreter python3
pm2 start cloud_orchestrator.py --interpreter python3
pm2 save
pm2 startup
```

---

## Success Criteria (Platinum Demo)

**Minimum Passing Gate:**
1. Email arrives while Local is OFFLINE
2. Cloud agent drafts reply + writes approval file
3. Local comes ONLINE, user approves
4. Local executes send via MCP
5. Task logged and moved to /Done

---

## Estimated Timeline

| Phase | Tasks | Time |
|-------|-------|------|
| Phase 1 (Git Sync) | Folder structure, Git setup, claim-by-move | 8-10 hours |
| Phase 2 (Cloud VM) | VM setup, Odoo deploy, watchers | 12-15 hours |
| Phase 3 (Security) | Secrets mgmt, coordination, health | 10-12 hours |
| Phase 4 (Demo) | End-to-end demo, recording | 5-8 hours |
| **Total** | | **35-45 hours** |

---

## Next Steps

1. **Create folder structure** for Platinum tier
2. **Setup Git repository** for vault sync
3. **Create cloud_watcher.py** for 24/7 email/social monitoring
4. **Implement claim-by-move coordination**
5. **Deploy to Oracle Cloud VM**
