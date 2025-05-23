# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Caret IT Solutions Pvt. Ltd. (Website: www.caretit.com).           #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################

from odoo import models, fields, api
import base64
import zipfile
from io import BytesIO
import re
import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def sanitize_filename(self, name):
        """This method replace any symbol to underscore for file name"""
        return re.sub(r'[\\/*?:"<>|]', "_", name)

    def action_attachments_download(self):
        """This method generate the zip file of attachment and combine in 1 zip and download"""
        zip_buffer = BytesIO()
        if not self.attachment_ids:
            return self._show_warning()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for move in self.filtered(lambda a: a.attachment_ids != False):
                attachments = self.env['ir.attachment'].search([
                    ('res_model', '=', 'account.move'),
                    ('res_id', '=', move.id)
                ])
                if attachments:
                    sub_zip_buffer = BytesIO()
                    with zipfile.ZipFile(sub_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as sub_zip_file:
                        for attachment in attachments:
                            sub_zip_file.writestr(attachment.name, base64.b64decode(attachment.datas))
                    sub_zip_buffer.seek(0)
                    file_name = 'attachments_%s'%move.id if move.name == '/' else move.name
                    zip_file.writestr(self.sanitize_filename(file_name)+'.zip', sub_zip_buffer.read())
                zip_buffer.seek(0)
        _logger.info("Zip Create and Combine success!!!!")

        if zip_buffer.getbuffer().nbytes > 0:
            zip_data = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')
            attachment = self.env['ir.attachment'].create({
                'name': 'Journal Entries Attachments.zip',
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