# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

{
    'name': 'Account Trial Balance',
    'version': '1.2',
    'summary': 'Account Trial Balance',
    'category': '',
    'description': """
        Adds Trial Balance report in PDF and Xls Format
    """,
    'author': 'Caret IT Solutions Pvt. Ltd.',
    'website': 'http://www.caretit.com',
    'depends': ['account_report_customization'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/account_trial_balance_wizard.xml',
        'report/trial_balance_report.xml',
    ],
    'qweb': [],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
