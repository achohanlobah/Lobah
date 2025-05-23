# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

{
    'name': 'Invoice PDF Report',
    'summary': 'Invoice PDF Custom Report',
    'description': """
            This module adds PDF custom report for invoice
        """,
    'version': '1.0',
    'category': 'account',
    'author': 'Caret IT Solutions Pvt. Ltd.',
    'website': 'https://www.caretit.com',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'views/account_move_custom_view.xml',
        'views/res_company_view.xml',
        'report/report_invoice_marco.xml',
    ],
}
