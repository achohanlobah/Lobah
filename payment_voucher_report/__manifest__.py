# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

{
    'name': 'Payment Voucher Report',
    'summary': 'Payment Voucher Report',
    'description': """
        Payment Voucher Report """,
    'version': '1.0',
    'category': 'account',
    'author': 'Caret IT Solutions Pvt. Ltd.',
    'website': 'http://www.caretit.com',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'data/ir_sequence.xml',
        'security/ir.model.access.csv',
        'views/account_move_view.xml',
        'report/report_payment_voucher.xml',
        'views/res_currency_views.xml',
    ],
}
