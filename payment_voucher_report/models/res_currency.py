# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

from odoo import models, fields


class Currency(models.Model):
    """Inherit account.move model"""
    _inherit = "res.currency"

    pv_report_string = fields.Char()
