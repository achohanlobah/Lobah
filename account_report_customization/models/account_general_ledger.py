# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT

class AccountGeneralLedgerReport(models.AbstractModel):
    _inherit = "account.general.ledger.report.handler"
    _description = "General Ledger Report"
    #_inherit = "account.report"

    # @api.model
    # def _get_aml_line(self, options, account, aml, cumulated_balance):
    #     if aml['payment_id']:
    #         caret_type = 'account.payment'
    #     else:
    #         caret_type = 'account.move'
    #
    #     if aml['ref'] and aml['name']:
    #         title = '%s - %s' % (aml['name'], aml['ref'])
    #     elif aml['ref']:
    #         title = aml['ref']
    #     elif aml['name']:
    #         title = aml['name']
    #     else:
    #         title = ''
    #
    #     if (aml['currency_id'] and aml['currency_id'] != account.company_id.currency_id.id) or account.currency_id:
    #         currency = self.env['res.currency'].browse(aml['currency_id'])
    #     else:
    #         currency = False
    #
    #     if aml['analytic_account_id']:
    #         analytic = self.env['account.analytic.account'].browse(aml['analytic_account_id']).name
    #     else:
    #         analytic = '-'
    #
    #     lable = ''
    #     if aml['lable']:
    #         a_string = aml['lable']
    #         if len(a_string) > 45:
    #             lable = a_string[0:45]
    #         else:
    #             lable = a_string
    #     else:
    #         lable = lable
    #
    #     columns = [
    #             {'name': format_date(self.env, aml['date']), 'class': 'date'},
    #             {'name': aml['move_name'], 'title': title, 'class': 'whitespace_print'},
    #             {'name': lable, 'class': 'whitespace_print'},
    #             {'name': analytic, 'class': 'whitespace_print'},
    #             {'name': aml['partner_name'], 'title': aml['partner_name'], 'class': 'whitespace_print'},
    #             {'name': self.format_value(aml['debit'], blank_if_zero=True), 'class': 'number'},
    #             {'name': self.format_value(aml['credit'], blank_if_zero=True), 'class': 'number'},
    #             {'name': self.format_value(cumulated_balance), 'class': 'number'},
    #         ]
    #
    #     if self.user_has_groups('base.group_multi_currency'):
    #         columns.insert(3, {'name': currency and aml['amount_currency'] and self.format_value(aml['amount_currency'], currency=currency, blank_if_zero=True) or '', 'class': 'number'})
    #     return {
    #         'id': aml['id'],
    #         'caret_options': caret_type,
    #         'class': 'top-vertical-align',
    #         'parent_id': 'account_%d' % aml['account_id'],
    #         'name': aml['move_name'],
    #         'columns': columns,
    #         'level': 6,
    #     }

    # @api.model
    # def _get_columns_name(self, options):
    #     columns_names = [
    #         {'name': ''},
    #         {'name': _('Date'), 'class': 'date'},
    #         {'name': _('Voucher Number')},
    #         {'name': _('Label')},
    #         {'name': _('Analytic Account')},
    #         {'name': _('Partner')},
    #         {'name': _('Debit'), 'class': 'number'},
    #         {'name': _('Credit'), 'class': 'number'},
    #         {'name': _('Balance'), 'class': 'number'},
    #
    #     ]
    #     if self.user_has_groups('base.group_multi_currency'):
    #         columns_names.insert(4, {'name': _('Currency'), 'class': 'number'})
    #     return columns_names

    # TODO: Commented this method becuase in the base method removed this key(colspan)
    # def _get_account_title_line(self, options, account, amount_currency, debit, credit, balance, has_lines):
    #     has_foreign_currency = account.currency_id and account.currency_id != account.company_id.currency_id or False
    #
    #     unfold_all = self._context.get('print_mode') and not options.get('unfolded_lines')
    #
    #     name = '%s %s' % (account.code, account.name)
    #
    #     max_length = self._context.get('print_mode') and 100 or 60
    #     if len(name) > max_length and not self._context.get('no_format'):
    #         name = name[:max_length] + '...'
    #     columns = [
    #         {'name': self.format_value(debit), 'class': 'number'},
    #         {'name': self.format_value(credit), 'class': 'number'},
    #         {'name': self.format_value(balance), 'class': 'number'},
    #     ]
    #     if self.user_has_groups('base.group_multi_currency'):
    #         columns.insert(0, {'name': has_foreign_currency and self.format_value(amount_currency, currency=account.currency_id, blank_if_zero=True) or '', 'class': 'number'})
    #     return {
    #         'id': 'account_%d' % account.id,
    #         'name': name,
    #         'title_hover': name,
    #         'columns': columns,
    #         'level': 2,
    #         'unfoldable': has_lines,
    #         'unfolded': has_lines and 'account_%d' % account.id in options.get('unfolded_lines') or unfold_all,
    #         'colspan': 6,
    #         'class': 'o_account_reports_totals_below_sections' if self.env.company.totals_below_sections else '',
    #         }

    # @api.model
    # def _get_initial_balance_line(self, options, account, amount_currency, debit, credit, balance):
    #     # MIG: Method not available in 17
    #     columns = [
    #         {'name': self.format_value(debit), 'class': 'number'},
    #         {'name': self.format_value(credit), 'class': 'number'},
    #         {'name': self.format_value(balance), 'class': 'number'},
    #     ]
    #
    #     has_foreign_currency = account.currency_id and account.currency_id != account.company_id.currency_id or False
    #     if self.user_has_groups('base.group_multi_currency'):
    #         columns.insert(0, {'name': has_foreign_currency and self.format_value(amount_currency, currency=account.currency_id, blank_if_zero=True) or '', 'class': 'number'})
    #     return {
    #         'id': 'initial_%d' % account.id,
    #         'class': 'o_account_reports_initial_balance',
    #         'name': _('Initial Balance'),
    #         'parent_id': 'account_%d' % account.id,
    #         'columns': columns,
    #         'colspan': 6,
    #     }

    # @api.model
    # def _get_account_total_line(self, options, account, amount_currency, debit, credit, balance):
    # # MIG: Method not available in 17
    #     has_foreign_currency = account.currency_id and account.currency_id != account.company_id.currency_id or False
    #
    #     columns = []
    #     if self.user_has_groups('base.group_multi_currency'):
    #         columns.append({'name': has_foreign_currency and self.format_value(amount_currency, currency=account.currency_id, blank_if_zero=True) or '', 'class': 'number'})
    #
    #     columns += [
    #         {'name': self.format_value(debit), 'class': 'number'},
    #         {'name': self.format_value(credit), 'class': 'number'},
    #         {'name': self.format_value(balance), 'class': 'number'},
    #     ]
    #
    #     return {
    #         'id': 'total_%s' % account.id,
    #         'class': 'o_account_reports_domain_total',
    #         'parent_id': 'account_%s' % account.id,
    #         'name': _('Total %s', account["display_name"]),
    #         'columns': columns,
    #         'colspan': 6,
    #     }

    # TODO: Commented this method becuase in the base method removed this key(colspan)
    # @api.model
    # def _get_total_line(self, options, debit, credit, balance):
    #     return {
    #         'id': 'general_ledger_total_%s' % self.env.company.id,
    #         'name': _('Total'),
    #         'class': 'total',
    #         'level': 1,
    #         'columns': [
    #             {'name': self.format_value(debit), 'class': 'number'},
    #             {'name': self.format_value(credit), 'class': 'number'},
    #             {'name': self.format_value(balance), 'class': 'number'},
    #         ],
    #         'colspan': self.user_has_groups('base.group_multi_currency') and 6 or 7,
    #     }
