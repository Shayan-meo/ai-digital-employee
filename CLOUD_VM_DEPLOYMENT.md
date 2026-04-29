# Cloud VM Deployment Guide - Platinum Tier

## Overview
This guide walks you through deploying the AI Employee to a Cloud VM for 24/7 operation.

---

## Step 1: Create Cloud VM (Oracle Cloud Free Tier)

### Sign Up for Oracle Cloud Free Tier
1. Visit: https://www.oracle.com/cloud/free/
2. Create account with credit card (required for verification, no charges for free tier)
3. Verify email and phone

### Create VM Instance
1. Login to Oracle Cloud Console
2. Navigate to **Compute** → **Instances**
3. Click **Create Instance**
4. Configure:
   - **Name**: `ai-employee-cloud`
   - **Compartment**: Select your compartment
   - **Availability Domain**: Any available
   - **Shape**: `VM.Standard.A1.Flex` (ARM, 4 OCPU, 24GB RAM - FREE)
   - **Image**: `Ubuntu 22.04 LTS`
   - **Networking**: Create new VCN, allow SSH (port 22), HTTP (80), HTTPS (443)
   - **SSH Keys**: Generate key pair or upload your public key
   - **Boot Volume**: 200GB (FREE)

5. Click **Create**
6. Note the **Public IP Address** (e.g., `129.146.123.45`)

---

## Step 2: Connect to Cloud VM

### SSH into VM
```bash
# Linux/Mac
ssh -i /path/to/private_key ubuntu@<VM_PUBLIC_IP>

# Windows (PowerShell)
ssh -i C:\path\to\private_key ubuntu@<VM_PUBLIC_IP>
```

### Update System
```bash
sudo apt update && sudo apt upgrade -y
```

---

## Step 3: Install Dependencies

### Install Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
```

### Install Python 3.13
```bash
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.13 python3.13-venv python3-pip
python3.13 --version
```

### Install Node.js 24 LTS
```bash
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt install -y nodejs
node --version
npm --version
```

### Install PM2 (Process Manager)
```bash
sudo npm install -g pm2
pm2 --version
```

### Install Git
```bash
sudo apt install -y git
git --version
```

---

## Step 4: Clone Vault Repository

### Setup Git
```bash
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
```

### Clone Repository
```bash
cd ~
git clone <YOUR_GIT_REPO_URL> ai_employee_vault
cd ai_employee_vault
```

### Setup Python Virtual Environment
```bash
python3.13 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 5: Configure Cloud Environment

### Create Cloud .env File
```bash
cp cloud/.env.example cloud/.env
nano cloud/.env
```

Fill in your API credentials (Gmail, Social Media, Odoo).

### Configure Cloud-Only Settings
Edit `cloud/.env`:
```
CLOUD_AGENT_ID=cloud_001
VAULT_SYNC_ENABLED=true
SYNC_INTERVAL=60

# Gmail API (Draft Only)
GMAIL_CLIENT_ID=your_client_id
GMAIL_CLIENT_SECRET=your_client_secret

# Odoo (Draft Only)
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_USER=admin
ODOO_PASSWORD=your_password
```

---

## Step 6: Deploy Odoo Community (Docker)

### Run Odoo Container
```bash
docker run -d \
  --name odoo \
  -p 8069:8069 \
  -e ODOO_ADMIN_PASSWORD=your_secure_password \
  -v odoo-data:/var/lib/odoo \
  --restart unless-stopped \
  odoo:19.0
```

### Setup HTTPS with Nginx + Let's Encrypt
```bash
# Install Nginx
sudo apt install -y nginx

# Configure Nginx
sudo nano /etc/nginx/sites-available/odoo
```

Add this configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8069;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/odoo /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Install Certbot for HTTPS
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## Step 7: Start Cloud Watchers

### Start with PM2
```bash
cd ~/ai_employee_vault

# Start cloud watcher
pm2 start cloud/cloud_watcher.py --interpreter python3.13 --name cloud-watcher

# Start vault sync (periodic)
pm2 start vault_sync.py --interpreter python3.13 --name vault-sync -- --auto

# Save PM2 configuration
pm2 save

# Setup PM2 startup on boot
pm2 startup
# Run the command it outputs (e.g., sudo env PATH=$PATH:... pm2 startup)
```

