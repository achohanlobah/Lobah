# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

from odoo import models, fields


class AccountMove(models.Model):
    """Inherit account.move model"""
    _inherit = "account.move"

    purchase_order_number = fields.Char(string= 'Purchase Order No')
    projectname = fields.Text(string= 'Project Name')
    bank_account_id = fields.Many2one('res.partner.bank',string="Bank Account Number")
    notes = fields.Text(string="Description")
    is_contract =   fields.Boolean(string="For Contract?")
    contract_order_number = fields.Char(string= 'Contract No')
    internal_custom_invoice_no = fields.Char(string="Invoice No")
    show_project_info = fields.Boolean(string="Show Project Info?",default=True,
                                       help="If checked true, than it'll show project and purchase info"
                                            " in Macro invoice report")

    def get_allowed_company_id(self):
        """ used to get company name"""
        allowed_company_id = False
        company_ids = self._context.get('allowed_company_ids', [])
        if company_ids:
            allowed_company_id = self.env['res.company'].browse(company_ids[0])
        return allowed_company_id

    def amount_to_text(self, amount, currency):
        """ Used to convert amount in words """
        convert_amount_in_words = self.currency_id.amount_to_text(amount)
        convert_amount_in_words = convert_amount_in_words.replace('And', '')
        # convert_amount_in_words = convert_amount_in_words.replace('and', '')
        convert_amount_in_words = convert_amount_in_words.replace('Riyal', 'Saudi Riyals')
        convert_amount_in_words = convert_amount_in_words.replace('Dollars', 'US Dollars')
        return convert_amount_in_words

    def invoice_amount_in_words(self, lang, amount):
        """ Used to convert amount in arabic words """
        convert_amount_in_words_arabic = self.currency_id.with_context(lang='ar_001').amount_to_text(amount)
        convert_amount_in_words_arabic = convert_amount_in_words_arabic.replace('and', '')
        convert_amount_in_words_arabic = convert_amount_in_words_arabic.replace('Riyal', 'Saudi Riyals')
        convert_amount_in_words_arabic = convert_amount_in_words_arabic.replace('Dollars', 'US Dollars')
        convert_amount_in_words_arabic = convert_amount_in_words_arabic.replace('Saudi Riyals', 'ريال سعودي')
        convert_amount_in_words_arabic = convert_amount_in_words_arabic.replace('Halala', 'هللة')
        convert_amount_in_words_arabic = convert_amount_in_words_arabic.replace('US Dollars', 'دولار أمريكي')
        convert_amount_in_words_arabic = convert_amount_in_words_arabic.replace('Cents', 'هللة')
        convert_amount_in_words_arabic = convert_amount_in_words_arabic.replace('Euros', 'يورو')
        return convert_amount_in_words_arabic
