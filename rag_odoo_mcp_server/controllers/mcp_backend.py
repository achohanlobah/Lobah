# -*- coding: utf-8 -*-
"""
MCP tool backend using Odoo's cursor and environment.
Used by the in-Odoo MCP controller; no standalone dependencies.
Supports read-only SQL tools and ORM-based data retrieval/write (search_read, create, write, unlink, execute).
"""
import json
import re


def _identifier_ok(name):
    """Allow only safe SQL identifiers (schema/table names)."""
    return name and re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name)


def _rows_to_dicts(cr, rows=None):
    """Convert cr.fetchall() + cr.description to list of dicts."""
    if rows is None:
        rows = cr.fetchall()
    if not cr.description or not rows:
        return []
    keys = [d[0] for d in cr.description]
    result = []
    for row in rows:
        r = dict(zip(keys, row))
        for k, v in r.items():
            if hasattr(v, "isoformat"):
                r[k] = v.isoformat()
            elif isinstance(v, (bytes, bytearray)):
                r[k] = v.decode("utf-8", errors="replace")
        result.append(r)
    return result


def list_tables(cr, env, schema="public"):
    if not _identifier_ok(schema):
        return []
    cr.execute("""
        SELECT c.relname AS table_name,
               pg_size_pretty(pg_total_relation_size(c.oid)) AS size
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s AND c.relkind = 'r'
        ORDER BY c.relname
    """, (schema,))
    return _rows_to_dicts(cr)


def describe_table(cr, env, table_name, schema="public"):
    if not _identifier_ok(schema) or not _identifier_ok(table_name):
        return []
    cr.execute("""
        SELECT a.attname AS column_name,
               pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
               NOT a.attnotnull AS nullable,
               pg_get_expr(d.adbin, d.adrelid) AS default_expr
        FROM pg_attribute a
        LEFT JOIN pg_attrdef d ON a.attrelid = d.adrelid AND a.attnum = d.adnum
        JOIN pg_class c ON a.attrelid = c.oid
        JOIN pg_namespace n ON c.relnamespace = n.oid
        WHERE n.nspname = %s AND c.relname = %s
          AND a.attnum > 0 AND NOT a.attisdropped
        ORDER BY a.attnum
    """, (schema, table_name))
    return _rows_to_dicts(cr)


def get_table_row_count(cr, env, table_name, schema="public"):
    if not _identifier_ok(schema) or not _identifier_ok(table_name):
        raise ValueError("Invalid schema or table name")
    # Identifiers validated: only [a-zA-Z0-9_], no SQL injection
    cr.execute("SELECT COUNT(*) FROM %s.%s" % (schema, table_name))
    return cr.fetchone()[0]


def run_readonly_query(cr, env, query, max_rows=500):
    q = query.strip()
    if not q.upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed. Got: " + q[:50])
    if re.search(r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|GRANT|REVOKE)\b", q, re.I):
        raise ValueError("Query must be read-only (SELECT only).")
    cr.execute(q)
    rows = cr.fetchall()
    rows = rows[:max_rows] if len(rows) > max_rows else rows
    columns = [d[0] for d in cr.description] if cr.description else []
    result = _rows_to_dicts(cr, rows)
    return {"row_count": len(result), "columns": columns, "rows": result}


def get_odoo_models_info(cr, env):
    cr.execute("""
        SELECT model, name, info
        FROM ir_model
        WHERE model IS NOT NULL AND model != ''
        ORDER BY model
        LIMIT 500
    """)
    return _rows_to_dicts(cr)


