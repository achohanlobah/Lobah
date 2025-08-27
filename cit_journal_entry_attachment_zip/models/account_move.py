# -*- coding: utf-8 -*-
from odoo import models, fields, api
import base64
import zipfile
from io import BytesIO
import re
import logging
from PyPDF2 import PdfMerger, PdfReader

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def sanitize_filename(self, name):
        """Sanitize filenames by replacing special characters with underscores."""
        return re.sub(r'[\\/*?:"<>|]', "_", name)

    def action_attachments_download(self):
        """Download all attachments of selected Journal Entries as a single ZIP file."""
        zip_buffer = BytesIO()
        has_attachments = False

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for move in self:
                attachments = self.env['ir.attachment'].search([
                    ('res_model', '=', 'account.move'),
                    ('res_id', '=', move.id)
                ])
                if attachments:
                    has_attachments = True
                    sub_zip_buffer = BytesIO()
                    with zipfile.ZipFile(sub_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as sub_zip:
                        for attachment in attachments:
                            sub_zip.writestr(attachment.name, base64.b64decode(attachment.datas))
                    sub_zip_buffer.seek(0)
                    filename = move.name if move.name and move.name != '/' else f'journal_entry_{move.id}'
                    zip_file.writestr(self.sanitize_filename(filename) + '.zip', sub_zip_buffer.read())

        zip_buffer.seek(0)

        if not has_attachments:
            return self._show_warning()

        zip_data = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')
        attachment = self.env['ir.attachment'].create({
            'name': 'Journal_Entries_Attachments.zip',
            'datas': zip_data,
            'mimetype': 'application/zip',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_pdf_attachments_download(self):
        """Download merged PDF of all PDF attachments for selected Journal Entries."""
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', 'in', self.ids)
        ])

        pdf_attachments = attachments.filtered(lambda att: att.mimetype and att.mimetype.startswith('application/pdf'))
        if not pdf_attachments:
            return self._show_warning()

        filename = 'Merged_Attachments'
        if len(self) == 1:
            filename = self.name if self.name and self.name != '/' else f'journal_entry_{self.id}'

        merged_attachment = self.merge_attachment_pdf(pdf_attachments, name=filename)
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{merged_attachment.id}?download=true',
            'target': 'self',
        }

    def merge_attachment_pdf(self, attachments, name):
        """Merge multiple PDF attachments into a single PDF."""
        merger = PdfMerger()
        has_pages = False

        for attachment in attachments:
            try:
                pdf_data = base64.b64decode(attachment.datas)
                reader = PdfReader(BytesIO(pdf_data))
                if len(reader.pages) > 0:
                    merger.append(BytesIO(pdf_data))
                    has_pages = True
                    _logger.info("Appended PDF: %s", attachment.name)
                else:
                    _logger.warning("PDF has no pages: %s", attachment.name)
            except Exception as e:
                _logger.warning("Could not append PDF '%s': %s", attachment.name, str(e))

        if not has_pages:
            return self._show_warning()

        output = BytesIO()
        merger.write(output)
        merger.close()
        output.seek(0)

        merged_pdf = output.read()
        attachment = self.env['ir.attachment'].create({
            'type': 'binary',
            'name': self.sanitize_filename(name) + '.pdf',
            'datas': base64.b64encode(merged_pdf),
            'mimetype': 'application/pdf',
        })
        return attachment

    def _show_warning(self):
        """Display warning if no valid attachments are found."""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'No Attachments Found',
                'message': 'There are no available attachments to download for the selected Journal Entries.',
                'type': 'warning',
                'sticky': False,
            }
        }
