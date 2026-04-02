# -*- coding: utf-8 -*-
"""
MCP server exposed as part of the Odoo HTTP server.
GET /mcp/sse — SSE stream (client connects here, receives session id).
POST /mcp/messages — JSON-RPC (client sends requests with session id).
No extra process: installing the module is enough.

IMPORTANT:
- When Odoo has multiple databases, add ?db=<dbname> to the URL.
- Use the URL that works for /mcp/health in your setup. If http://host:port/mcp/health works
  (no /odoo), use that base for SSE too: http://host:port/mcp/sse?db=mydb
  If your deployment only exposes Odoo under /odoo, then /odoo/mcp/... may be handled by the
  web frontend (controller/action) and show "Missing Action" — in that case use the root path.

When using mcp-remote (Cursor/Claude), add: --transport sse-only

If an API key is configured in Settings, clients must send it in the request:
  Authorization: Bearer <key>   or   X-API-Key: <key>
"""
import json
import logging
import queue
import secrets
import uuid
import threading

from odoo import http, registry, SUPERUSER_ID
from odoo.api import Environment
from odoo.http import request

from . import mcp_backend

_logger = logging.getLogger(__name__)

# Sentinel: when _dispatch_jsonrpc returns (resp, MCP_REQUEST_ENV_RESTORE), caller must restore request.env.
# Second element is the previous request.env, or MCP_REQUEST_ENV_RESTORE_NONE meaning "request.env was not set".
MCP_REQUEST_ENV_RESTORE_NONE = object()

MCP_API_KEY_PARAM = "rag_odoo_mcp_server.api_key"
MCP_API_KEY_USER_PARAM = "rag_odoo_mcp_server.api_key_user"
MCP_API_KEY_ADMIN_PARAM = "rag_odoo_mcp_server.api_key_admin"
MCP_REQUIRE_API_KEY_PARAM = "rag_odoo_mcp_server.require_api_key"


# Header and Bearer token can carry database name so you don't need ?db= or odoo.conf.
# Bearer format: "Bearer <db>:<api_key>" or "Bearer <api_key>". Header: X-Odoo-Database: <db>
MCP_DB_HEADER = "X-Odoo-Database"


def _get_db_from_bearer_token():
    """If Authorization is Bearer db:key, return (db, key); else return (None, token_or_none)."""
    auth = (request.httprequest.headers.get("Authorization") or "").strip()
    if not auth.startswith("Bearer "):
        return None, None
    token = auth[7:].strip()
    if ":" in token:
        db, key = token.split(":", 1)
        db, key = db.strip(), key.strip()
        return (db or None), (key or None)
    return None, (token or None)


def _get_db_name():
    """Database name from query, header X-Odoo-Database, Bearer db:key, session, or env."""
    db = request.httprequest.args.get("db")
    if db:
        return db
    db = (request.httprequest.headers.get(MCP_DB_HEADER) or "").strip()
    if db:
        return db
    db, _ = _get_db_from_bearer_token()
    if db:
        return db
    if getattr(request, "session", None) and getattr(request.session, "db", None):
        return request.session.db
    env = getattr(request, "env", None)
    if env and getattr(env, "cr", None) and getattr(env.cr, "dbname", None):
        return request.env.cr.dbname
    return None


def _get_company_id():
    """Extract company_id from query param or X-Odoo-Company header."""
    cid = request.httprequest.args.get("company_id")
    if cid:
        try:
            return int(cid)
        except (ValueError, TypeError):
            pass
    cid = (request.httprequest.headers.get("X-Odoo-Company") or "").strip()
    if cid:
        try:
            return int(cid)
        except (ValueError, TypeError):
            pass
    return None


def _ensure_mcp_session_db():
    """Bind session to db from query, header, or Bearer token so dispatch uses the correct database."""
    db = _get_db_name()
    if db and hasattr(request, "session"):
        request.session.db = db


def _get_request_api_key_from_token():
    """Return API key from Bearer token (either 'key' or 'db:key' format)."""
    _, key = _get_db_from_bearer_token()
    return key


