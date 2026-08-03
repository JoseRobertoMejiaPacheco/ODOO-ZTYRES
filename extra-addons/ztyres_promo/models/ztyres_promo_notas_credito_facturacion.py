# -*- coding: utf-8 -*-
"""Creación de notas de crédito y consulta de su estado ante el SAT."""

from odoo import _, fields, models
from odoo.exceptions import UserError

# Dependencias de negocio existentes. Se mantienen centralizadas para que sean
# fáciles de localizar hasta que se migren a campos de configuración.
NC_JOURNAL_ID = 148
NC_PRODUCT_ID = 50785
CONDONATION_PAYMENT_METHOD_ID = 11


class ZtyresPromoCreditNoteInvoicing(models.Model):
    _inherit = 'ztyres_promo.notas_credito'

    def _get_valid_invoices(self, invoice_type):
        self.ensure_one()
        if invoice_type == 'out_invoice':
            return self.detailed_line_ids.filtered(
                lambda line: (
                    line.state in ('valid', 'partial')
                    and line.move_type == 'out_invoice'
                )
            ).mapped('move_id')
        if invoice_type == 'out_refund':
            return self.line_ids.mapped('nc_credit_id')
        return self.env['account.move']

    def check_sat_status(self):
        self.ensure_one()
        for line in self.line_ids.filtered('nc_credit_id'):
            line.nc_credit_id.l10n_mx_edi_update_sat_status()
            line.sat_estatus = line.nc_credit_id.l10n_mx_edi_sat_status
        return True

    def _create_nc(self):
        self.ensure_one()
        self._check_partner_vat_before_confirm()
        result_lines = self.line_ids.filtered(
            lambda line: line.total_nc_untaxed > 0 and not line.nc_credit_id
        )
        for line in result_lines:
            credit_note = self.env['account.move'].sudo().create(
                self._prepare_credit_note_vals(line)
            )
            credit_note.action_post()
            documents = credit_note.edi_document_ids.filtered(
                lambda document: (
                    document.state in ('to_send', 'to_cancel')
                    and document.blocking_level != 'error'
                )
            )
            if documents:
                documents._process_documents_web_services(with_commit=True)
            line.nc_credit_id = credit_note

    def _check_partner_vat_before_confirm(self):
        """Protección de servidor; no depende solamente de la alerta UI."""
        missing_documents = self.detailed_line_ids.filtered(
            'missing_partner_vat'
        ).mapped('move_id')
        if not missing_documents:
            return

        message = self.missing_partner_vat_warning or _(
            'Los siguientes documentos tienen líneas sin RFC receptor: %s. '
            'Corrija los datos y vuelva a calcular.'
        ) % ', '.join(missing_documents.mapped('display_name'))
        raise UserError(_(
            'No se puede confirmar la promoción.\n\n%s'
        ) % message)

    def _prepare_credit_note_vals(self, result_line):
        invoice_uuids = self._get_result_invoice_uuids(result_line)
        values = {
            'move_type': 'out_refund',
            'x_studio_tipo': 'Bonificación',
            # RFC receptor exacto del cubo partner + RFC. Proviene del XML
            # de las facturas origen; no se infiere ni se sustituye.
            'edi_vat_receptor': result_line.rfc,
            'invoice_date': fields.Date.context_today(self),
            'journal_id': NC_JOURNAL_ID,
            'l10n_mx_edi_payment_method_id': CONDONATION_PAYMENT_METHOD_ID,
            'l10n_mx_edi_usage': 'G02',
            'currency_id': self.env.company.currency_id.id,
            'partner_id': result_line.partner_id.id,
            'partner_shipping_id': result_line.partner_id.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': NC_PRODUCT_ID,
                'quantity': 1,
                'name': self.nombre,
                'price_unit': round(result_line.total_nc_untaxed, 2),
            })],
        }
        if invoice_uuids:
            values['l10n_mx_edi_origin'] = '01|%s' % ','.join(invoice_uuids)
        return values

    def _get_result_invoice_uuids(self, result_line):
        detail_lines = self.detailed_line_ids.filtered(
            lambda line: (
                line.partner_id == result_line.partner_id
                and line.rfc == result_line.rfc
                # 'partial' = línea que sí generó NC pero topada por el
                # límite de cupones; su CFDI también debe ir en el origen.
                and line.state in ('valid', 'partial')
            )
        )
        return [
            uuid
            for uuid in detail_lines.mapped('move_id.l10n_mx_edi_cfdi_uuid')
            if uuid
        ]

    def action_confirmar_nc(self):
        self.ensure_one()
        self._create_nc()
        self.status = 'done'
        return True
