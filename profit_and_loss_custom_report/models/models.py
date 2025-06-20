# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

from odoo import models, fields


# class profit_and_loss_custom_report(models.Model):
#     _name = 'profit_and_loss_custom_report.profit_and_loss_custom_report'
#     _description = 'profit_and_loss_custom_report.profit_and_loss_custom_report'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

class AccountAccountInherit(models.Model):
    _inherit = "account.account"

    temp_account_report = fields.Boolean(string= 'Select', default=False)

class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    temp_analytics_report = fields.Boolean(string= 'Select', default=False)

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