### Monitor PM2
```bash
# View status
pm2 status

# View logs
pm2 logs cloud-watcher

# Restart if needed
pm2 restart cloud-watcher

# Stop
pm2 stop cloud-watcher
```

---

## Step 8: Configure Git Sync

### Setup Git Remote
```bash
cd ~/ai_employee_vault

# Initialize Git if needed
git init

# Add remote (your Git repo)
git remote add origin <YOUR_GIT_REPO_URL>

# Initial push
git add -A
git commit -m "Initial cloud deployment"
git push -u origin main
```

### Configure .gitignore
Ensure `.gitignore` excludes:
- `.env`
- `*.session`
- `gmail_credentials/`
- `local/`

---

## Step 9: Setup Health Monitoring

### Create Health Check Script
```bash
nano ~/health_check.sh
```

```bash
#!/bin/bash
# Health check script

# Check PM2 processes
pm2 status | grep -q "online"
if [ $? -ne 0 ]; then
    echo "PM2 process offline!" | mail -s "AI Employee Alert" your@email.com
    pm2 restart all
fi

# Check Odoo
curl -f http://localhost:8069 || echo "Odoo down!" | mail -s "AI Employee Alert" your@email.com

# Check disk space
df -h | awk '$5 > 80 {print "Disk usage high: " $5}'
```

```bash
chmod +x ~/health_check.sh
```

### Add Cron Job
```bash
crontab -e
```

Add:
```
*/5 * * * * /home/ubuntu/health_check.sh
0 * * * * cd /home/ubuntu/ai_employee_vault && git pull origin main
```

---

## Step 10: Test Cloud Deployment

### Verify Watchers Running
```bash
pm2 status
# Should show: cloud-watcher (online), vault-sync (online)
```

### Check Logs
```bash
pm2 logs
# Should show watcher activity
```

### Test Git Sync
```bash
# On Local machine
echo "# Test sync" >> Dashboard.md
git add .
git commit -m "Test sync"
git push

# On Cloud VM
git pull
# Should see Dashboard.md update
```

---

## Step 11: Local Machine Configuration

### Setup Local Agent
```bash
cd D:\AI_Employee_Vault

# Copy local .env
copy local\.env.example local\.env

# Edit local\.env with your credentials
notepad local\.env
```

### Start Local Agent
```bash
python local\local_agent.py
```

### Configure Git Sync
```bash
python vault_sync.py init
python vault_sync.py remote <YOUR_GIT_REPO_URL>
python vault_sync.py push
```

---

## Step 12: Platinum Demo Test

### Test Flow
1. **Stop Local Agent** (simulate offline)
2. **Send email** to your Gmail
3. **Cloud detects** email, creates draft in `/Pending_Approval/email/`
4. **Cloud pushes** to Git
5. **Start Local Agent**, pull from Git
6. **Review draft** in `/Pending_Approval/email/`
7. **Move to `/Approved/`**
8. **Local sends** email via Gmail MCP
9. **Task moves** to `/Done/`
10. **Local pushes** to Git
11. **Cloud pulls** and sees completion

---

## Troubleshooting

### Cloud Watcher Not Running
```bash
pm2 restart cloud-watcher
pm2 logs cloud-watcher
```

### Git Sync Failing
```bash
cd ~/ai_employee_vault
git status
git pull --rebase
```

### Odoo Not Accessible
```bash
docker ps | grep odoo
docker logs odoo
docker restart odoo
```

### PM2 Not Starting on Boot
```bash
pm2 startup
# Run the output command
pm2 save
```

---

## Cost Estimate

### Oracle Cloud Free Tier
- **VM**: VM.Standard.A1.Flex (4 OCPU, 24GB RAM) - **FREE**
- **Storage**: 200GB block volume - **FREE**
- **Network**: 10TB outbound/month - **FREE**

### Total Monthly Cost: **$0** (within free tier limits)

---

## Next Steps

1. **Monitor** cloud VM for 24 hours
2. **Test** all integrations (Gmail, Social, Odoo)
3. **Document** lessons learned
4. **Record** demo video
5. **Submit** to hackathon

---

## Security Checklist

- [ ] `.env` files excluded from Git
- [ ] SSH keys secured (chmod 600)
- [ ] Firewall configured (only 22, 80, 443 open)
- [ ] HTTPS enabled with Let's Encrypt
- [ ] Odoo admin password changed
- [ ] Regular backups configured
- [ ] Monitoring alerts setup
- [ ] Credentials rotated monthly
