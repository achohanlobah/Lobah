# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

from odoo import models, api


class AccountMoveLine(models.Model):
    """ Inherit account.move.line model"""
    _inherit = "account.move.line"


    @api.onchange('product_id')
    def _onchange_product_id(self):
        """ Used to set account id and tax based on product"""
        for line in self:
            if not line.product_id or line.display_type in ('line_section', 'line_note'):
                continue
            if line.move_id.partner_id.income_account:
                line.account_id = line.move_id.partner_id.income_account
            else:
                line.account_id = line._get_computed_account()
            taxes = line._get_computed_taxes()
            if taxes and line.move_id.fiscal_position_id:
                taxes = line.move_id.fiscal_position_id.map_tax(taxes)
            line.tax_ids = taxes
            line.product_uom_id = line.product_id.uom_id or line.product_id.uom_po_id
            line.price_unit = line.product_id.lst_price

        if len(self) == 1:
            return {'domain': {'product_uom_id': [('category_id', '=', self.product_uom_id.category_id.id)]}}