def _mcp_require_db():
    """Return None or a 400 JSON response if db is missing."""
    if _get_db_name() is not None:
        return None
    return request.make_response(
        json.dumps({
            "error": "Missing database",
            "message": "Pass the database by: ?db= name in URL, header X-Odoo-Database: name, or Bearer token db:api_key.",
        }),
        status=400,
        headers=[
            ("Content-Type", "application/json"),
            ("Access-Control-Allow-Origin", "*"),
        ],
    )


def _get_require_api_key():
    """Return True if MCP should require an API key for this database."""
    db = _get_db_name()
    try:
        if db:
            reg = registry(db)
            with reg.cursor() as cr:
                env = Environment(cr, SUPERUSER_ID, {})
                val = env["ir.config_parameter"].get_param(MCP_REQUIRE_API_KEY_PARAM)
                return _parse_require_api_key(val)
        # No db in request: read from current env (e.g. single-DB or env already set)
        val = request.env["ir.config_parameter"].sudo().get_param(MCP_REQUIRE_API_KEY_PARAM)
        return _parse_require_api_key(val)
    except Exception as e:
        _logger.warning("MCP require_api_key read failed (fail secure): %s", e)
        return True


def _parse_require_api_key(val):
    """Parse require_api_key from ir.config_parameter (string or bool)."""
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    s = (str(val).strip()).lower()
    return s in ("true", "1", "yes")


def _get_configured_api_keys():
    """Return (user_key, admin_key, legacy_key) for the request's database. Any can be None if not set.
    legacy_key is the old single API key (rag_odoo_mcp_server.api_key); accepted for backward compatibility as admin.
    """
    db = _get_db_name()
    try:
        if db:
            reg = registry(db)
            with reg.cursor() as cr:
                env = Environment(cr, SUPERUSER_ID, {})
                user_key = (env["ir.config_parameter"].get_param(MCP_API_KEY_USER_PARAM) or "").strip() or None
                admin_key = (env["ir.config_parameter"].get_param(MCP_API_KEY_ADMIN_PARAM) or "").strip() or None
                legacy_key = (env["ir.config_parameter"].get_param(MCP_API_KEY_PARAM) or "").strip() or None
                return user_key, admin_key, legacy_key
        user_key = (request.env["ir.config_parameter"].sudo().get_param(MCP_API_KEY_USER_PARAM) or "").strip() or None
        admin_key = (request.env["ir.config_parameter"].sudo().get_param(MCP_API_KEY_ADMIN_PARAM) or "").strip() or None
        legacy_key = (request.env["ir.config_parameter"].sudo().get_param(MCP_API_KEY_PARAM) or "").strip() or None
        return user_key, admin_key, legacy_key
    except Exception as e:
        _logger.debug("Could not read MCP API keys: %s", e)
        return None, None, None


def _get_request_api_key():
    """Extract API key: Bearer (supports db:key format), X-API-Key header, or api_key query param."""
    key = _get_request_api_key_from_token()
    if key:
        return key
    key = (request.httprequest.headers.get("X-API-Key") or "").strip()
    if key:
        return key
    key = (request.httprequest.args.get("api_key") or "").strip()
    return key or None


