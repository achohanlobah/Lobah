# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

{
    'name': 'Profit And Loss Custom Report',
    'version': '1.2',
    'license': 'LGPL-3',
    'summary': 'Profit And Loss',
    'category': ' ',
    'description': """Adds Profit And Loss report in PDF and Xls Format
    """,
    'author': 'Caret IT Solutions Pvt. Ltd.',
    'website': 'http://www.caretit.com',
    'depends': ['base', 'account', 'analytic', 'accountant', 'account_report_customization'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/profit_and_loss_custom_wizard.xml',
        'report/profit_and_loss_report.xml',
    ],
    'qweb': [],
    'installable': True,
    'application': False,
}
