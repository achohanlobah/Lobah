# -*- coding: utf-8 -*-
# MCP is exposed via the Odoo HTTP server at /mcp/sse and /mcp/messages (no separate process).
# Optional standalone: python -m rag_odoo_mcp_server.mcp_server --host 0.0.0.0 --port 8000
# Patch request handling first so session.db is set from URL/header/token before routing (fixes 404).
from . import patch_http
patch_http.apply_patch()

from . import controllers
from . import models