def _mcp_api_key_required():
    """If "require API key" is on, check the request has a valid User or Admin token.
    Set request.mcp_allow_write = True only when Admin token is used; else False.
    Return None or a 403 response.
    We use 403 (not 401) so Odoo/proxies do not redirect to the login page (which returns HTML and
    breaks MCP clients that expect JSON/SSE).
    """
    request.mcp_allow_write = False
    if not _get_require_api_key():
        return None
    user_key, admin_key, legacy_key = _get_configured_api_keys()
    if not user_key and not admin_key and not legacy_key:
        return request.make_response(
            json.dumps({
                "error": "Forbidden",
                "message": "API key required but no token configured. Generate a User or Admin token in Settings → RAG Odoo MCP Server.",
            }),
            status=403,
            headers=[
                ("Content-Type", "application/json"),
                ("Cache-Control", "no-store, no-cache"),
                ("Access-Control-Allow-Origin", "*"),
            ],
        )
    provided = _get_request_api_key()
    if not provided:
        return request.make_response(
            json.dumps({"error": "Forbidden", "message": "Invalid or missing API key"}),
            status=403,
            headers=[
                ("Content-Type", "application/json"),
                ("Cache-Control", "no-store, no-cache"),
                ("Access-Control-Allow-Origin", "*"),
            ],
        )
    if admin_key and secrets.compare_digest(admin_key, provided):
        request.mcp_allow_write = True
        return None
    if user_key and secrets.compare_digest(user_key, provided):
        request.mcp_allow_write = False
        return None
    # Backward compatibility: accept legacy single API key (treated as admin)
    if legacy_key and secrets.compare_digest(legacy_key, provided):
        request.mcp_allow_write = True
        return None
    return request.make_response(
        json.dumps({"error": "Forbidden", "message": "Invalid or missing API key"}),
        status=403,
        headers=[
            ("Content-Type", "application/json"),
            ("Cache-Control", "no-store, no-cache"),
            ("Access-Control-Allow-Origin", "*"),
        ],
    )

_mcp_sessions = {}
_mcp_sessions_lock = threading.Lock()

MCP_PROTOCOL_VERSION = "2025-11-25"


def _get_allow_write(cr):
    """Return True if the current request is authorized for write tools (Admin token was used)."""
    return getattr(request, "mcp_allow_write", False)


def _get_session_queue(session_id):
    with _mcp_sessions_lock:
        data = _mcp_sessions.get(session_id)
        if data is None:
            return None
        return data["queue"] if isinstance(data, dict) else data


def _get_session_company_id(session_id):
    """Return the company_id stored at session creation, or None."""
    with _mcp_sessions_lock:
        data = _mcp_sessions.get(session_id)
        if isinstance(data, dict):
            return data.get("company_id")
        return None


def _create_session(company_id=None):
    session_id = str(uuid.uuid4())
    q = queue.Queue()
    with _mcp_sessions_lock:
        _mcp_sessions[session_id] = {"queue": q, "company_id": company_id}
    return session_id, q


def _drop_session(session_id):
    with _mcp_sessions_lock:
        _mcp_sessions.pop(session_id, None)


_ORM_TOOLS_WITH_COMPANY = frozenset({
    "odoo_search_read", "odoo_create", "odoo_write", "odoo_unlink", "odoo_execute",
})


def _get_default_company_id(cr):
    """Read default company_id from ir.config_parameter."""
    env = Environment(cr, SUPERUSER_ID, {})
    val = env['ir.config_parameter'].get_param('rag_odoo_mcp_server.default_company_id')
    if val:
        try:
            return int(val)
        except (ValueError, TypeError):
            pass
    return None


