# -*- coding: utf-8 -*-

import secrets

from odoo import fields, models


MCP_API_KEY_PARAM = 'rag_odoo_mcp_server.api_key'  # legacy, unused
MCP_API_KEY_USER_PARAM = 'rag_odoo_mcp_server.api_key_user'
MCP_API_KEY_ADMIN_PARAM = 'rag_odoo_mcp_server.api_key_admin'
MCP_REQUIRE_API_KEY_PARAM = 'rag_odoo_mcp_server.require_api_key'
MCP_DEFAULT_COMPANY_PARAM = 'rag_odoo_mcp_server.default_company_id'


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mcp_endpoint_hint = fields.Char(
        string='MCP endpoint',
        readonly=True,
        default='http://<your-odoo>/mcp/sse?db=<database>',
        help='MCP runs inside Odoo. Use this URL in Cursor/Claude with mcp-remote (--transport sse-only, --allow-http). '
             'Replace <your-odoo> and <database> with your base URL and database name.',
    )

    require_api_key = fields.Boolean(
        string='Require API key for MCP',
        help='If checked, clients must send a valid User or Admin token. If not checked, no token is required (read-only).',
    )

    user_token_set = fields.Boolean(
        string='User token (read-only)',
        readonly=True,
        help='User token: Claude can only search and read data. Give this token to standard users.',
    )

    admin_token_set = fields.Boolean(
        string='Admin token (read+write)',
        readonly=True,
        help='Admin token: Claude can create, edit and delete records. Give only to managers or admins.',
    )

    mcp_default_company_id = fields.Many2one(
        'res.company',
        string='Default MCP Company',
        help='Default company context for MCP tools. If set, all ORM operations will run in this '
             'company context unless overridden per-tool or per-request. Leave empty for no default '
             '(all companies visible).',
    )

    def get_values(self):
        res = super().get_values()
        val = self.env['ir.config_parameter'].sudo().get_param(MCP_REQUIRE_API_KEY_PARAM)
        res['require_api_key'] = (str(val or '').strip().lower() in ('true', '1', 'yes'))
        user_key = (self.env['ir.config_parameter'].sudo().get_param(MCP_API_KEY_USER_PARAM) or '').strip()
        admin_key = (self.env['ir.config_parameter'].sudo().get_param(MCP_API_KEY_ADMIN_PARAM) or '').strip()
        res['user_token_set'] = bool(user_key)
        res['admin_token_set'] = bool(admin_key)
        default_cid = self.env['ir.config_parameter'].sudo().get_param(MCP_DEFAULT_COMPANY_PARAM)
        if default_cid:
            try:
                res['mcp_default_company_id'] = int(default_cid)
            except (ValueError, TypeError):
                pass
        return res

    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            MCP_REQUIRE_API_KEY_PARAM, 'True' if self.require_api_key else 'False'
        )
        self.env['ir.config_parameter'].sudo().set_param(
            MCP_DEFAULT_COMPANY_PARAM,
            str(self.mcp_default_company_id.id) if self.mcp_default_company_id else '',
        )

    def action_generate_mcp_api_key_user(self):
        """Generate a read-only (user) API key; show it once in a popup."""
        self.ensure_one()
        new_key = secrets.token_urlsafe(32)
        self.env['ir.config_parameter'].sudo().set_param(MCP_API_KEY_USER_PARAM, new_key)
        return {
            'type': 'ir.actions.act_window',
            'name': 'User token (read-only) — copy and store securely',
            'res_model': 'rag_odoo_mcp_server.generate_api_key_wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_api_key_display': new_key,
                'default_token_type': 'User (read-only)',
            },
        }

    def action_generate_mcp_api_key_admin(self):
        """Generate a read+write (admin) API key; show it once in a popup."""
        self.ensure_one()
        new_key = secrets.token_urlsafe(32)
        self.env['ir.config_parameter'].sudo().set_param(MCP_API_KEY_ADMIN_PARAM, new_key)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Admin token (read+write) — copy and store securely',
            'res_model': 'rag_odoo_mcp_server.generate_api_key_wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_api_key_display': new_key,
                'default_token_type': 'Admin (read+write)',
            },
        }
