"""
Odoo MCP Server — Gold Tier
Connects to Odoo Community 19+ via JSON-RPC API.
Provides tools for Claude to interact with the accounting system.

Usage:
    python odoo_mcp_server.py                  # Start MCP server (stdio)
    python odoo_mcp_server.py --test           # Test Odoo connection

Requires: Odoo 19 running at http://localhost:8069
"""

import json
import sys
import os
import logging
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
ODOO_URL = os.environ.get("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.environ.get("ODOO_DB", "odoo")
ODOO_USER = os.environ.get("ODOO_USER", "admin")
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD", "admin")

VAULT_ROOT = Path(__file__).parent.resolve()
LOG_DIR = VAULT_ROOT / "Logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"odoo_mcp_{datetime.now():%Y-%m-%d}.log", encoding="utf-8"),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger(__name__)

# ── JSON-RPC Client ──────────────────────────────────────────────────────────

_request_id = 0


def jsonrpc(url: str, method: str, params: dict) -> dict:
    """Make a JSON-RPC 2.0 call to Odoo."""
    global _request_id
    _request_id += 1
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "id": _request_id,
        "params": params,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if "error" in result:
            raise Exception(f"Odoo error: {result['error']}")
        return result.get("result", {})
    except urllib.error.URLError as e:
        raise ConnectionError(f"Cannot connect to Odoo at {url}: {e}")


# ── Odoo API Wrapper ─────────────────────────────────────────────────────────

class OdooClient:
    def __init__(self, url=ODOO_URL, db=ODOO_DB, user=ODOO_USER, password=ODOO_PASSWORD):
        self.url = url.rstrip("/")
        self.db = db
        self.user = user
        self.password = password
        self.uid = None

    def authenticate(self) -> int:
        """Authenticate and return user ID."""
        result = jsonrpc(f"{self.url}/web/session/authenticate", "call", {
            "db": self.db,
            "login": self.user,
            "password": self.password,
        })
        self.uid = result.get("uid")
        if not self.uid:
            raise Exception("Authentication failed — check credentials and database name")
        logger.info(f"Authenticated as uid={self.uid}")
        return self.uid

    def call(self, model: str, method: str, args: list = None, kwargs: dict = None) -> any:
        """Call an Odoo model method via JSON-RPC."""
        if not self.uid:
            self.authenticate()
        return jsonrpc(f"{self.url}/web/dataset/call_kw", "call", {
            "model": model,
            "method": method,
            "args": args or [],
            "kwargs": kwargs or {},
        })

    def search_read(self, model: str, domain: list = None, fields: list = None, limit: int = 100) -> list:
        """Search and read records from an Odoo model."""
        if not self.uid:
            self.authenticate()
        return jsonrpc(f"{self.url}/web/dataset/call_kw", "call", {
            "model": model,
            "method": "search_read",
            "args": [domain or []],
            "kwargs": {
                "fields": fields or [],
                "limit": limit,
            },
        })

    def create(self, model: str, values: dict) -> int:
        """Create a new record."""
        if not self.uid:
            self.authenticate()
        return jsonrpc(f"{self.url}/web/dataset/call_kw", "call", {
            "model": model,
            "method": "create",
            "args": [values],
            "kwargs": {},
        })

    # ── Accounting Helpers ────────────────────────────────────────────────────

    def get_invoices(self, state: str = None, limit: int = 50) -> list:
        """Get invoices (account.move) from Odoo."""
        domain = [("move_type", "in", ["out_invoice", "in_invoice"])]
        if state:
            domain.append(("state", "=", state))
        return self.search_read("account.move", domain,
                                ["name", "partner_id", "amount_total", "state", "date", "move_type"],
                                limit)

    def get_journal_entries(self, limit: int = 50) -> list:
        """Get journal entries."""
        return self.search_read("account.move", [("move_type", "=", "entry")],
                                ["name", "date", "amount_total", "state", "ref"],
                                limit)

    def get_partners(self, limit: int = 100) -> list:
        """Get business partners/contacts."""
        return self.search_read("res.partner", [],
                                ["name", "email", "phone", "is_company", "customer_rank", "supplier_rank"],
                                limit)

    def get_products(self, limit: int = 100) -> list:
        """Get products."""
        return self.search_read("product.template", [],
                                ["name", "list_price", "standard_price", "type", "qty_available"],
                                limit)

    def get_account_balance_summary(self) -> dict:
        """Get a summary of account balances for CEO briefing."""
        try:
            accounts = self.search_read("account.account", [],
                                        ["name", "code", "account_type"], 200)
            invoices = self.get_invoices()
            total_receivable = sum(inv.get("amount_total", 0) for inv in invoices
                                   if inv.get("move_type") == "out_invoice" and inv.get("state") == "posted")
            total_payable = sum(inv.get("amount_total", 0) for inv in invoices
                                if inv.get("move_type") == "in_invoice" and inv.get("state") == "posted")
            return {
                "total_accounts": len(accounts),
                "total_receivable": total_receivable,
                "total_payable": total_payable,
                "net_position": total_receivable - total_payable,
                "open_invoices": len([i for i in invoices if i.get("state") == "posted"]),
            }
        except Exception as e:
            logger.error(f"Error getting balance summary: {e}")
            return {"error": str(e)}

    def test_connection(self) -> dict:
        """Test connection and return server info."""
        try:
            result = jsonrpc(f"{self.url}/web/session/get_session_info", "call", {})
            self.authenticate()
            return {
                "status": "connected",
                "url": self.url,
                "database": self.db,
                "uid": self.uid,
                "server_version": result.get("server_version", "unknown"),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


# ── MCP Server (stdio) ───────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "odoo_test_connection",
        "description": "Test connection to Odoo and return server info",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "odoo_get_invoices",
        "description": "Get invoices from Odoo accounting. Optional state filter: draft, posted, cancel",
        "inputSchema": {
            "type": "object",
            "properties": {
                "state": {"type": "string", "description": "Filter by state: draft, posted, cancel"},
                "limit": {"type": "integer", "default": 50},
            },
        },
    },
    {
        "name": "odoo_get_partners",
        "description": "Get business partners/contacts from Odoo",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 100}},
        },
    },
    {
        "name": "odoo_get_products",
        "description": "Get products from Odoo",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 100}},
        },
    },
    {
        "name": "odoo_get_balance_summary",
        "description": "Get accounting balance summary for CEO briefing (receivables, payables, net position)",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "odoo_create_invoice",
        "description": "Create a draft invoice in Odoo (requires approval to post)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "partner_name": {"type": "string", "description": "Customer/vendor name"},
                "amount": {"type": "number", "description": "Invoice amount"},
                "type": {"type": "string", "enum": ["out_invoice", "in_invoice"], "description": "out_invoice=customer, in_invoice=vendor"},
            },
            "required": ["partner_name", "amount"],
        },
    },
    {
        "name": "odoo_search_read",
        "description": "Generic search_read on any Odoo model",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Odoo model name (e.g. res.partner)"},
                "domain": {"type": "array", "description": "Search domain filter", "default": []},
                "fields": {"type": "array", "items": {"type": "string"}, "description": "Fields to return"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["model"],
        },
    },
]