def _dispatch_jsonrpc(body, cr, session_company_id=None):
    """Handle a single JSON-RPC request. Returns response dict or None for notifications."""
    try:
        data = json.loads(body) if isinstance(body, (str, bytes)) else body
    except Exception as e:
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error: %s" % e}}
    req_id = data.get("id")
    method = data.get("method")
    params = data.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": "rag-odoo-mcp-server", "version": "0.1"},
            },
        }

    if method == "tools/list":
        tools = mcp_backend.TOOL_DEFINITIONS
        if not _get_allow_write(cr):
            tools = [t for t in tools if t["name"] not in mcp_backend.MCP_WRITE_TOOLS]
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": tools},
        }

    if method == "tools/call":
        name = (params.get("name") or "").strip()
        arguments = dict(params.get("arguments") or {})
        # Accept "table" as alias for "table_name" (some clients send "table").
        if name in ("get_table_row_count", "describe_table", "get_table_schema_pg"):
            if "table" in arguments and "table_name" not in arguments:
                arguments["table_name"] = arguments.pop("table")
        # Inject company_id for ORM tools only when explicitly set by client (session or request).
        # Do not inject system default here: it can break ORM tools on some setups (e.g. Odoo.sh).
        # Clients can pass company_id per tool call, or at SSE connect via ?company_id=.
        if name in _ORM_TOOLS_WITH_COMPANY and "company_id" not in arguments and session_company_id is not None:
            arguments = dict(arguments)
            arguments["company_id"] = session_company_id
        if not name:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": "Missing tool name"}}
        if name not in mcp_backend.DISPATCH:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": "Unknown tool: %s" % name}}
        if name in mcp_backend.MCP_WRITE_TOOLS and not _get_allow_write(cr):
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32602,
                    "message": "Write operations are disabled. Enable 'Allow Claude to create, edit and delete records' in Settings → RAG Odoo MCP Server.",
                },
            }
        try:
            env = Environment(cr, SUPERUSER_ID, {})
            fn, formatter = mcp_backend.DISPATCH[name]
            result = fn(cr, env, **arguments)
            text = formatter(result)
            # Commit write tools immediately so changes persist; never return success if commit fails.
            # Bind request.env so precommit hooks (e.g. sale.order _track_finalize) see a valid env
            # during commit() and when the cursor context manager exits (it also calls commit()).
            # Return (response, old_request_env) so caller can restore request.env after the with block.
            if name in mcp_backend.MCP_WRITE_TOOLS:
                try:
                    old_request_env = getattr(request, "env", None)
                    request.env = env
                    try:
                        cr.commit()
                    except Exception as commit_err:
                        if old_request_env is not None:
                            request.env = old_request_env
                        elif hasattr(request, "env"):
                            del request.env
                        _logger.exception("MCP commit failed after %s", name)
                        return (
                            {
                                "jsonrpc": "2.0",
                                "id": req_id,
                                "error": {
                                    "code": -32603,
                                    "message": "Tool succeeded but commit failed; changes were not saved: %s" % commit_err,
                                },
                            },
                            None,
                        )
                    # Leave request.env set until cursor __exit__ runs; return old env so caller restores.
                    return (
                        {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {"content": [{"type": "text", "text": text}]},
                        },
                        old_request_env if old_request_env is not None else MCP_REQUEST_ENV_RESTORE_NONE,
                    )
                except Exception as commit_err:
                    if old_request_env is not None:
                        request.env = old_request_env
                    elif hasattr(request, "env"):
                        del request.env
                    _logger.exception("MCP commit failed after %s", name)
                    return (
                        {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {
                                "code": -32603,
                                "message": "Tool succeeded but commit failed; changes were not saved: %s" % commit_err,
                            },
                        },
                        None,
                    )
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": text}]},
            }
        except Exception as e:
            msg = str(e)
            # Help LLM recover from selection field errors (e.g. product.template.type)
            if "Wrong value for" in msg and "type" in msg.lower():
                msg = "%s Use odoo_search_read on that model with fields=[\"type\"] to see valid type values (e.g. consu, service)." % msg
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": msg},
            }

    if method == "notifications/initialized":
        return None

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found: %s" % method}}


