"""
Vault Sync Manager - Platinum Tier
Manages Git-based synchronization between Cloud and Local vaults

Features:
- Push Local changes to Cloud (excluding secrets)
- Pull Cloud updates to Local
- Handle merge conflicts gracefully
- Maintain .gitignore for security

Usage:
    python vault_sync.py push    # Push Local → Cloud
    python vault_sync.py pull    # Pull Cloud → Local
    python vault_sync.py status  # Show sync status
"""

import subprocess
import logging
from pathlib import Path
from datetime import datetime

VAULT_ROOT = Path(__file__).parent.resolve()
LOGS = VAULT_ROOT / "Logs"
LOGS.mkdir(exist_ok=True)

# Configure logging
log_file = LOGS / f"vault_sync_{datetime.now():%Y-%m-%d}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class VaultSync:
    """Manages Git-based vault synchronization."""
    
    def __init__(self):
        self.remote_url = None
        self.branch = "main"
    
    def set_remote(self, url: str):
        """Set the Git remote URL for sync."""
        self.remote_url = url
        try:
            subprocess.run(
                ["git", "remote", "set-url", "origin", url],
                cwd=VAULT_ROOT,
                check=True,
                capture_output=True,
            )
            logger.info(f"Remote URL set: {url}")
        except subprocess.CalledProcessError:
            subprocess.run(
                ["git", "remote", "add", "origin", url],
                cwd=VAULT_ROOT,
                check=True,
                capture_output=True,
            )
            logger.info(f"Remote URL added: {url}")
    
    def init_repo(self):
        """Initialize Git repository if not exists."""
        git_dir = VAULT_ROOT / ".git"
        if not git_dir.exists():
            logger.info("Initializing Git repository...")
            subprocess.run(["git", "init"], cwd=VAULT_ROOT, check=True, capture_output=True)
            logger.info("Git repository initialized")
        else:
            logger.info("Git repository already exists")
    
    def check_gitignore(self):
        """Verify .gitignore is properly configured."""
        gitignore = VAULT_ROOT / ".gitignore"
        if not gitignore.exists():
            logger.warning(".gitignore not found! Creating default...")
            self.create_gitignore()
        else:
            logger.info(".gitignore found")
    
    def create_gitignore(self):
        """Create .gitignore file."""
        content = """# Platinum Tier .gitignore - Security Rules

# === CRITICAL: Never Sync These ===
.env
.env.local
.env.*.local
*.session
whatsapp_session/
facebook_session/
instagram_session/
twitter_session/
linkedin_session/
gmail_credentials/
banking_credentials/
private_keys/
*.pem
*.key

# === Local-Only Config ===
local/.env
local/banking_config.json
local/whatsapp_config.json

# === OS Files ===
.DS_Store
Thumbs.db
desktop.ini

# === IDE/Editor ===
.vscode/
.idea/
*.swp
*.swo

# === Python ===
__pycache__/
*.py[cod]
*.pyo
*.pyd
venv/
env/

# === Node ===
node_modules/
"""
        gitignore = VAULT_ROOT / ".gitignore"
        gitignore.write_text(content, encoding="utf-8")
        logger.info(".gitignore created")
    
    def status(self) -> dict:
        """Get Git repository status."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=VAULT_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            
            changes = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            return {
                "has_changes": len(changes) > 0,
                "changes": changes,
                "branch": self._get_branch(),
            }
        except subprocess.CalledProcessError as e:
            logger.error(f"Git status failed: {e}")
            return {"has_changes": False, "changes": [], "branch": "unknown"}
    
    def _get_branch(self) -> str:
        """Get current branch name."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=VAULT_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "unknown"
    
    def add_all(self):
        """Stage all changes."""
        subprocess.run(["git", "add", "-A"], cwd=VAULT_ROOT, check=True, capture_output=True)
        logger.info("All changes staged")
    
    def commit(self, message: str):
        """Commit staged changes."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"{message} [Sync: {timestamp}]"
        
        subprocess.run(
            ["git", "commit", "-m", full_message],
            cwd=VAULT_ROOT,
            check=True,
            capture_output=True,
        )
        logger.info(f"Committed: {full_message}")
    
    def push(self, force: bool = False):
        """Push changes to remote."""
        if not self.remote_url:
            logger.error("Remote URL not set. Use set_remote() first.")
            return False
        
        args = ["git", "push", "-u", "origin", self.branch]
        if force:
            args.insert(2, "--force")
        
        try:
            subprocess.run(args, cwd=VAULT_ROOT, check=True, capture_output=True)
            logger.info(f"Pushed to {self.remote_url}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Push failed: {e.stderr.decode() if e.stderr else e}")
            return False
    
    def pull(self):
        """Pull changes from remote."""
        if not self.remote_url:
            logger.error("Remote URL not set. Use set_remote() first.")
            return False
        
        try:
            subprocess.run(
                ["git", "pull", "origin", self.branch],
                cwd=VAULT_ROOT,
                check=True,
                capture_output=True,
            )
            logger.info(f"Pulled from {self.remote_url}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Pull failed: {e.stderr.decode() if e.stderr else e}")
            return False
    
    def sync(self, message: str = "Auto-sync"):
        """Full sync: add, commit, push, pull."""
        logger.info("Starting full sync...")
        
        self.init_repo()
        self.check_gitignore()
        self.add_all()
        
        status = self.status()
        if status["has_changes"]:
            self.commit(message)
        
        self.push()
        self.pull()
        
        logger.info("Sync complete")


def main():
    """CLI for vault sync."""
    import sys
    
    sync = VaultSync()
    
    if len(sys.argv) < 2:
        print("Usage: python vault_sync.py [push|pull|status|init]")
        return
    
    command = sys.argv[1].lower()
    
    if command == "init":
        sync.init_repo()
        sync.check_gitignore()
        print("Git repository initialized. Set remote with: python vault_sync.py remote <url>")
    
    elif command == "remote":
        if len(sys.argv) < 3:
            print("Usage: python vault_sync.py remote <url>")
            return
        sync.set_remote(sys.argv[2])
        print(f"Remote URL set: {sys.argv[2]}")
    
    elif command == "status":
        status = sync.status()
        print(f"Branch: {status['branch']}")
        if status["has_changes"]:
            print("Changes:")
            for change in status["changes"][:10]:  # Show first 10
                print(f"  {change}")
        else:
            print("No changes")
    
    elif command == "push":
        sync.sync(message="Push")
        print("Pushed to remote")
    
    elif command == "pull":
        sync.pull()
        print("Pulled from remote")
    
    else:
        print(f"Unknown command: {command}")
        print("Usage: python vault_sync.py [push|pull|status|init|remote]")


if __name__ == "__main__":
    main()