def get_table_schema_pg(cr, env, table_name, schema="public"):
    cols = describe_table(cr, env, table_name, schema or "public")
    if not _identifier_ok(schema) or not _identifier_ok(table_name):
        return {"table": table_name, "schema": schema or "public", "columns": [], "indexes": []}
    cr.execute("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = %s AND tablename = %s
    """, (schema or "public", table_name))
    indexes = _rows_to_dicts(cr)
    return {"table": table_name, "schema": schema or "public", "columns": cols, "indexes": indexes}


# ---------------------------------------------------------------------------
# ORM-based tools (data retrieval and management)
# ---------------------------------------------------------------------------

def _parse_domain(domain):
    """Parse domain from JSON string or list. Return a list of tuples."""
    if domain is None:
        return []
    if isinstance(domain, list):
        return domain
    if isinstance(domain, str):
        return json.loads(domain)
    return []


def _parse_values(values):
    """Parse values dict from JSON string or dict."""
    if values is None:
        return {}
    if isinstance(values, dict):
        return values
    if isinstance(values, str):
        return json.loads(values)
    return {}


def _parse_ids(ids):
    """Parse ids: int, list of int, or JSON string."""
    if ids is None:
        return []
    if isinstance(ids, int):
        return [ids]
    if isinstance(ids, list):
        return [int(x) for x in ids]
    if isinstance(ids, str):
        data = json.loads(ids)
        return [data] if isinstance(data, int) else [int(x) for x in data]
    return []


def _serialize_value(v):
    """Convert Odoo record/value to JSON-serializable (e.g. for display)."""
    if hasattr(v, "isoformat"):  # date, datetime
        return v.isoformat()
    if isinstance(v, (list, tuple)) and len(v) == 2 and isinstance(v[0], int):
        return v  # (id, name) display
    if hasattr(v, "id"):
        return {"id": v.id, "display_name": getattr(v, "display_name", str(v))}
    if isinstance(v, (bytes, bytearray)):
        return v.decode("utf-8", errors="replace")
    return v


def _apply_company_context(env, company_id):
    """Apply company context to the environment if company_id is provided."""
    if company_id is None:
        return env
    company_id = int(company_id)
    company = env['res.company'].browse(company_id)
    if not company.exists():
        raise ValueError(
            "Company not found: id=%s. Use list_companies to see available companies." % company_id
        )
    # Odoo 14+ has with_company; older versions use context
    if hasattr(env, 'with_company'):
        return env.with_company(company_id)
    return env.with_context(allowed_company_ids=[company_id])


def odoo_search_read(cr, env, model, domain=None, fields=None, limit=100, order=None, company_id=None):
    """
    Search and read records from an Odoo model (ORM).
    Use for: customers from Spain, products with low stock, today's sales orders, unpaid invoices, etc.
    """
    env = _apply_company_context(env, company_id)
    Model = env.get(model)
    if Model is None:
        raise ValueError(_model_not_found_msg(model))
    domain = _parse_domain(domain)
    if fields is None:
        fields = []
    if isinstance(fields, str):
        fields = json.loads(fields) if fields.strip() else []
    limit = min(int(limit), 500) if limit else 100
    order = order or ""
    records = Model.search_read(domain, fields or None, limit=limit, order=order or None)
    # Serialize for JSON (dates, many2one tuples, etc.)
    out = []
    for r in records:
        row = {}
        for k, v in r.items():
            row[k] = _serialize_value(v)
        out.append(row)
    return {"model": model, "count": len(out), "records": out}


def _model_not_found_msg(model):
    return (
        "Model not found: %s. Use get_odoo_models_info to list available models (names are module.model, e.g. website.website)."
        % model
    )


def odoo_create(cr, env, model, values, company_id=None):
    """Create one record in an Odoo model. values: dict of field names to values (JSON or dict)."""
    env = _apply_company_context(env, company_id)
    Model = env.get(model)
    if Model is None:
        raise ValueError(_model_not_found_msg(model))
    values = _parse_values(values)
    if not values:
        raise ValueError("values is required and must not be empty")
    record = Model.create(values)
    return {"model": model, "id": record.id, "created": True, "display_name": record.display_name}


def odoo_write(cr, env, model, ids, values, company_id=None):
    """Update record(s) in an Odoo model. ids: single id or list; values: dict (JSON or dict)."""
    env = _apply_company_context(env, company_id)
    Model = env.get(model)
    if Model is None:
        raise ValueError(_model_not_found_msg(model))
    ids = _parse_ids(ids)
    if not ids:
        raise ValueError("ids is required (integer or list of ids)")
    values = _parse_values(values)
    if not values:
        raise ValueError("values is required and must not be empty")
    records = Model.browse(ids)
    records.write(values)
    return {"model": model, "ids": ids, "updated": len(records)}


def odoo_unlink(cr, env, model, ids, company_id=None):
    """Delete record(s) from an Odoo model. ids: single id or list (JSON or list)."""
    env = _apply_company_context(env, company_id)
    Model = env.get(model)
    if Model is None:
        raise ValueError(_model_not_found_msg(model))
    ids = _parse_ids(ids)
    if not ids:
        raise ValueError("ids is required (integer or list of ids)")
    records = Model.browse(ids)
    n = len(records)
    records.unlink()
    return {"model": model, "ids": ids, "deleted": n}


def odoo_execute(cr, env, model, ids, method_name, args=None, kwargs=None, company_id=None):
    """
    Call a method on record(s), e.g. action_confirm on sale.order.
    args: list (JSON array), kwargs: dict (JSON object). Optional.
    """
    env = _apply_company_context(env, company_id)
    Model = env.get(model)
    if Model is None:
        raise ValueError(_model_not_found_msg(model))
    ids = _parse_ids(ids)
    if not ids:
        raise ValueError("ids is required (integer or list of ids)")
    args = json.loads(args) if isinstance(args, str) else (args or [])
    kwargs = json.loads(kwargs) if isinstance(kwargs, str) else (kwargs or {})
    records = Model.browse(ids)
    method = getattr(records, method_name, None)
    if method is None:
        raise ValueError("Method not found: %s on %s" % (method_name, model))
    result = method(*args, **kwargs)
    # Serialize result for display
    if result is None or isinstance(result, (bool, int, float, str)):
        pass  # keep as-is
    elif hasattr(result, "id") and not isinstance(result, (list, tuple)):
        result = {"id": result.id, "display_name": getattr(result, "display_name", str(result))}
    elif isinstance(result, (list, tuple)) and result and hasattr(result[0], "id"):
        result = [{"id": r.id, "display_name": getattr(r, "display_name", str(r))} for r in result]
    elif hasattr(result, "isoformat"):
        result = result.isoformat()
    return {"model": model, "ids": ids, "method": method_name, "result": result}


def list_companies(cr, env):
    """List all companies configured in Odoo (res.company)."""
    companies = env['res.company'].search_read(
        [], ['name', 'currency_id', 'parent_id'], order='id'
    )
    out = []
    for c in companies:
        out.append({
            'id': c['id'],
            'name': c['name'],
            'currency': c['currency_id'][1] if c['currency_id'] else None,
            'parent': c['parent_id'][1] if c['parent_id'] else None,
        })
    return {"companies": out, "count": len(out)}


def _format_list_companies(result):
    lines = ["Companies (%s):" % result.get("count", 0), ""]
    for c in result.get("companies", []):
        parent = " (parent: %s)" % c['parent'] if c.get('parent') else ""
        lines.append("  - id=%s  %s  [%s]%s" % (c['id'], c['name'], c.get('currency', '?'), parent))
    return "\n".join(lines)


def _format_search_read(result):
    lines = ["Model: %s | Records: %s" % (result.get("model", ""), result.get("count", 0)), ""]
    for r in result.get("records", [])[:50]:
        lines.append("  " + str(r))
    if result.get("count", 0) > 50:
        lines.append("  ... and %s more" % (result["count"] - 50))
    return "\n".join(lines)


def _format_create(result):
    return "Created %s (id=%s): %s" % (result.get("model", ""), result.get("id"), result.get("display_name", ""))


def _format_write(result):
    return "Updated %s record(s) in %s (ids=%s)" % (result.get("updated", 0), result.get("model", ""), result.get("ids", []))


def _format_unlink(result):
    return "Deleted %s record(s) from %s (ids=%s)" % (result.get("deleted", 0), result.get("model", ""), result.get("ids", []))


def _format_execute(result):
    return "Executed %s on %s (ids=%s). Result: %s" % (
        result.get("method", ""), result.get("model", ""), result.get("ids", []), result.get("result", "")
    )


# Formatters (same output as standalone mcp_server.py)
def _format_list_tables(result):
    lines = ["Tables in schema (total: %s):" % len(result), ""]
    for r in result:
        lines.append("  - %s  (%s)" % (r.get("table_name", "?"), r.get("size", "?")))
    return "\n".join(lines)


def _format_describe(result):
    if not result:
        return "No columns found (table or schema may not exist)."
    lines = ["Column | Type | Nullable | Default", "------ | ---- | -------- | -------"]
    for r in result:
        lines.append("%s | %s | %s | %s" % (r.get("column_name"), r.get("data_type"), r.get("nullable"), r.get("default_expr") or ""))
    return "\n".join(lines)


def _format_run_query(result):
    rows = result.get("rows", [])
    cols = result.get("columns", [])
    count = result.get("row_count", 0)
    if not cols:
        return "No columns (empty result). Row count: %s" % count
    header = " | ".join(cols)
    sep = "-" * min(80, len(header))
    lines = ["Rows returned: %s" % count, "Columns: %s" % cols, "", header, sep]
    for r in rows[:100]:
        line = " | ".join(str(r.get(c, "")) for c in cols)
        lines.append(line)
    if len(rows) > 100:
        lines.append("... and %s more rows" % (len(rows) - 100))
    return "\n".join(lines)


def _format_odoo_models(result):
    lines = ["Odoo models (ir_model) — %s entries:" % len(result), ""]
    for r in result[:80]:
        lines.append("  - %s  |  %s" % (r.get("model", ""), r.get("name") or ""))
    if len(result) > 80:
        lines.append("  ... and %s more" % (len(result) - 80))
    return "\n".join(lines)


def _format_schema_pg(result):
    lines = ["Table: %s.%s" % (result.get("schema", "public"), result.get("table", "")), ""]
    lines.append("Columns:")
    for c in result.get("columns", []):
        lines.append("  - %s: %s (nullable=%s)" % (c.get("column_name"), c.get("data_type"), c.get("nullable")))
    lines.append("")
    lines.append("Indexes:")
    for ix in result.get("indexes", []):
        lines.append("  - %s" % ix.get("indexname", ""))
    return "\n".join(lines)


TOOL_DEFINITIONS = [
    {"name": "list_tables", "description": "List all tables in the PostgreSQL schema (default: public). Returns table names and approximate size. Use this to discover Odoo tables.", "inputSchema": {"type": "object", "properties": {"schema": {"type": "string", "default": "public", "description": "Schema name (default: public)"}}}},
    {"name": "describe_table", "description": "Get column definitions for a table: column name, data type, nullable, default. Use after list_tables to inspect a specific table.", "inputSchema": {"type": "object", "properties": {"table_name": {"type": "string", "description": "Table name (e.g. res_partner, sale_order)"}, "schema": {"type": "string", "default": "public"}}, "required": ["table_name"]}},
    {"name": "get_table_row_count", "description": "Get the exact row count for a table. Useful to know table size before querying.", "inputSchema": {"type": "object", "properties": {"table_name": {"type": "string"}, "schema": {"type": "string", "default": "public"}}, "required": ["table_name"]}},
    {"name": "run_readonly_query", "description": "Run a read-only SQL query (SELECT only) against the Odoo PostgreSQL database. Use describe_table and list_tables first to build correct queries. Returns up to max_rows rows.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string", "description": "Single SELECT SQL statement"}, "max_rows": {"type": "integer", "default": 500, "maximum": 2000}}, "required": ["query"]}},
    {"name": "get_odoo_models_info", "description": "List Odoo ORM models from ir_model (model name, description). Helps map Odoo models to database tables (e.g. res.partner -> res_partner).", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "get_table_schema_pg", "description": "Get full table schema: columns and indexes. Use for detailed inspection of a table.", "inputSchema": {"type": "object", "properties": {"table_name": {"type": "string"}, "schema": {"type": "string", "default": "public"}}, "required": ["table_name"]}},
    # Company discovery
    {"name": "list_companies", "description": "List all companies configured in Odoo (res.company). Returns id, name, currency, and parent company. Use this to discover available companies before setting company_id on other tools.", "inputSchema": {"type": "object", "properties": {}}},
    # Data retrieval (ORM)
    {"name": "odoo_search_read", "description": "Search and read records from an Odoo model using domain and optional fields. Use for: 'customers from Spain' (res.partner, country_id.code=ES), 'products with stock below 10', 'today's sales orders over 1000', 'unpaid invoices'. Domain: list of [field, operator, value], e.g. [[\"country_id.code\", \"=\", \"ES\"]]. Fields: list of field names or empty for all.", "inputSchema": {"type": "object", "properties": {"model": {"type": "string", "description": "Odoo model technical name (e.g. res.partner, product.product, sale.order, account.move)"}, "domain": {"type": "string", "description": "JSON array of conditions, e.g. [[\"country_id.code\", \"=\", \"ES\"]] or [] for all"}, "fields": {"type": "string", "description": "JSON array of field names to return, e.g. [\"name\", \"email\"] or leave empty for all"}, "limit": {"type": "integer", "default": 100, "description": "Max records to return (cap 500)"}, "order": {"type": "string", "description": "Sort order, e.g. \"name asc\", \"date_order desc\""}, "company_id": {"type": "integer", "description": "Odoo company ID to scope operations. Use list_companies to see available companies. When set, operations run in that company's context (affects record visibility and defaults)."}}, "required": ["model"]}},
    # Data management (write) — create, edit, delete sale orders, purchase orders, invoices
    {"name": "odoo_create", "description": "Create one record in an Odoo model. Persists to DB. Use for: Sale orders (sale.order, required: partner_id; optional: order_line), Purchase orders (purchase.order), Invoices (account.move), Customers (res.partner), Products (product.template or product.product). Workflow: Prefer creating the sale order first with order_line using existing product IDs (from product.product); only create missing products when needed. Do not create many products one-by-one before creating the sale order — create the sale order with existing products, or create few products then the order. product.template: type field must be a valid selection value. Odoo 18 often uses 'consu' (consumable/goods) and 'service'; 'product' (storable) may not exist in all DBs. If you get 'Wrong value for product.template.type', run odoo_search_read(model='product.template', fields=['type'], limit=5) and use one of the type values returned (e.g. consu, service). order_line tax_id: set tax_id: [[6,0,[tax_ids]]] for taxed lines, tax_id: false for no tax; use odoo_search_read(account.tax) to find tax IDs.", "inputSchema": {"type": "object", "properties": {"model": {"type": "string", "description": "Odoo model: sale.order, purchase.order, account.move, res.partner, product.template, product.product, etc."}, "values": {"type": "string", "description": "JSON object of fields. For product.template use type: 'consu' or 'service' (check existing products if error). For order_line include tax_id."}, "company_id": {"type": "integer", "description": "Odoo company ID to scope operations. Use list_companies to see available companies."}}, "required": ["model", "values"]}},
    {"name": "odoo_write", "description": "Update existing record(s). Persists to DB. Use for: Edit sale order (sale.order), purchase order (purchase.order), invoice (account.move), customer (res.partner), or order lines (sale.order.line, purchase.order.line, account.move.line). ids: single id or JSON array; values: JSON object of field: value. For order/invoice lines: always set tax_id explicitly — tax_id: [[6, 0, [tax_ids]]] for lines with taxes, tax_id: false for lines without taxes. Use get_odoo_models_info or odoo_search_read(account.tax) to find tax IDs.", "inputSchema": {"type": "object", "properties": {"model": {"type": "string", "description": "Odoo model (e.g. sale.order, purchase.order, account.move, res.partner, sale.order.line, account.move.line)"}, "ids": {"type": "string", "description": "Record id(s): integer or JSON array, e.g. 42 or [1,2,3]"}, "values": {"type": "string", "description": "JSON object of field: value. For lines include tax_id when changing taxes."}, "company_id": {"type": "integer", "description": "Odoo company ID to scope operations. Use list_companies to see available companies."}}, "required": ["model", "ids", "values"]}},
    {"name": "odoo_unlink", "description": "Delete record(s) from an Odoo model. Persists to DB. Use for: Delete/cancel sale order (sale.order), purchase order (purchase.order), invoice (account.move), or any record. ids: single id or JSON array. Prefer cancelling orders/invoices via odoo_execute (action_cancel) when applicable.", "inputSchema": {"type": "object", "properties": {"model": {"type": "string", "description": "Odoo model (e.g. sale.order, purchase.order, account.move)"}, "ids": {"type": "string", "description": "Record id(s): integer or JSON array"}, "company_id": {"type": "integer", "description": "Odoo company ID to scope operations. Use list_companies to see available companies."}}, "required": ["model", "ids"]}},
    {"name": "odoo_execute", "description": "Call a method on record(s). Persists to DB. Use for: Confirm sale order (model=sale.order, method_name=action_confirm), confirm purchase (purchase.order, action_confirm), confirm/send invoice (account.move, action_post), cancel (action_cancel), create invoice from sale (sale.order, action_create_invoice). method_name: action_confirm, action_cancel, action_post, action_create_invoice, etc.", "inputSchema": {"type": "object", "properties": {"model": {"type": "string", "description": "Odoo model (e.g. sale.order, purchase.order, account.move)"}, "ids": {"type": "string", "description": "Record id(s): integer or JSON array"}, "method_name": {"type": "string", "description": "Method: action_confirm, action_cancel, action_post, action_create_invoice"}, "args": {"type": "string", "description": "Optional JSON array of positional arguments"}, "kwargs": {"type": "string", "description": "Optional JSON object of keyword arguments"}, "company_id": {"type": "integer", "description": "Odoo company ID to scope operations. Use list_companies to see available companies."}}, "required": ["model", "ids", "method_name"]}},
]

# Tools that modify data; we must commit after success so changes persist.
MCP_WRITE_TOOLS = frozenset({"odoo_create", "odoo_write", "odoo_unlink", "odoo_execute"})

DISPATCH = {
    "list_tables": (list_tables, _format_list_tables),
    "describe_table": (describe_table, _format_describe),
    "get_table_row_count": (get_table_row_count, lambda x: "Row count: %s" % x),
    "run_readonly_query": (run_readonly_query, _format_run_query),
    "get_odoo_models_info": (get_odoo_models_info, _format_odoo_models),
    "get_table_schema_pg": (get_table_schema_pg, _format_schema_pg),
    "list_companies": (list_companies, _format_list_companies),
    "odoo_search_read": (odoo_search_read, _format_search_read),
    "odoo_create": (odoo_create, _format_create),
    "odoo_write": (odoo_write, _format_write),
    "odoo_unlink": (odoo_unlink, _format_unlink),
    "odoo_execute": (odoo_execute, _format_execute),
}