def handle_tool_call(name: str, arguments: dict) -> str:
    """Execute an MCP tool and return JSON result."""
    client = OdooClient()
    try:
        if name == "odoo_test_connection":
            return json.dumps(client.test_connection(), indent=2)
        elif name == "odoo_get_invoices":
            result = client.get_invoices(arguments.get("state"), arguments.get("limit", 50))
            return json.dumps(result, indent=2, default=str)
        elif name == "odoo_get_partners":
            result = client.get_partners(arguments.get("limit", 100))
            return json.dumps(result, indent=2, default=str)
        elif name == "odoo_get_products":
            result = client.get_products(arguments.get("limit", 100))
            return json.dumps(result, indent=2, default=str)
        elif name == "odoo_get_balance_summary":
            result = client.get_account_balance_summary()
            return json.dumps(result, indent=2, default=str)
        elif name == "odoo_create_invoice":
            partner_name = arguments["partner_name"]
            amount = arguments["amount"]
            inv_type = arguments.get("type", "out_invoice")
            # Find or create partner
            partners = client.search_read("res.partner", [("name", "ilike", partner_name)], ["id", "name"], 1)
            if partners:
                partner_id = partners[0]["id"]
            else:
                partner_id = client.create("res.partner", {"name": partner_name})
            # Create draft invoice
            invoice_id = client.create("account.move", {
                "move_type": inv_type,
                "partner_id": partner_id,
                "invoice_line_ids": [(0, 0, {
                    "name": f"Invoice for {partner_name}",
                    "quantity": 1,
                    "price_unit": amount,
                })],
            })
            return json.dumps({"status": "created", "invoice_id": invoice_id, "state": "draft"}, indent=2)
        elif name == "odoo_search_read":
            result = client.search_read(
                arguments["model"],
                arguments.get("domain", []),
                arguments.get("fields"),
                arguments.get("limit", 50),
            )
            return json.dumps(result, indent=2, default=str)
        else:
            return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return json.dumps({"error": str(e)})


def run_mcp_stdio():
    """Run as MCP server over stdio."""
    logger.info("Odoo MCP Server starting (stdio mode)...")

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line.strip())
            method = request.get("method", "")
            req_id = request.get("id")

            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "odoo-mcp", "version": "1.0.0"},
                    },
                }
            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"tools": TOOLS},
                }
            elif method == "tools/call":
                tool_name = request["params"]["name"]
                tool_args = request["params"].get("arguments", {})
                result_text = handle_tool_call(tool_name, tool_args)
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": result_text}],
                    },
                }
            elif method == "notifications/initialized":
                continue
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }

            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()

        except json.JSONDecodeError:
            continue
        except Exception as e:
            logger.error(f"MCP error: {e}")
            if req_id:
                error_resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32603, "message": str(e)},
                }
                sys.stdout.write(json.dumps(error_resp) + "\n")
                sys.stdout.flush()


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--test" in sys.argv:
        print("Testing Odoo connection...")
        client = OdooClient()
        result = client.test_connection()
        print(json.dumps(result, indent=2))
    else:
        run_mcp_stdio()
