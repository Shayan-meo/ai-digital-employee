"""
OdooClient — XML-RPC client for Odoo 19+
Uses the proven xmlrpc approach from check_products.py
"""

import xmlrpc.client

ODOO_URL = "http://localhost:8069"
ODOO_DB = "odoo"
ODOO_USER = "shayanrehan386@gmail.com"
ODOO_PASSWORD = "admin123"


class OdooClient:
    def __init__(self):
        self.url = ODOO_URL
        self.db = ODOO_DB
        self.user = ODOO_USER
        self.password = ODOO_PASSWORD
        self.uid = None
        self.models = None

    def authenticate(self):
        common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.uid = common.authenticate(self.db, self.user, self.password, {})
        if not self.uid:
            raise Exception("Authentication failed — check credentials")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
        return self.uid

    def search_read(self, model, domain=None, fields=None, limit=200, order=None):
        if not self.uid:
            self.authenticate()
        kwargs = {"fields": fields or [], "limit": limit}
        if order:
            kwargs["order"] = order
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, "search_read",
            [domain or []], kwargs
        )

    def get_products(self):
        return self.search_read("product.template", [],
            ["name", "list_price", "standard_price", "type", "categ_id", "qty_available"],
            order="categ_id, name")

    def get_partners(self):
        return self.search_read("res.partner", [("customer_rank", ">", 0)],
            ["name", "email", "phone", "is_company", "customer_rank", "city", "country_id"])

    def get_all_partners(self):
        return self.search_read("res.partner", [],
            ["name", "email", "phone", "is_company", "customer_rank", "supplier_rank", "city", "country_id"])

    def get_invoices(self):
        return self.search_read("account.move",
            [("move_type", "in", ["out_invoice", "in_invoice"])],
            ["name", "partner_id", "amount_total", "amount_residual", "state", "date", "move_type", "invoice_date_due"])

    def get_categories(self):
        return self.search_read("product.category", [], ["name", "parent_id", "complete_name"])

    def get_accounting_summary(self):
        invoices = self.get_invoices()
        receivable = sum(i.get("amount_total", 0) for i in invoices
                        if i.get("move_type") == "out_invoice" and i.get("state") == "posted")
        payable = sum(i.get("amount_total", 0) for i in invoices
                     if i.get("move_type") == "in_invoice" and i.get("state") == "posted")
        return {
            "total_receivable": receivable,
            "total_payable": payable,
            "net_position": receivable - payable,
            "open_invoices": len([i for i in invoices if i.get("state") == "posted"]),
            "draft_invoices": len([i for i in invoices if i.get("state") == "draft"]),
        }

    def get_sale_orders(self):
        return self.search_read("sale.order", [],
            ["name", "partner_id", "amount_total", "state", "date_order"])

    def test_connection(self):
        try:
            self.authenticate()
            return {"status": "connected", "uid": self.uid}
        except Exception as e:
            return {"status": "error", "message": str(e)}
