# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.tools import pdf


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        """
        This code is added for add ribbon on top left corner when voucher report download.
        """
        collected_streams = super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)
        invoices = self.env['account.move'].browse(res_ids)
        if self._get_report(report_ref).report_name == 'payment_voucher_report.report_payment_voucher':
            for invoice in invoices:
                stream = pdf.add_banner(collected_streams[invoice.id].get('stream'), invoice.pv_sequence or '', logo=True)
                collected_streams[invoice.id].update({
                    'stream': stream,
                })
        return collected_streams