# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

from odoo import api, models, _
from odoo.exceptions import UserError


class ProfitLossReport(models.AbstractModel):
    _name = 'report.profit_and_loss_custom_report.report_profit_loss'
    _description = 'Profit And Loss Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        return {
            'stockdata': data.get('get_profit_loss'),
            'data': data.get('form'),
        }
