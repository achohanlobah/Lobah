from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move.line'

    def action_attachments_download(self):
        """Download zip from journal entries"""
        move_ids = self.mapped('move_id')
        attachment_zip = move_ids.action_attachments_download()
        return attachment_zip

    def action_pdf_attachments_download(self):
        """Download pdf from journal entries"""
        move_ids = self.mapped('move_id')
        attachment_pdf = move_ids.action_pdf_attachments_download()
        return attachment_pdf
