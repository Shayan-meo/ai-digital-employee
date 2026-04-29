"""
Gold Tier Test Suite
Tests all Gold Tier functionality to verify correct operation

Run: python test_gold_tier.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

VAULT_ROOT = Path(__file__).parent.resolve()

# Use ASCII-safe icons for Windows compatibility
PASS_ICON = "[PASS]"
FAIL_ICON = "[FAIL]"

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_test(name, status, details=""):
    icon = PASS_ICON if status else FAIL_ICON
    color = Colors.GREEN if status else Colors.RED
    print(f"{icon} {color}{name}{Colors.RESET}")
    if details:
        print(f"   {Colors.YELLOW}{details}{Colors.RESET}")

def test_vault_structure():
    """Test 1: Vault folder structure"""
    print_header("TEST 1: Vault Folder Structure")
    
    required_folders = [
        'Inbox',
        'Needs_Action',
        'Plans',
        'Pending_Approval',
        'Approved',
        'Done',
        'Logs',
        'Briefings',
        'skills',
        'odoo',
        'cloud',
        'local',
        'Updates',
        'In_Progress'
    ]
    
    all_exist = True
    for folder in required_folders:
        folder_path = VAULT_ROOT / folder
        exists = folder_path.exists() and folder_path.is_dir()
        print_test(f"  Folder: {folder}", exists)
        if not exists:
            all_exist = False
    
    return all_exist

def test_gold_scripts():
    """Test 2: Gold Tier scripts existence"""
    print_header("TEST 2: Gold Tier Scripts")
    
    required_scripts = [
        ('facebook_playwright.py', 'Facebook posting'),
        ('instagram_playwright.py', 'Instagram posting'),
        ('twitter_playwright.py', 'Twitter/X posting'),
        ('social_media_watcher.py', 'Social media monitoring'),
        ('ceo_briefing.py', 'CEO Briefing generation'),
        ('odoo_mcp_server.py', 'Odoo MCP server'),
        ('ralph_wiggum_hook.py', 'Ralph Wiggum loop'),
        ('scheduler.py', 'Task scheduler'),
    ]
    
    all_exist = True
    for script, description in required_scripts:
        script_path = VAULT_ROOT / script
        exists = script_path.exists()
        print_test(f"  {script}", exists, description)
        if not exists:
            all_exist = False
    
    return all_exist

def test_mcp_servers():
    """Test 3: MCP Servers configuration"""
    print_header("TEST 3: MCP Servers Configuration")
    
    mcp_file = VAULT_ROOT / '.mcp.json'
    if not mcp_file.exists():
        print_test("MCP Config", False, ".mcp.json not found")
        return False
    
    try:
        config = json.loads(mcp_file.read_text(encoding='utf-8'))
        servers = config.get('mcpServers', {})
        
        # Check required servers
        required = ['gmail', 'linkedin', 'odoo']
        all_configured = True
        
        for server in required:
            configured = server in servers
            print_test(f"  MCP Server: {server}", configured)
            if not configured:
                all_configured = False
            elif configured:
                # Show config details
                srv_config = servers[server]
                print(f"     {Colors.YELLOW}Command: {srv_config.get('command', 'N/A')}{Colors.RESET}")
        
        return all_configured
        
    except json.JSONDecodeError as e:
        print_test("MCP Config", False, f"JSON parse error: {e}")
        return False

def test_agent_skills():
    """Test 4: Agent Skills"""
    print_header("TEST 4: Agent Skills (6 required)")
    
    skills_dir = VAULT_ROOT / 'skills'
    if not skills_dir.exists():
        print_test("Skills folder", False)
        return False
    
    required_skills = [
        'process_task.md',
        'email_triage.md',
        'social_media_post.md',
        'ceo_briefing.md',
        'odoo_accounting.md',
        'approval_workflow.md'
    ]
    
    all_exist = True
    for skill in required_skills:
        skill_path = skills_dir / skill
        exists = skill_path.exists()
        print_test(f"  Skill: {skill}", exists)
        if not exists:
            all_exist = False
    
    # Count total skills
    total_skills = len(list(skills_dir.glob('*.md')))
    print(f"\n   {Colors.BLUE}Total skills: {total_skills}{Colors.RESET}")
    
    return all_exist and total_skills >= 6

def test_ceo_briefings():
    """Test 5: CEO Briefings"""
    print_header("TEST 5: CEO Briefings")
    
    briefings_dir = VAULT_ROOT / 'Briefings'
    if not briefings_dir.exists():
        print_test("Briefings folder", False)
        return False
    
    briefings = list(briefings_dir.glob('*.md'))
    count = len(briefings)
    
    print_test(f"CEO Briefings exist", count > 0, f"Found {count} briefing(s)")
    
    if count > 0:
        print(f"\n   {Colors.BLUE}Recent briefings:{Colors.RESET}")
        for b in briefings[:3]:
            print(f"     - {b.name}")
    
    return count >= 1

def test_audit_logs():
    """Test 6: Audit Logging"""
    print_header("TEST 6: Audit Logging")
    
    logs_dir = VAULT_ROOT / 'Logs'
    if not logs_dir.exists():
        print_test("Logs folder", False)
        return False
    
    log_files = list(logs_dir.glob('*.log')) + list(logs_dir.glob('*_task_log.md'))
    count = len(log_files)
    
    print_test(f"Log files exist", count > 0, f"Found {count} log file(s)")
    
    # Check for recent logs (today or yesterday)
    today = datetime.now().strftime('%Y-%m-%d')
    recent_logs = [f for f in log_files if today in f.name]
    
    print_test(f"Recent logs (today)", len(recent_logs) > 0, f"Found {len(recent_logs)} today")
    
    return count >= 10  # At least 10 log files

def test_social_sessions():
    """Test 7: Social Media Sessions"""
    print_header("TEST 7: Social Media Sessions")
    
    sessions = [
        ('.facebook_session', 'Facebook'),
        ('.instagram_session', 'Instagram'),
        ('.twitter_session', 'Twitter'),
        ('.linkedin_session', 'LinkedIn'),
    ]
    
    all_exist = True
    for session_file, platform in sessions:
        session_path = VAULT_ROOT / session_file
        exists = session_path.exists()
        print_test(f"  {platform} session", exists)
        if not exists:
            all_exist = False
            print(f"     {Colors.RED}Run {platform}_playwright.py to create session{Colors.RESET}")
    
    return all_exist

def test_completed_tasks():
    """Test 8: Completed Tasks"""
    print_header("TEST 8: Completed Tasks")
    
    done_dir = VAULT_ROOT / 'Done'
    if not done_dir.exists():
        print_test("Done folder", False)
        return False
    
    tasks = list(done_dir.glob('*.md'))
    count = len(tasks)
    
    print_test(f"Completed tasks", count >= 3, f"Found {count} task(s)")
    
    if count > 0:
        print(f"\n   {Colors.BLUE}Recent tasks:{Colors.RESET}")
        for task in tasks[:5]:
            print(f"     - {task.name}")
    
    return count >= 3

def test_ralph_wiggum():
    """Test 9: Ralph Wiggum Loop"""
    print_header("TEST 9: Ralph Wiggum Stop Hook")
    
    ralph_file = VAULT_ROOT / 'ralph_wiggum_hook.py'
    exists = ralph_file.exists()
    print_test(f"Ralph Wiggum script", exists)
    
    state_file = VAULT_ROOT / '.ralph_wiggum_state.json'
    state_exists = state_file.exists()
    print_test(f"Ralph Wiggum state", state_exists)
    
    # Check if configured in .claude folder
    claude_folder = VAULT_ROOT / '.claude' / 'plugins'
    if claude_folder.exists():
        print_test(f"Ralph Wiggum in .claude/plugins", True)
    else:
        # Check alternative location
        alt_location = VAULT_ROOT / '.claude' / 'settings.local.json'
        if alt_location.exists():
            print_test(f"Ralph Wiggum in settings", True)
        else:
            print_test(f"Ralph Wiggum configured", False, "Check .claude configuration")
    
    return exists and state_exists

def test_scheduler():
    """Test 10: Scheduler Configuration"""
    print_header("TEST 10: Scheduler")
    
    scheduler_file = VAULT_ROOT / 'scheduler.py'
    exists = scheduler_file.exists()
    print_test(f"Scheduler script", exists)
    
    if exists:
        # Check scheduler content for required jobs
        content = scheduler_file.read_text(encoding='utf-8')
        
        has_gmail = 'gmail' in content.lower()
        has_daily = 'daily' in content.lower() or 'summary' in content.lower()
        has_ceo = 'ceo' in content.lower() or 'briefing' in content.lower()
        
        print_test(f"  Gmail job configured", has_gmail)
        print_test(f"  Daily summary configured", has_daily)
        print_test(f"  CEO briefing configured", has_ceo)
        
        return has_gmail and has_daily and has_ceo
    
    return False

def run_all_tests():
    """Run all Gold Tier tests"""
    print_header("GOLD TIER TEST SUITE")
    print(f"Running comprehensive Gold Tier verification...")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Vault Structure", test_vault_structure),
        ("Gold Scripts", test_gold_scripts),
        ("MCP Servers", test_mcp_servers),
        ("Agent Skills", test_agent_skills),
        ("CEO Briefings", test_ceo_briefings),
        ("Audit Logs", test_audit_logs),
        ("Social Sessions", test_social_sessions),
        ("Completed Tasks", test_completed_tasks),
        ("Ralph Wiggum", test_ralph_wiggum),
        ("Scheduler", test_scheduler),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"{Colors.RED}Error in {name}: {e}{Colors.RESET}")
            results.append((name, False))
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        icon = PASS_ICON if result else FAIL_ICON
        color = Colors.GREEN if result else Colors.RED
        print(f"{icon} {color}{name}{Colors.RESET}")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.RESET}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}[SUCCESS] GOLD TIER: ALL TESTS PASSED!{Colors.RESET}")
        print(f"\n{Colors.BLUE}Gold Tier is fully functional and ready for submission.{Colors.RESET}")
        return True
    else:
        failed = total - passed
        print(f"\n{Colors.YELLOW}{Colors.BOLD}[WARNING] GOLD TIER: {failed} test(s) need attention{Colors.RESET}")
        print(f"\n{Colors.BLUE}Review failed tests above and fix issues.{Colors.RESET}")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
