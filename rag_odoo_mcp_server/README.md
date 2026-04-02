# RAG Odoo MCP Server

Odoo 18 module that exposes an **MCP (Model Context Protocol)** server so Claude/Cursor can access and manage your Odoo data via natural language.

## API Endpoints (in-Odoo)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/mcp/sse?db=<database>` | SSE stream — connect here; client receives session endpoint. |
| POST | `/mcp/messages/?session_id=<id>&db=<database>` | JSON-RPC — send `tools/list`, `tools/call`. |
| GET | `/mcp/health?db=<database>` | Health check. |

When API key is required (Settings → RAG Odoo MCP Server):  
`Authorization: Bearer <key>`, header `X-API-Key: <key>`, or query `api_key=<key>` (e.g. for SSE: `/mcp/sse?db=<database>&api_key=<key>` if your client cannot send headers).

## Usage Examples

Once configured, you can query and manage Odoo data using natural language.

### Data retrieval

- **"Show me all customers from Spain"**  
  → `odoo_search_read` with `model="res.partner"`, `domain=[["country_id.code", "=", "ES"]]`

- **"Find products with stock below 10 units"**  
  → `odoo_search_read` on `product.product` / stock-related model, or `run_readonly_query` on stock tables

- **"List today's sales orders over $1000"**  
  → `odoo_search_read` with `model="sale.order"`, domain on `amount_total` and date

- **"Search for unpaid invoices from last month"**  
  → `odoo_search_read` with `model="account.move"`, domain on `payment_state` and date

### Data management (create, edit, delete — all persist to the database)

Write operations (`odoo_create`, `odoo_write`, `odoo_unlink`, `odoo_execute`) are committed after each successful `tools/call`, so records persist. Use the in-Odoo MCP endpoint (`/mcp/sse`) for these tools.

- **"Create a new customer contact for Acme Corporation"**  
  → `odoo_create(model="res.partner", values={"name": "Acme Corporation", "is_company": true})`

- **"Create a sale order for partner 5 with one product"**  
  → `odoo_create(model="sale.order", values={"partner_id": 5, "order_line": [[0, 0, {"product_id": 2, "product_uom_qty": 1, "price_unit": 10.0, "tax_id": [[6, 0, [<tax_id>]]]}]]})` for a taxed line, or `"tax_id": false` for a line without tax. Always set `tax_id` explicitly per line (use `odoo_search_read(model="account.tax", domain=[[["type_tax_use", "=", "sale"]]])` to get tax IDs).  
  Then confirm: `odoo_execute(model="sale.order", ids=<id>, method_name="action_confirm")`

- **"Create / edit / delete purchase orders or invoices"**  
  → `odoo_create(model="purchase.order", values={"partner_id": 3})` or `model="account.move"` with `move_type` and `partner_id`  
  → `odoo_write(model="sale.order", ids=<id>, values={...})` to edit  
  → `odoo_unlink(model="sale.order", ids=[<id>])` to delete, or `odoo_execute(..., method_name="action_cancel")` to cancel

- **"Add a new product called 'Premium Widget' with price $99.99"**  
  → `odoo_create(model="product.product", values={"name": "Premium Widget", "list_price": 99.99})`  
  (If using `product.template`, create template first then variant as needed.)

- **"Update the phone number for customer John Doe"**  
  → `odoo_search_read` to find the partner id, then  
  → `odoo_write(model="res.partner", ids=<id>, values={"phone": "+1 234 567 8900"})`

- **"Change the status of order SO/2024/001 to confirmed"**  
  → `odoo_search_read` to find the order by `name`, then  
  → `odoo_execute(model="sale.order", ids=<id>, method_name="action_confirm")`

- **"Delete the test contact we created earlier"**  
  → `odoo_unlink(model="res.partner", ids=[<id>])`

## MCP tools

| Tool | Purpose |
|------|--------|
| `list_tables`, `describe_table`, `get_table_row_count`, `run_readonly_query` | Read-only SQL / schema discovery |
| `get_odoo_models_info`, `get_table_schema_pg` | Model and table metadata |
| `odoo_search_read` | Search and read records (ORM) — main tool for “show me …” / “find …” |
| `odoo_create` | Create one record |
| `odoo_write` | Update record(s) |
| `odoo_unlink` | Delete record(s) |
| `odoo_execute` | Call a method on record(s) (e.g. `action_confirm`) |

ORM tools (`odoo_search_read`, `odoo_create`, `odoo_write`, `odoo_unlink`, `odoo_execute`) are available only when using the **in-Odoo MCP** (e.g. `/mcp/sse`). The standalone server (Python process with PostgreSQL only) exposes the read-only SQL tools only.

## Troubleshooting

- **"Server transport closed unexpectedly"** in Cursor/Claude logs after idle or when closing the MCP panel is normal: the client closed the connection and the proxy shuts down. No change needed on the Odoo side.
- **"Model not found: X"** — Odoo model names are `module.model` (e.g. `website.website`, not `website`). Use the `get_odoo_models_info` tool to list available models.
- **Taxes on order/invoice lines** — When creating or editing sale order lines, purchase order lines, or invoice lines, always set `tax_id` explicitly: `tax_id: [[6, 0, [<account.tax id(s)>]]]` for lines that must have taxes, and `tax_id: false` (or `[[5, 0, 0]]`) for lines that must have no taxes. Find tax IDs with `odoo_search_read(model="account.tax", domain=[[["type_tax_use", "in", ["sale", "purchase"]]]])`.
- **"Wrong value for product.template.type"** — The `type` field is a selection; valid values depend on the database (often `consu` and `service` in Odoo 18; `product` may not exist). Run `odoo_search_read(model="product.template", fields=["type"], limit=5)` and use one of the returned values (e.g. `consu` for goods, `service` for services).
- **Sale order not created / stuck** — Prefer creating the sale order first with `order_line` using existing product IDs (from `product.product`). Only create missing products when needed. Avoid creating many products one-by-one before creating the sale order; create the order with existing products, or create a few products then the order.
