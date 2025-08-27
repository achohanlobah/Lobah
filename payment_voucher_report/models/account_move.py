# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

import base64
from io import BytesIO
from odoo import models, fields, api
from odoo.tools import pdf
from odoo.exceptions import UserError

class AccountMove(models.Model):
    """Inherit account.move model"""
    _inherit = "account.move"

    payment_voucher_partner = fields.Many2one('res.partner', copy=False)
    wht_expense_ids = fields.One2many('wht.expense', 'account_move_id', string="WHT Expense", copy=False)
    pv_sequence = fields.Char(string="PV Sequence", copy=False)
    payment_voucher_currency_id = fields.Many2one('res.currency', copy=False)
    currency_rate = fields.Float(string="Currency Conversion Rate", default=1)
    merge_invoice_attachment_ids = fields.One2many('merge.invoice.attachments', 'account_move_id', string="Merge Attachments", copy=False)
    payment_voucher_journal_entry_id = fields.Many2one('account.move', copy=False)
    payment_voucher_payment_method = fields.Char(copy=False)

    def get_analytic_distribution(self, val):
        if val:
            val = val[0]
            return self.env['account.analytic.account'].browse(int(next(iter(val)))).name
        return ''

    def get_converted_currency_value(self):
        o = self
        # return o.currency_id._convert(o.get_pv_total(), o.currency_id.search([('name', '=', 'USD')], limit=1))
        if o.payment_voucher_currency_id:
            return o.get_pv_total() / o.currency_rate
        return o.get_pv_total()

    def get_pv_total(self):
        o = self
        lines = o.line_ids.filtered(lambda l: l.show_in_pv_report)
        return sum(lines.mapped('credit') + lines.mapped('debit'))

    def get_today_date(self):
        return fields.Datetime.today().strftime('%d %B %Y')

    @api.model_create_multi
    def create(self, vals):
        new_vals = []
        for val in vals:
            if val.get('payment_voucher_partner'):
                val.update({'pv_sequence': self.env['ir.sequence'].next_by_code('payment_voucher')})
            new_vals.append(val)
        return super().create(new_vals)

    def write(self, vals):
        if vals.get('payment_voucher_partner') and not self.pv_sequence:
            vals.update({'pv_sequence': self.env['ir.sequence'].next_by_code('payment_voucher')})
        return super().write(vals)

    def merge_voucher(self):
        data = []
        if not self.merge_invoice_attachment_ids:
            raise UserError('Please add attachments to merge.')
        # Merge multiple prepend attachment
        for attachment in self.merge_invoice_attachment_ids.sorted('sequence'):
            stream = pdf.to_pdf_stream(attachment.attachment_id)
            stream = pdf.add_banner(stream, self.name, logo=True)
            pdf_content = stream.getvalue()
            data.append(pdf_content)
            # data.append(base64.b64decode(attachment.attachment_id.datas))

        pdf_content = pdf.merge_pdf(data)
        attachment = self.env['ir.attachment'].create({
            'type': 'binary',
            'name': 'Merged-Attachments.pdf',
            'res_model': 'account.move',
            'res_id': self.id,
            'datas': base64.encodebytes(pdf_content),
        })
        return {
            'effect': {
                'type': 'rainbow_man',
                'message': "Merged attachment created successfully",
            },
        }

    def action_post(self):
        res = super(AccountMove, self).action_post()
        if self.wht_expense_ids:
            wht_journal = self.payment_voucher_journal_entry_id or self.copy()
            wht_journal.line_ids.unlink()
            wht_journal.ref = self.ref
            if self.payment_voucher_journal_entry_id:
                wht_journal.message_post(body="WHT Journal Updated")
            else:
                wht_journal.message_post(body="WHT Journal created")
            # wht_journal.pv_sequence = self.env['ir.sequence'].next_by_code('payment_voucher')
            for wht in self.wht_expense_ids:
                wht_journal.line_ids.create([{
                    "name": wht.name,
                    "account_id": wht.debit_account_id.id,
                    "debit": wht.amount,
                    "move_id": wht_journal.id,
                    'analytic_distribution': wht.account_move_line_id.analytic_distribution,
                }, {
                    "name": wht.name,
                    "account_id": wht.credit_account_id.id,
                    "credit": wht.amount,
                    "move_id": wht_journal.id,
                    'analytic_distribution': wht.account_move_line_id.analytic_distribution,
                }])
            self.payment_voucher_journal_entry_id = wht_journal.id
        return res

    def get_currency_in_words(self):
        o = self
        currency = o.payment_voucher_currency_id or o.currency_id
        return 'Only %s' % currency.amount_to_text(o.get_converted_currency_value())

class AccountMoveLine(models.Model):
    """Inherit account.move model"""
    _inherit = "account.move.line"

    def toggle_show_in_pv_report(self):
        self.ensure_one()
        self.show_in_pv_report = not self.show_in_pv_report
