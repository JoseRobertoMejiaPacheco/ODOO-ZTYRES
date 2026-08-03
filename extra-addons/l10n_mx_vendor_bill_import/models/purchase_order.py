# -*- coding: utf-8 -*-
from odoo import models, fields, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # ── Contador de XMLs importados (informativo) ─────────────────────────────
    xml_import_count = fields.Integer(
        string='XMLs Importados',
        compute='_compute_xml_import_count',
    )

    def _compute_xml_import_count(self):
        for rec in self:
            rec.xml_import_count = self.env['account.move'].search_count([
                ('narration', 'ilike', 'Pedidos relacionados:'),
                ('invoice_line_ids.purchase_line_id.order_id', '=', rec.id),
                ('move_type', '=', 'in_invoice'),
            ])

    # ── Acción del botón: abre el wizard con contexto del PO ──────────────────
    def action_import_xml_cfdi(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Importar Factura XML CFDI 4.0'),
            'res_model': 'import.xml.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                # El wizard usa estos valores para precargar el proveedor y el PO
                'default_origin_po_id': self.id,
                'default_supplier_rfc': self.partner_id.vat or '',
                'default_supplier_name': self.partner_id.name or '',
            },
        }
