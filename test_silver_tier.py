"""
Silver Tier Test Script
Tests all Silver Tier components one by one.
"""

import sys
import time
from pathlib import Path
from datetime import datetime

VAULT_ROOT = Path(__file__).parent.resolve()

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")


def print_result(test_name, passed, message=""):
    status = f"{GREEN}✅ PASS{RESET}" if passed else f"{RED}❌ FAIL{RESET}"
    print(f"{status} - {test_name}")
    if message:
        print(f"   {message}")


# ── Test 1: Folder Structure ──────────────────────────────────────────────────
def test_folder_structure():
    """Test 1: Verify all required folders exist."""
    required_folders = [
        "Inbox",
        "Needs_Action",
        "Plans",
        "Pending_Approval",
        "Approved",
        "Done",
        "Logs",
        "Briefings",
    ]
    
    all_exist = True
    for folder in required_folders:
        folder_path = VAULT_ROOT / folder
        if not folder_path.exists():
            print_result(f"Folder: {folder}", False, "Missing!")
            all_exist = False
        else:
            print_result(f"Folder: {folder}", True)
    
    return all_exist


# ── Test 2: Required Files ────────────────────────────────────────────────────
def test_required_files():
    """Test 2: Verify critical files exist."""
    required_files = [
        "Dashboard.md",
        "Company_Handbook.md",
        "Business_Goals.md",
        "CLAUDE.md",
        "filesystem_watcher.py",
        "gmail_watcher.py",
        "approval_watcher.py",
        "linkedin_watcher.py",
        "linkedin_playwright.py",
        "scheduler.py",
        "dashboard_updater.py",
    ]
    
    all_exist = True
    for file in required_files:
        file_path = VAULT_ROOT / file
        if not file_path.exists():
            print_result(f"File: {file}", False, "Missing!")
            all_exist = False
        else:
            print_result(f"File: {file}", True)
    
    return all_exist


# ── Test 3: Watcher Scripts Syntax Check ──────────────────────────────────────
def test_watcher_syntax():
    """Test 3: Check watcher scripts for syntax errors."""
    watchers = [
        "filesystem_watcher.py",
        "gmail_watcher.py",
        "approval_watcher.py",
        "linkedin_watcher.py",
        "linkedin_playwright.py",
        "scheduler.py",
        "dashboard_updater.py",
    ]
    
    all_valid = True
    for watcher in watchers:
        watcher_path = VAULT_ROOT / watcher
        try:
            with open(watcher_path, "r", encoding="utf-8") as f:
                compile(f.read(), watcher_path, "exec")
            print_result(f"Syntax: {watcher}", True)
        except SyntaxError as e:
            print_result(f"Syntax: {watcher}", False, str(e))
            all_valid = False
    
    return all_valid


# ── Test 4: MCP Configuration ─────────────────────────────────────────────────
def test_mcp_config():
    """Test 4: Verify MCP servers are configured."""
    mcp_file = VAULT_ROOT / ".mcp.json"
    
    if not mcp_file.exists():
        print_result("MCP Config", False, ".mcp.json not found!")
        return False
    
    import json
    try:
        config = json.loads(mcp_file.read_text(encoding="utf-8"))
        servers = config.get("mcpServers", {})
        
        required_servers = ["gmail", "linkedin", "odoo"]
        all_configured = True
        
        for server in required_servers:
            if server in servers:
                print_result(f"MCP Server: {server}", True)
            else:
                print_result(f"MCP Server: {server}", False, "Not configured!")
                all_configured = False
        
        return all_configured
    except Exception as e:
        print_result("MCP Config Parse", False, str(e))
        return False


# ── Test 5: Environment Variables ─────────────────────────────────────────────
def test_env_vars():
    """Test 5: Check required environment variables."""
    env_file = VAULT_ROOT / ".env"
    
    if not env_file.exists():
        print_result("Environment File", False, ".env not found!")
        return False
    
    content = env_file.read_text(encoding="utf-8")
    
    required_vars = [
        "LINKEDIN_EMAIL",
        "LINKEDIN_PASSWORD",
    ]
    
    all_present = True
    for var in required_vars:
        if var + "=" in content:
            print_result(f"Env Var: {var}", True)
        else:
            print_result(f"Env Var: {var}", False, "Missing!")
            all_present = False
    
    return all_present


# ── Test 6: Filesystem Watcher Live Test ──────────────────────────────────────
def test_filesystem_watcher_live():
    """Test 6: Test filesystem watcher with a sample file."""
    inbox = VAULT_ROOT / "Inbox"
    needs_action = VAULT_ROOT / "Needs_Action"
    
    # Create test file
    test_file = inbox / f"test_silver_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    test_file.write_text("# Test File\nThis is a Silver Tier test.\n")
    print(f"{YELLOW}Created test file: {test_file.name}{RESET}")
    
    # Run filesystem_watcher for 3 seconds
    import subprocess
    try:
        result = subprocess.run(
            ["python", "filesystem_watcher.py"],
            cwd=VAULT_ROOT,
            timeout=3,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        pass  # Expected - watcher runs forever
    
    time.sleep(1)
    
    # Check if file moved
    moved = False
    for f in needs_action.iterdir():
        if "test_silver_" in f.name:
            moved = True
            # Move back to Inbox for cleanup
            (inbox / f.name).write_text(f.read_text(encoding="utf-8"))
            f.unlink()
            break
    
    print_result("Filesystem Watcher Live Test", moved, "File moved to Needs_Action" if moved else "File not moved")
    return moved


# ── Test 7: Logs Directory ────────────────────────────────────────────────────
def test_logs():
    """Test 7: Check if logs are being created."""
    log_dir = VAULT_ROOT / "Logs"
    
    if not log_dir.exists():
        print_result("Logs Directory", False, "Does not exist!")
        return False
    
    log_files = list(log_dir.glob("*.log"))
    if len(log_files) > 0:
        print_result("Logs Directory", True, f"{len(log_files)} log files found")
        return True
    else:
        print_result("Logs Directory", False, "No log files found")
        return False


# ── Main Test Runner ──────────────────────────────────────────────────────────
def main():
    print_header("🥈 SILVER TIER TEST SUITE")
    
    results = []
    
    print_header("Test 1: Folder Structure")
    results.append(("Folder Structure", test_folder_structure()))
    
    print_header("Test 2: Required Files")
    results.append(("Required Files", test_required_files()))
    
    print_header("Test 3: Watcher Scripts Syntax")
    results.append(("Watcher Syntax", test_watcher_syntax()))
    
    print_header("Test 4: MCP Configuration")
    results.append(("MCP Config", test_mcp_config()))
    
    print_header("Test 5: Environment Variables")
    results.append(("Env Variables", test_env_vars()))
    
    print_header("Test 6: Logs")
    results.append(("Logs", test_logs()))
    
    print_header("Test 7: Filesystem Watcher Live Test")
    results.append(("Filesystem Watcher Live", test_filesystem_watcher_live()))
    
    # Summary
    print_header("📊 TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{GREEN}✅{RESET}" if result else f"{RED}❌{RESET}"
        print(f"{status} {test_name}")
    
    print(f"\n{BLUE}Total: {passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}🎉 SILVER TIER: ALL TESTS PASSED!{RESET}")
        return 0
    else:
        print(f"\n{RED}⚠️  Some tests failed. Review above for details.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
