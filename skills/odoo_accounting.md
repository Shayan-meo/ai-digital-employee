# Skill: Odoo Accounting

## Description
Interact with Odoo Community ERP for accounting operations via MCP server.

## Trigger
Accounting-related tasks, invoice creation, weekly audit, financial queries.

## Available Operations
1. **Test Connection** — verify Odoo is reachable
2. **Get Invoices** — list customer/vendor invoices (filterable by state)
3. **Get Partners** — list business contacts
4. **Get Products** — list product catalog
5. **Balance Summary** — receivables, payables, net position
6. **Create Invoice** — create draft invoice (requires approval to post)
7. **Search Read** — generic query on any Odoo model

## Safety
- Invoice creation always starts as DRAFT (requires manual posting in Odoo)
- Financial transactions require human approval
- All operations logged to /Logs/odoo_mcp_*.log

## MCP Server
Configured in .mcp.json as "odoo" server. Connects via JSON-RPC to http://localhost:8069.