class McpController(http.Controller):

    # auth='none' so routes match even when no database is set in session (multi-db without db in odoo.conf).
    # Register both /mcp/... and /odoo/mcp/... so it works with or without /odoo mount.
    @http.route(["/mcp/sse", "/odoo/mcp/sse"], type="http", auth="none", csrf=False, save_session=False, methods=["GET"])
    def mcp_sse(self, **kw):
        """SSE endpoint. Connect here; receives session endpoint event, then message events."""
        _ensure_mcp_session_db()
        missing_db = _mcp_require_db()
        if missing_db:
            return missing_db
        unauth = _mcp_api_key_required()
        if unauth:
            return unauth
        company_id = _get_company_id()
        session_id, q = _create_session(company_id=company_id)
        path = (request.httprequest.path or "").rstrip("/")
        # When hit at /odoo/mcp/sse, client must POST to /odoo/mcp/messages/
        prefix = "/odoo" if path.startswith("/odoo/") else ""
        messages_uri = "%s/mcp/messages/?session_id=%s" % (prefix, session_id)
        db = request.httprequest.args.get("db")
        if db:
            messages_uri += "&db=%s" % db

        def stream():
            yield ("event: endpoint\ndata: %s\n\n" % messages_uri).encode("utf-8")
            try:
                while True:
                    try:
                        msg = q.get(timeout=25)
                    except queue.Empty:
                        yield b": keepalive\n\n"
                        continue
                    if msg is None:
                        break
                    payload = json.dumps(msg) if isinstance(msg, dict) else msg
                    yield ("event: message\ndata: %s\n\n" % payload).encode("utf-8")
            finally:
                _drop_session(session_id)

        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        }
        response = request.make_response(stream(), headers=list(headers.items()))
        response.headers["Content-Type"] = "text/event-stream"
        if hasattr(response, "content_type"):
            response.content_type = "text/event-stream"
        return response

    @http.route(["/mcp/messages/", "/odoo/mcp/messages/"], type="http", auth="none", csrf=False,
                methods=["POST", "OPTIONS"], save_session=False)
    def mcp_messages(self, **kw):
        """JSON-RPC POST endpoint. session_id from query param (matching official SDK)."""
        if request.httprequest.method == "OPTIONS":
            return request.make_response("", headers=[
                ("Access-Control-Allow-Origin", "*"),
                ("Access-Control-Allow-Methods", "POST, OPTIONS"),
                ("Access-Control-Allow-Headers", "Content-Type, mcp-session-id, Authorization, X-API-Key, X-Odoo-Database, X-Odoo-Company"),
            ])
        _ensure_mcp_session_db()
        missing_db = _mcp_require_db()
        if missing_db:
            return missing_db
        unauth = _mcp_api_key_required()
        if unauth:
            return unauth
        session_id = (
            request.httprequest.args.get("session_id")
            or request.httprequest.args.get("sessionId")
            or request.httprequest.headers.get("mcp-session-id")
        )
        if not session_id:
            return request.make_response(
                json.dumps({"error": "Missing sessionId"}), status=400,
                headers=[("Content-Type", "application/json")],
            )
        q = _get_session_queue(session_id)
        if not q:
            return request.make_response(
                json.dumps({"error": "Unknown or expired session"}), status=400,
                headers=[("Content-Type", "application/json")],
            )
        body = request.httprequest.get_data(as_text=True)
        db = _get_db_name()
        if not db:
            return request.make_response(
                json.dumps({"error": "Missing database", "message": "Add ?db=<database_name> to the URL."}),
                status=400, headers=[("Content-Type", "application/json")],
            )
        # Resolve effective company_id: per-request > session > system default (handled in dispatch)
        session_cid = _get_session_company_id(session_id)
        request_cid = _get_company_id()
        effective_company_id = request_cid or session_cid
        request_env_to_restore = None
        try:
            reg = registry(db)
            with reg.cursor() as cr:
                out = _dispatch_jsonrpc(body, cr, session_company_id=effective_company_id)
                if isinstance(out, tuple):
                    resp, request_env_to_restore = out
                else:
                    resp = out
                if resp is not None:
                    q.put(resp)
        except Exception as e:
            _logger.exception("MCP dispatch error")
            q.put({"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}})
        finally:
            if request_env_to_restore is MCP_REQUEST_ENV_RESTORE_NONE:
                if hasattr(request, "env"):
                    del request.env
            elif request_env_to_restore is not None:
                request.env = request_env_to_restore
        return request.make_response("", status=202, headers=[
            ("Content-Type", "application/json"),
            ("Access-Control-Allow-Origin", "*"),
        ])

    @http.route(["/mcp/health", "/odoo/mcp/health"], type="http", auth="none", csrf=False, methods=["GET"])
    def mcp_health(self, **kw):
        """Health check."""
        _ensure_mcp_session_db()
        missing_db = _mcp_require_db()
        if missing_db:
            return missing_db
        unauth = _mcp_api_key_required()
        if unauth:
            return unauth
        return request.make_response(
            json.dumps({"status": "ok", "server": "rag-odoo-mcp-server"}),
            headers=[("Content-Type", "application/json"), ("Access-Control-Allow-Origin", "*")],
        )
