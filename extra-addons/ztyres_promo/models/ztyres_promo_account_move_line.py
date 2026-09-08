# -*- coding: utf-8 -*-
"""
Extiende `account.move.line` con la promoción ganada correspondiente
a ESA línea puntual de factura (no el agregado de toda la factura, que
ya vive en `account.move.promo_ganada_amount`/`promo_ganada_text`).
Solo aplica a líneas de facturas de cliente (move_type ==
'out_invoice'); para cualquier otra línea (pagos, impuestos, facturas
de proveedor, etc.) queda en 0 / vacío.

Lo que importa aquí es `promo_ganada_text` (Text, texto plano): usa el
mismo `promo_ganada_message` configurado en la promoción, pero con el
monto ganado de ESTA línea. `promo_ganada_amount` existe para el
cálculo interno, pero se mantiene siempre oculto en la vista (ver
ztyres_promo_sale_account_views.xml) — lo que se muestra es el texto.

Mismas simplificaciones que el cálculo a nivel de documento (ver
ztyres_promo_notas_credito_eval.py).

store=False a propósito: mismo motivo que en sale.order/account.move
(ver esos archivos) — evitar recalcular sobre miles de líneas
históricas al instalar el módulo.
"""
from odoo import models, fields, api

class AccountMoveLinePromo(models.Model):
    _inherit = 'account.move.line'

    promo_ganada_amount = fields.Monetary(
        string='Promoción Ganada (NC)',
        compute='_compute_promo_ganada',
        currency_field='currency_id',
    )
    promo_ganada_text = fields.Text(
        string='Observaciones',
        compute='_compute_promo_ganada',
    )

    @api.depends(
        'move_id.partner_id', 'move_id.invoice_date', 'move_id.move_type',
        'move_id.invoice_line_ids.product_id', 'move_id.invoice_line_ids.price_subtotal',
        'move_id.invoice_line_ids.quantity', 'move_id.invoice_line_ids.display_type',
        'move_id.invoice_line_ids.edi_vat_receptor',
    )
    def _compute_promo_ganada(self):
        mixin = self.env['ztyres_promo.document_promo_mixin']
        # Agrupar por factura para evaluar cada promoción una sola vez
        # por factura, no una vez por cada línea.
        details_by_move = {}
        for move in self.mapped('move_id'):
            if move.move_type != 'out_invoice':
                details_by_move[move.id] = {}
                continue
            product_lines = move.invoice_line_ids.filtered(
                lambda line: line.display_type == 'product'
            )
            details_by_move[move.id] = mixin.compute_promo_ganada_line_details(
                move.partner_id,
                move.invoice_date,
                move.invoice_line_ids,
                quantity_field='quantity',
                edi_vat_receptor=(
                    product_lines[:1].edi_vat_receptor or False
                ),
            )

        for line in self:
            details = details_by_move.get(line.move_id.id, {})
            amount, text = details.get(line.id, (0.0, False))
            line.promo_ganada_amount = amount
            line.promo_ganada_text = text
