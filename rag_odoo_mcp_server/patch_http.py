# -*- coding: utf-8 -*-
"""
Patch Odoo's request handling so session.db is set from ?db=, X-Odoo-Database header,
or Bearer db:key token BEFORE routing. This fixes 404 when no db is set in odoo.conf.
"""
import logging

_logger = logging.getLogger(__name__)

_APPLIED = False


def _mcp_db_from_request(request):
    """Extract database name from query, X-Odoo-Database header, or Bearer db:key."""
    if not getattr(request, "httprequest", None):
        return None
    db = request.httprequest.args.get("db")
    if db:
        return db
    db = (request.httprequest.headers.get("X-Odoo-Database") or "").strip()
    if db:
        return db
    auth = (request.httprequest.headers.get("Authorization") or "").strip()
    if auth.startswith("Bearer "):
        token = auth[7:].strip()
        if ":" in token:
            return token.split(":", 1)[0].strip() or None
    return None


def apply_patch():
    """Set session.db from URL/header/token before _serve_db runs so routing finds the database."""
    global _APPLIED
    if _APPLIED:
        return
    try:
        import odoo.http as http
        # Find the class that has _serve_db (may be Request or Root request wrapper)
        target = None
        for name in ("Request", "Root", "Application"):
            cls = getattr(http, name, None)
            if cls and hasattr(cls, "_serve_db"):
                target = cls
                break
        if not target:
            _logger.debug("rag_odoo_mcp_server: no class with _serve_db found, skip patch")
            return
        _serve_db_orig = target._serve_db
        if getattr(_serve_db_orig, "_mcp_patched", False):
            return

        def _serve_db_patched(self):
            db = _mcp_db_from_request(self)
            if db and getattr(self, "session", None):
                self.session.db = db
            return _serve_db_orig(self)

        _serve_db_patched._mcp_patched = True
        target._serve_db = _serve_db_patched
        _APPLIED = True
        _logger.debug("rag_odoo_mcp_server: patched _serve_db for db from query/header/token")
    except Exception as e:
        _logger.warning("rag_odoo_mcp_server: could not patch _serve_db: %s", e)
