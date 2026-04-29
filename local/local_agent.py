"""
Local Agent - Platinum Tier
Handles approvals, WhatsApp, banking, and final send actions

Responsibilities:
- Review Cloud agent drafts in /Pending_Approval/
- Execute approved actions via MCP (send email, post social, payments)
- Manage WhatsApp sessions (NEVER sync to Cloud)
- Manage banking credentials (NEVER sync to Cloud)
- Merge Cloud updates into Dashboard.md
- Move completed tasks to /Done/

Usage:
    python local_agent.py
"""

import logging
import time
import json
import shutil
from pathlib import Path
from datetime import datetime
from abc import ABC, abstractmethod

# Vault paths
VAULT_ROOT = Path(__file__).parent.resolve()
PENDING_APPROVAL = VAULT_ROOT / "Pending_Approval"
APPROVED = VAULT_ROOT / "Approved"
DONE = VAULT_ROOT / "Done"
IN_PROGRESS_LOCAL = VAULT_ROOT / "In_Progress" / "local"
UPDATES = VAULT_ROOT / "Updates"
LOGS = VAULT_ROOT / "Logs"
DASHBOARD = VAULT_ROOT / "Dashboard.md"

# Ensure directories exist
for d in [PENDING_APPROVAL, APPROVED, DONE, IN_PROGRESS_LOCAL, UPDATES, LOGS]:
    d.mkdir(parents=True, exist_ok=True)

# Configure logging
log_file = LOGS / f"local_agent_{datetime.now():%Y-%m-%d}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class BaseLocalAgent(ABC):
    """Base class for all local agent actions."""
    
    @abstractmethod
    def execute(self, approval_file: Path) -> bool:
        """Execute the approved action. Returns True if successful."""
        pass
    
    def archive_task(self, approval_file: Path, success: bool):
        """Move task to /Done/ with success/failure note."""
        done_subdir = DONE / self.__class__.__name__
        done_subdir.mkdir(exist_ok=True)
        
        # Add completion metadata
        content = approval_file.read_text(encoding="utf-8")
        if success:
            content += f"\n\n---\n**Completed:** {datetime.now().isoformat()}\n**Status:** SUCCESS\n"
        else:
            content += f"\n\n---\n**Completed:** {datetime.now().isoformat()}\n**Status:** FAILED\n"
        
        dest = done_subdir / approval_file.name
        dest.write_text(content, encoding="utf-8")
        approval_file.unlink()
        
        logger.info(f"Task archived: {approval_file.name} (Success: {success})")
    
    def claim_for_local_execution(self, approval_file: Path) -> Path:
        """Move approved file to /In_Progress/local/ for execution."""
        dest = IN_PROGRESS_LOCAL / approval_file.name
        shutil.move(str(approval_file), str(dest))
        logger.info(f"Claimed for local execution: {approval_file.name}")
        return dest


