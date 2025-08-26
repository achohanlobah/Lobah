import base64
from io import BytesIO
from PyPDF2 import PdfMerger, PdfReader
import logging

from odoo import models

_logger = logging.getLogger(__name__)

class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        pdf_content, _ = super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
        #Inject pdf attachments into approval request report
        if report_ref == 'approvals.action_report_approval_request':
            _logger.info("Merging report %s with attachments...", report_ref)
            merger = PdfMerger()
            merger.append(BytesIO(pdf_content))

            for res_id in res_ids:
                attachments = self.env['ir.attachment'].search([
                    ('res_model', '=', 'approval.request'),
                    ('res_id', '=', res_id),
                    ('mimetype', '=', 'application/pdf'),
                ])
                _logger.info("Found attachments: %s", attachments)

                for att in attachments:
                    try:
                        pdf_data = base64.b64decode(att.datas)
                        reader = PdfReader(BytesIO(pdf_data))
                        if len(reader.pages) > 0:
                            merger.append(BytesIO(pdf_data))
                            _logger.info("Appended PDF attachment: %s", att.name)
                        else:
                            _logger.warning("Attachment has no pages: %s", att.name)
                    except Exception as e:
                        _logger.warning("Failed to add attachment '%s': %s", att.name, e)

            output = BytesIO()
            merger.write(output)
            merger.close()
            output.seek(0)

            merged_pdf = output.read()
            _logger.info("Merged PDF size: %s bytes", len(merged_pdf))

            return merged_pdf, 'pdf'

        return pdf_content, _
