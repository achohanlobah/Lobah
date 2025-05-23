# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

from odoo import models, fields


class MergeInvoiceAttachments(models.Model):
    _name = "merge.invoice.attachments"
    _description = "merge.invoice.attachments"

    account_move_id = fields.Many2one("account.move")
    sequence = fields.Integer()
    attachment_id = fields.Many2one("ir.attachment", domain="[('res_id', '=?', account_move_id), ('res_model', '=', 'account.move'), ('mimetype', '=', 'application/pdf')]", required=True)