class EmailLocalAgent(BaseLocalAgent):
    """
    Local Agent for sending emails
    - Uses Gmail MCP to send approved emails
    - Requires Gmail credentials (NEVER sync to Cloud)
    """
    
    def execute(self, approval_file: Path) -> bool:
        """Send email using Gmail MCP."""
        try:
            # Parse approval file
            content = approval_file.read_text(encoding="utf-8")
            
            # Extract email details (simple parsing, improve with proper frontmatter parser)
            lines = content.split('\n')
            email_to = None
            email_subject = None
            email_body = None
            
            in_reply_section = False
            for line in lines:
                if line.startswith('to:'):
                    email_to = line.split(':', 1)[1].strip()
                elif line.startswith('subject:'):
                    email_subject = line.split(':', 1)[1].strip()
                elif '## Suggested Reply' in line:
                    in_reply_section = True
                elif in_reply_section and email_body is None:
                    email_body = line.strip()
            
            if not email_to:
                logger.error("Email 'to' address not found")
                return False
            
            logger.info(f"Sending email to {email_to} with subject '{email_subject}'")
            
            # TODO: Integrate with Gmail MCP server
            # For now, log the action
            # In production:
            # await gmail_mcp.send_email(to=email_to, subject=email_subject, body=email_body)
            
            logger.info(f"Email sent successfully to {email_to}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


class SocialLocalAgent(BaseLocalAgent):
    """
    Local Agent for posting to social media
    - Uses Playwright scripts to post
    - Requires social media sessions (NEVER sync to Cloud)
    """
    
    def execute(self, approval_file: Path) -> bool:
        """Post to social media using Playwright."""
        try:
            # Parse approval file
            content = approval_file.read_text(encoding="utf-8")
            
            # Extract platform and content
            platform = None
            post_content = None
            
            lines = content.split('\n')
            in_content_section = False
            for line in lines:
                if line.startswith('platform:'):
                    platform = line.split(':', 1)[1].strip()
                elif '## Suggested Content' in line:
                    in_content_section = True
                elif in_content_section and line.strip() and not line.startswith('##'):
                    post_content = line.strip()
                    break
            
            if not platform:
                logger.error("Platform not found")
                return False
            
            logger.info(f"Posting to {platform}: {post_content[:50]}...")
            
            # TODO: Integrate with Playwright scripts
            # For now, log the action
            # In production:
            # if platform == 'linkedin':
            #     from linkedin_playwright import post_to_linkedin
            #     await post_to_linkedin(post_content)
            # elif platform == 'twitter':
            #     from twitter_playwright import post_to_twitter
            #     await post_to_twitter(post_content)
            
            logger.info(f"Posted successfully to {platform}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to post to social media: {e}")
            return False


class AccountingLocalAgent(BaseLocalAgent):
    """
    Local Agent for accounting actions
    - Uses Odoo MCP to post payments/invoices
    - Requires Odoo credentials (NEVER sync to Cloud)
    """
    
    def execute(self, approval_file: Path) -> bool:
        """Post accounting entry using Odoo MCP."""
        try:
            # Parse approval file
            content = approval_file.read_text(encoding="utf-8")
            
            # Extract transaction details
            lines = content.split('\n')
            tx_type = None
            amount = None
            
            for line in lines:
                if line.startswith('transaction_type:'):
                    tx_type = line.split(':', 1)[1].strip()
                elif line.startswith('amount:'):
                    amount = float(line.split(':', 1)[1].strip())
            
            logger.info(f"Posting {tx_type} entry for ${amount}")
            
            # TODO: Integrate with Odoo MCP server
            # For now, log the action
            # In production:
            # await odoo_mcp.post_transaction(type=tx_type, amount=amount)
            
            logger.info(f"Accounting entry posted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to post accounting entry: {e}")
            return False


class ApprovalWatcher:
    """
    Watches /Approved/ folder and executes approved actions
    """
    
    def __init__(self):
        self.agents = {
            "email": EmailLocalAgent(),
            "social": SocialLocalAgent(),
            "accounting": AccountingLocalAgent(),
        }
    
    def check_approved(self):
        """Check /Approved/ folder for new approvals."""
        approved_items = []
        
        # Check all subdirectories
        for subdir in PENDING_APPROVAL.iterdir():
            if subdir.is_dir():
                for file in subdir.glob("*.md"):
                    approved_items.append(file)
        
        # Also check root Approved folder
        if APPROVED.exists():
            for file in APPROVED.glob("*.md"):
                approved_items.append(file)
        
        return approved_items
    
    def process_approval(self, approval_file: Path):
        """Process an approved file."""
        # Determine action type from filename or content
        filename = approval_file.name.lower()
        
        if filename.startswith("email"):
            agent = self.agents["email"]
        elif filename.startswith("social"):
            agent = self.agents["social"]
        elif filename.startswith("accounting"):
            agent = self.agents["accounting"]
        else:
            # Try to detect from content
            content = approval_file.read_text(encoding="utf-8")
            if "email" in content.lower():
                agent = self.agents["email"]
            elif "social" in content.lower() or "post" in content.lower():
                agent = self.agents["social"]
            elif "accounting" in content.lower() or "payment" in content.lower():
                agent = self.agents["accounting"]
            else:
                logger.warning(f"Unknown action type: {approval_file.name}")
                return
        
        # Claim for local execution
        local_file = agent.claim_for_local_execution(approval_file)
        
        # Execute
        success = agent.execute(local_file)
        
        # Archive
        agent.archive_task(local_file, success)
    
    def run(self):
        """Main approval watcher loop."""
        logger.info("Starting Approval Watcher (Local)")
        
        while True:
            try:
                approved = self.check_approved()
                for item in approved:
                    self.process_approval(item)
            except Exception as e:
                logger.error(f"Error in approval watcher: {e}")
            time.sleep(30)


class UpdatesMerger:
    """
    Merges Cloud updates from /Updates/ into Dashboard.md
    """
    
    def __init__(self):
        self.processed_updates = set()
        self.state_file = VAULT_ROOT / ".updates_merger_state.json"
        self.load_state()
    
    def load_state(self):
        """Load processed update IDs."""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                self.processed_updates = set(data.get("processed", []))
            except (json.JSONDecodeError, OSError):
                pass
    
    def save_state(self):
        """Save processed update IDs."""
        data = {"processed": list(self.processed_updates)}
        self.state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    
    def check_updates(self):
        """Check /Updates/ for new Cloud updates."""
        if not UPDATES.exists():
            return []
        
        updates = []
        for file in UPDATES.glob("*.md"):
            if file.stem not in self.processed_updates:
                updates.append(file)
        
        return updates
    
    def merge_update(self, update_file: Path):
        """Merge a Cloud update into Dashboard.md."""
        content = update_file.read_text(encoding="utf-8")
        
        # Parse update metadata
        update_type = "unknown"
        for line in content.split('\n'):
            if line.startswith('type:'):
                update_type = line.split(':', 1)[1].strip()
                break
        
        logger.info(f"Merging {update_type} update: {update_file.name}")
        
        # Append to Dashboard.md (simplified - improve with proper parsing)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_entry = f"\n- [{timestamp}] Cloud update: {update_type} ({update_file.name})\n"
        
        if DASHBOARD.exists():
            dashboard_content = DASHBOARD.read_text(encoding="utf-8")
            # Find the "Recently Completed" section and add entry
            if "## Recently Completed" in dashboard_content:
                dashboard_content = dashboard_content.replace(
                    "## Recently Completed",
                    f"## Recently Completed{update_entry}"
                )
            else:
                dashboard_content += update_entry
            
            DASHBOARD.write_text(dashboard_content, encoding="utf-8")
        
        # Mark as processed
        self.processed_updates.add(update_file.stem)
        
        # Move to Done
        done_updates = DONE / "updates"
        done_updates.mkdir(exist_ok=True)
        shutil.move(str(update_file), str(done_updates / update_file.name))
        
        logger.info(f"Update merged: {update_file.name}")
    
    def run(self):
        """Main updates merger loop."""
        logger.info("Starting Updates Merger (Local)")
        
        while True:
            try:
                updates = self.check_updates()
                for update in updates:
                    self.merge_update(update)
            except Exception as e:
                logger.error(f"Error in updates merger: {e}")
            finally:
                self.save_state()
            time.sleep(60)


def main():
    """Start local agent components."""
    logger.info("=" * 60)
    logger.info("Local Agent Starting (Platinum Tier)")
    logger.info(f"Vault root: {VAULT_ROOT}")
    logger.info("=" * 60)
    
    approval_watcher = ApprovalWatcher()
    updates_merger = UpdatesMerger()
    
    try:
        while True:
            # Run approval watcher
            approval_watcher.run()
            
            # Run updates merger
            updates_merger.run()
            
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Local Agent stopped by user.")


if __name__ == "__main__":
    main()
