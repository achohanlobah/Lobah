# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

from odoo import models, fields, api


class WHTExpense(models.Model):
    _name = "wht.expense"
    _description = "WHT Expense"

    account_move_id = fields.Many2one("account.move")
    account_move_line_id = fields.Many2one("account.move.line")
    debit_account_id = fields.Many2one("account.account")
    credit_account_id = fields.Many2one("account.account")
    name = fields.Char()
    amount_percent = fields.Float()
    amount = fields.Float()

    @api.onchange("account_move_line_id")
    def _onchange_account_move_line_id(self):
        for rec in self:
            rec.name = rec.account_move_line_id.name
            rec._onchange_amount_percent()

    @api.onchange("amount_percent")
    def _onchange_amount_percent(self):
        for rec in self:
            amount = rec.account_move_line_id.debit or rec.account_move_line_id.credit
            if amount and rec.amount_percent:
                rec.amount = (amount / 100) * rec.amount_percent
