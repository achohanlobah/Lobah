# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

from odoo import models, fields


class AccountAccountsInherit(models.Model):
    _inherit = "account.account"

    temp_accounts = fields.Boolean(string= 'Select', default=False)
   

class AccountAnalyticAccounts(models.Model):
    _inherit = "account.analytic.account"

    temp_analytics = fields.Boolean(string= 'Select', default=False)
