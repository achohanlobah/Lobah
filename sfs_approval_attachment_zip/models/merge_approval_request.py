from odoo import models, fields


class MergeApprovalAttachments(models.Model):
    _name = "merge.approval.attachments"
    _description = "merge.approval.attachments"

    sequence = fields.Integer()
    approval_request_id = fields.Many2one("approval.request")
    attachment_id = fields.Many2one("ir.attachment",
                                    domain="[('res_id', '=?', approval_request_id), ('res_model', '=', 'approval.request'), ('mimetype', '=', 'application/pdf')]",
                                    required=True)
