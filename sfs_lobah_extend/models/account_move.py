from odoo import api, models


class AccountMove(models.Model):
    """Inherit account.move model"""
    _inherit = "account.move"

    def action_force_register_payment(self):
        """overide action_force_register_payment and enable payment for entry type"""
        # if any(m.move_type == 'entry' for m in self):
        #     raise UserError(_("You cannot register payments for miscellaneous entries."))
        return self.line_ids.action_register_payment()
