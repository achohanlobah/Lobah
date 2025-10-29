from odoo import api, models


class AccounAssets(models.Model):
    """Inherit account.asset model"""
    _inherit = "account.asset"

    def unlink(self):
        if self._context.get('is_disable_asset_deletion'):
            return True
        return super().unlink()
