import xmlrpc.client

# Odoo Connection
ODOO_URL = "http://localhost:8069"
ODOO_DB = "odoo"
ODOO_USER = "shayanrehan386@gmail.com"
ODOO_PASS = "admin123"

# Connect
common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})
models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

if not uid:
    print("Login FAILED! Check credentials.")
    exit()

print("=" * 70)
print("ODOO INVENTORY - ALL PRODUCTS")
print("=" * 70)

# Get all products with category
products = models.execute_kw(ODOO_DB, uid, ODOO_PASS, "product.template", "search_read", [[]], {
    "fields": ["name", "categ_id", "list_price", "type"],
    "order": "categ_id, name"
})

current_cat = ""
total = 0
for p in products:
    cat = p["categ_id"][1] if p["categ_id"] else "No Category"
    if cat != current_cat:
        current_cat = cat
        print(f"\n--- {cat} ---")
    total += 1
    print(f"  {total}. {p['name']}  |  Rs. {p['list_price']:.0f}  |  {p['type']}")

print(f"\n{'=' * 70}")
print(f"TOTAL PRODUCTS: {total}")
print("=" * 70)
