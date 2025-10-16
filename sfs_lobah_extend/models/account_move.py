from odoo import api, models, fields


class AccountMove(models.Model):
    """Inherit account.move model"""
    _inherit = "account.move"

    disable_asset_deletion = fields.Boolean(string="Disable Assets deletion on reset to draft", default=False)

    def action_force_register_payment(self):
        """overide action_force_register_payment and enable payment for entry type"""
        # if any(m.move_type == 'entry' for m in self):
        #     raise UserError(_("You cannot register payments for miscellaneous entries."))
        return self.line_ids.action_register_payment()

    def button_draft(self):
        is_disable_asset_deletion = any(rec.disable_asset_deletion for rec in self)
        if is_disable_asset_deletion:
            ctx = dict(self.env.context, is_disable_asset_deletion=True)
            self = self.with_context(ctx)
        return super().button_draft()
