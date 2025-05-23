# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

from odoo import models


class BalanceSheetReport(models.AbstractModel):
    _name = 'report.account_balance_sheet.account_balance_sheet'
    _description = 'Balance Sheet Report'
