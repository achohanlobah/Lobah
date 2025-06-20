# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

from odoo import models, fields


class AccountMoveLine(models.Model):
    """Inherit account.move model"""
    _inherit = "account.move.line"

    show_in_pv_report = fields.Boolean()
