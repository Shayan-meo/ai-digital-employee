"""
Agent Coordinator - Platinum Tier
Implements claim-by-move rule for multi-agent coordination

Rules:
1. First agent to move task from /Needs_Action to /In_Progress/<agent>/ owns it
2. Other agents MUST ignore claimed tasks
3. Cloud claims → /In_Progress/cloud/
4. Local claims → /In_Progress/local/
5. After completion, move to /Done/

Usage:
    python agent_coordinator.py
"""

import logging
import time
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

# Vault paths
VAULT_ROOT = Path(__file__).parent.resolve()
NEEDS_ACTION = VAULT_ROOT / "Needs_Action"
IN_PROGRESS_CLOUD = VAULT_ROOT / "In_Progress" / "cloud"
IN_PROGRESS_LOCAL = VAULT_ROOT / "In_Progress" / "local"
DONE = VAULT_ROOT / "Done"
LOGS = VAULT_ROOT / "Logs"
STATE_FILE = VAULT_ROOT / ".agent_coordinator_state.json"

# Ensure directories exist
for d in [IN_PROGRESS_CLOUD, IN_PROGRESS_LOCAL, DONE, LOGS]:
    d.mkdir(parents=True, exist_ok=True)

# Configure logging
log_file = LOGS / f"agent_coordinator_{datetime.now():%Y-%m-%d}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class TaskClaim:
    """Represents a task claim by an agent."""
    
    def __init__(self, task_file: str, claimed_by: str, claimed_at: str):
        self.task_file = task_file
        self.claimed_by = claimed_by  # "cloud" or "local"
        self.claimed_at = claimed_at
    
    def to_dict(self) -> dict:
        return {
            "task_file": self.task_file,
            "claimed_by": self.claimed_by,
            "claimed_at": self.claimed_at,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TaskClaim":
        return cls(
            task_file=data["task_file"],
            claimed_by=data["claimed_by"],
            claimed_at=data["claimed_at"],
        )


class AgentCoordinator:
    """
    Manages task claims between Cloud and Local agents.
    Implements claim-by-move rule.
    """
    
    def __init__(self, agent_id: str):
        """
        Initialize coordinator.
        
        Args:
            agent_id: "cloud" or "local"
        """
        self.agent_id = agent_id
        self.claims = {}  # task_file -> TaskClaim
        self.load_state()
    
    def load_state(self):
        """Load claims from state file."""
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                self.claims = {
                    k: TaskClaim.from_dict(v) for k, v in data.get("claims", {}).items()
                }
                logger.info(f"Loaded {len(self.claims)} claims from state")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load state: {e}")
                self.claims = {}
    
    def save_state(self):
        """Save claims to state file."""
        data = {
            "claims": {k: v.to_dict() for k, v in self.claims.items()},
            "last_updated": datetime.now().isoformat(),
        }
        STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    
    def get_available_tasks(self) -> list[Path]:
        """
        Get list of unclaimed tasks in /Needs_Action/.
        
        Returns:
            List of Path objects for unclaimed task files
        """
        if not NEEDS_ACTION.exists():
            return []
        
        available = []
        for file in NEEDS_ACTION.rglob("*.md"):
            # Skip subdirectory files (they're already claimed)
            if file.parent != NEEDS_ACTION:
                continue
            
            # Check if already claimed
            if file.name in self.claims:
                claim = self.claims[file.name]
                # If claimed by another agent, skip
                if claim.claimed_by != self.agent_id:
                    continue
            
            available.append(file)
        
        return available
    
    def claim_task(self, task_file: Path) -> Optional[TaskClaim]:
        """
        Claim a task by moving it to /In_Progress/<agent_id>/.
        
        Args:
            task_file: Path to task file in /Needs_Action/
        
        Returns:
            TaskClaim if successful, None if failed
        """
        if not task_file.exists():
            logger.warning(f"Task file not found: {task_file}")
            return None
        
        # Check if already claimed by another agent
        if task_file.name in self.claims:
            existing_claim = self.claims[task_file.name]
            if existing_claim.claimed_by != self.agent_id:
                logger.warning(f"Task already claimed by {existing_claim.claimed_by}")
                return None
        
        # Determine destination
        if self.agent_id == "cloud":
            dest_dir = IN_PROGRESS_CLOUD
        elif self.agent_id == "local":
            dest_dir = IN_PROGRESS_LOCAL
        else:
            logger.error(f"Invalid agent_id: {self.agent_id}")
            return None
        
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / task_file.name
        
        try:
            # Move task to In_Progress
            shutil.move(str(task_file), str(dest))
            
            # Create claim
            claim = TaskClaim(
                task_file=task_file.name,
                claimed_by=self.agent_id,
                claimed_at=datetime.now().isoformat(),
            )
            self.claims[task_file.name] = claim
            self.save_state()
            
            logger.info(f"Claimed task: {task_file.name} → {dest_dir.name}/")
            return claim
            
        except Exception as e:
            logger.error(f"Failed to claim task {task_file.name}: {e}")
            return None
    
    def release_claim(self, task_file: str, success: bool = True):
        """
        Release a claim by moving task to /Done/.
        
        Args:
            task_file: Name of claimed task file
            success: Whether task completed successfully
        """
        if task_file not in self.claims:
            logger.warning(f"No claim found for: {task_file}")
            return
        
        claim = self.claims[task_file]
        
        # Find task in In_Progress
        if self.agent_id == "cloud":
            source_dir = IN_PROGRESS_CLOUD
        else:
            source_dir = IN_PROGRESS_LOCAL
        
        source = source_dir / task_file
        if not source.exists():
            logger.warning(f"Task file not found in In_Progress: {source}")
            return
        
        # Move to Done
        done_subdir = DONE / self.agent_id / datetime.now().strftime("%Y-%m-%d")
        done_subdir.mkdir(parents=True, exist_ok=True)
        dest = done_subdir / task_file
        
        try:
            # Add completion metadata
            content = source.read_text(encoding="utf-8")
            completion_note = f"""
---
**Completed:** {datetime.now().isoformat()}
**Agent:** {self.agent_id}
**Status:** {"SUCCESS" if success else "FAILED"}
"""
            content += completion_note
            dest.write_text(content, encoding="utf-8")
            source.unlink()
            
            # Remove claim
            del self.claims[task_file]
            self.save_state()
            
            logger.info(f"Released claim: {task_file} → Done/ ({'SUCCESS' if success else 'FAILED'})")
            
        except Exception as e:
            logger.error(f"Failed to release claim {task_file}: {e}")
    
    def get_my_claims(self) -> list[str]:
        """Get list of tasks claimed by this agent."""
        return [
            task_file for task_file, claim in self.claims.items()
            if claim.claimed_by == self.agent_id
        ]
    
    def get_status(self) -> dict:
        """Get coordinator status."""
        my_claims = self.get_my_claims()
        other_claims = [
            task_file for task_file, claim in self.claims.items()
            if claim.claimed_by != self.agent_id
        ]
        
        return {
            "agent_id": self.agent_id,
            "my_claims": my_claims,
            "my_claims_count": len(my_claims),
            "other_claims": other_claims,
            "other_claims_count": len(other_claims),
            "total_claims": len(self.claims),
        }


class CloudAgentCoordinator(AgentCoordinator):
    """Coordinator specialized for Cloud agent."""
    
    def __init__(self):
        super().__init__("cloud")
    
    def process_tasks(self):
        """Process all available tasks."""
        available = self.get_available_tasks()
        
        if not available:
            logger.debug("No available tasks")
            return
        
        logger.info(f"Found {len(available)} available task(s)")
        
        for task_file in available:
            claim = self.claim_task(task_file)
            if claim:
                # Process the task
                # In production, this would trigger Cloud agent logic
                logger.info(f"Processing: {task_file.name}")
                
                # Simulate processing (replace with actual logic)
                # After processing, release claim
                # self.release_claim(task_file.name, success=True)
    
    def run(self):
        """Main coordinator loop for Cloud agent."""
        logger.info("=" * 60)
        logger.info("Cloud Agent Coordinator Starting")
        logger.info(f"Monitoring: {NEEDS_ACTION}")
        logger.info(f"Claim directory: {IN_PROGRESS_CLOUD}")
        logger.info("=" * 60)
        
        while True:
            try:
                self.process_tasks()
            except Exception as e:
                logger.error(f"Error in coordinator: {e}")
            
            self.save_state()
            time.sleep(30)


class LocalAgentCoordinator(AgentCoordinator):
    """Coordinator specialized for Local agent."""
    
    def __init__(self):
        super().__init__("local")
    
    def process_tasks(self):
        """Process all available tasks."""
        available = self.get_available_tasks()
        
        if not available:
            logger.debug("No available tasks")
            return
        
        logger.info(f"Found {len(available)} available task(s)")
        
        for task_file in available:
            claim = self.claim_task(task_file)
            if claim:
                # Process the task
                # In production, this would trigger Local agent logic
                logger.info(f"Processing: {task_file.name}")
                
                # Simulate processing (replace with actual logic)
                # After processing, release claim
                # self.release_claim(task_file.name, success=True)
    
    def run(self):
        """Main coordinator loop for Local agent."""
        logger.info("=" * 60)
        logger.info("Local Agent Coordinator Starting")
        logger.info(f"Monitoring: {NEEDS_ACTION}")
        logger.info(f"Claim directory: {IN_PROGRESS_LOCAL}")
        logger.info("=" * 60)
        
        while True:
            try:
                self.process_tasks()
            except Exception as e:
                logger.error(f"Error in coordinator: {e}")
            
            self.save_state()
            time.sleep(30)


def main():
    """CLI for agent coordinator."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python agent_coordinator.py [cloud|local|status]")
        return
    
    command = sys.argv[1].lower()
    
    if command == "cloud":
        coordinator = CloudAgentCoordinator()
        coordinator.run()
    
    elif command == "local":
        coordinator = LocalAgentCoordinator()
        coordinator.run()
    
    elif command == "status":
        cloud = CloudAgentCoordinator()
        local = LocalAgentCoordinator()
        
        print("\n=== Agent Coordinator Status ===\n")
        
        cloud_status = cloud.get_status()
        print(f"Cloud Agent:")
        print(f"  Claims: {cloud_status['my_claims_count']}")
        if cloud_status['my_claims']:
            for task in cloud_status['my_claims'][:5]:
                print(f"    - {task}")
        
        print()
        
        local_status = local.get_status()
        print(f"Local Agent:")
        print(f"  Claims: {local_status['my_claims_count']}")
        if local_status['my_claims']:
            for task in local_status['my_claims'][:5]:
                print(f"    - {task}")
        
        print()
        print(f"Total Active Claims: {cloud_status['total_claims'] + local_status['total_claims']}")
    
    else:
        print(f"Unknown command: {command}")
        print("Usage: python agent_coordinator.py [cloud|local|status]")


if __name__ == "__main__":
    main()
