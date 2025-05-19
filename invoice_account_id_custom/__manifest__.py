# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

{
    'name': 'Invoice Account ID Customization',
    'summary': 'Invoice Account Customization',
    'description': """
        This module selects Account ID Based on Set value in Income Account field on 
        Partner """,
    'version': '1.0',
    'category': 'account',
    'author': 'Caret IT Solutions Pvt. Ltd.',
    'website': 'http://www.caretit.com',
    'license': 'LGPL-3',
    'depends': ['account','contacts'],
    'data': [
        'views/res_partner_views.xml',
    ],
}
