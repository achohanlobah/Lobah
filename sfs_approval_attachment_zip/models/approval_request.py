# -*- coding: utf-8 -*-
import base64
import zipfile
from io import BytesIO
import re
import logging
from PyPDF2 import PdfMerger, PdfReader

from odoo.exceptions import UserError
from odoo.tools import pdf
from odoo import models, fields

_logger = logging.getLogger(__name__)


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    merge_approval_attachment_ids = fields.One2many('merge.approval.attachments', 'approval_request_id',
                                                   string="Merge Attachments", copy=False)

    def sanitize_filename(self, name):
        return re.sub(r'[\\/*?:"<>|]', "_", str(name) if name else "unknown")

    def action_attachments_download(self):
        """This method generate the zip file of attachment and combine in 1 zip and download"""
        zip_buffer = BytesIO()
        if not self.attachment_ids:
            return self._show_warning()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for approval_id in self.filtered(lambda a: a.attachment_ids != False):
                attachments = self.env['ir.attachment'].search([
                    ('res_model', '=', 'approval.request'),
                    ('res_id', '=', approval_id.id)
                ])
                if attachments:
                    sub_zip_buffer = BytesIO()
                    with zipfile.ZipFile(sub_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as sub_zip_file:
                        for attachment in attachments:
                            sub_zip_file.writestr(attachment.name, base64.b64decode(attachment.datas))
                    sub_zip_buffer.seek(0)
                    file_name = 'attachments_%s' % approval_id.id if approval_id.name == '/' else approval_id.name
                    zip_file.writestr(self.sanitize_filename(file_name) + '.zip', sub_zip_buffer.read())
                zip_buffer.seek(0)
        _logger.info("Zip Create and Combine success!!!!")

        if zip_buffer.getbuffer().nbytes > 0:
            zip_data = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')
            attachment = self.env['ir.attachment'].create({
                'name': 'Approval Attachments.zip',
                'datas': zip_data,
                'mimetype': 'application/zip',
            })
            _logger.info("Attachment Created for Zip!!!!")
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }
        else:
            return self._show_warning()

    def _show_warning(self):
        """This method gives warning when no attachment are found"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'No Attachments',
                'message': 'No attachments found for the Journal Entries.',
                'type': 'warning',
                'sticky': False,
            }
        }

    def action_pdf_attachments_download(self):
        """Download the PDF for Particular approval from Server Action"""
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'approval.request'),
            ('res_id', 'in', self.ids)
        ], order='id asc')
        if not attachments:
            return self.no_attachment_erro()

        file_name = 'Attachments'
        if len(self.ids) == 1:
            file_name = 'Attachments' if self.name == '/' else self.name

        attachment = self.merge_attachment_pdf(attachments, name=file_name, move_name='Attachments')

        # If merge_attachment_pdf returned a dict (warning), return it directly
        if isinstance(attachment, dict):
            return attachment

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def no_attachment_erro(self):
        """Error if no any Attachment Found in Journal Entries"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'No PDF',
                'message': 'No PDF found for the selected Journal Entries.',
                'type': 'warning',
                'sticky': False,
            }
        }

    def merge_attachment_pdf(self, attachment_ids, name, move_name):
        """Create Merge PDF for the Attachment"""
        data = []
        for attachment in attachment_ids:
            if attachment.mimetype == 'application/pdf':
                if not attachment.datas:
                    _logger.warning("Skipping empty attachment %s (ID %s)", attachment.name, attachment.id)
                    continue
                try:
                    stream = pdf.to_pdf_stream(attachment)
                    if not stream or stream.getbuffer().nbytes == 0:
                        _logger.warning("Skipping invalid PDF stream for %s (ID %s)", attachment.name, attachment.id)
                        continue
                    stream = pdf.add_banner(stream, move_name, logo=True)
                    pdf_content = stream.getvalue()
                    if pdf_content:
                        data.append(pdf_content)
                except Exception as e:
                    _logger.warning("Skipping corrupted PDF attachment %s (ID %s): %s", attachment.name, attachment.id,
                                    e)
                    continue

        if not data:
            return self.no_attachment_erro()

        pdf_content = pdf.merge_pdf(data)
        attachment = self.env['ir.attachment'].create({
            'type': 'binary',
            'name': name + '.pdf',
            'datas': base64.encodebytes(pdf_content),
        })
        return attachment

    def merge_approval_attachment(self):
        """Merge PDFs from approval attachments into a single file and save as attachment."""
        if not self.merge_approval_attachment_ids:
            raise UserError('Please add attachments to merge.')

        merger = PdfMerger()
        attachments_sorted = self.merge_approval_attachment_ids.sorted('sequence')

        for attachment in attachments_sorted:
            attachment_id = attachment.attachment_id
            try:
                if not attachment_id or not attachment_id.datas:
                    _logger.warning("Empty or missing attachment: %s",
                                    attachment_id.name if attachment_id else 'unknown')
                    continue

                pdf_data = base64.b64decode(attachment_id.datas)
                reader = PdfReader(BytesIO(pdf_data))

                if len(reader.pages) > 0:
                    merger.append(BytesIO(pdf_data))
                    _logger.info("Appended PDF attachment: %s", attachment_id.name)
                else:
                    _logger.warning("Attachment has no pages: %s", attachment_id.name)

            except Exception as e:
                _logger.warning("Failed to add attachment '%s': %s", attachment_id.name if attachment_id else 'unknown',
                                e)

        output = BytesIO()
        merger.write(output)
        merger.close()
        output.seek(0)

        merged_pdf = output.read()
        _logger.info("Merged PDF size: %s bytes", len(merged_pdf))

        self.env['ir.attachment'].create({
            'name': f'Merged-Attachments.pdf',
            'type': 'binary',
            'datas': base64.b64encode(merged_pdf),
            'res_model': 'approval.request',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })
        _logger.info("Saved merged PDF as attachment for approval.request: %s", self.name)

        return {
            'effect': {
                'type': 'rainbow_man',
                'message': "Merged attachment created successfully",
            },
        }
