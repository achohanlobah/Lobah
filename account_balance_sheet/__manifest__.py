# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

{
    'name': "Account Balance Sheet",
    'summary': """Balance Sheet""",
    'description': """Add Balance Sheet report in PDF and Xls Format..
    """,
    'author': 'Caret IT Solutions Pvt. Ltd.',
    'website': 'http://www.caretit.com',
    'version': '1.1',
    'license': 'LGPL-3',
    'depends': ['analytic','accountant', 'account_report_customization'],
    'data': [
        # 'views/views.xml',
        'security/ir.model.access.csv',
        'wizard/balance_sheet_wizard.xml',
        'report/balance_sheet_report.xml',
    ],
    'installable': True,
    'application': False,
   
}
