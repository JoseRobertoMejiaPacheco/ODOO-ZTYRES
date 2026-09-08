# -*- coding: utf-8 -*-
"""
Extiende `account.move` con el texto y el monto de las promociones
aprobadas (`ztyres_promo.notas_credito`) que aplican según las líneas
de la factura. Solo aplica a facturas de cliente (out_invoice); solo
considera lo que aporta esta factura (no el acumulado del cliente en
el periodo).

IMPORTANTE (store=False a propósito): estos campos NO se guardan en
la tabla. Si se marcaran `store=True`, al instalar/actualizar el
módulo Odoo recalcularía el campo para TODAS las facturas existentes
de una sola vez (con miles de facturas históricas, eso es lento y
totalmente innecesario). Al dejarlos sin store, el cálculo se hace
al vuelo únicamente cuando se abre/muestra ese documento puntual —
nunca hay un recálculo masivo sobre el histórico.
"""
from odoo import models, fields, api

class AccountMovePromo(models.Model):
    _inherit = 'account.move'

    promo_ganada_amount = fields.Monetary(
        string='Promoción Ganada (NC)',
        compute='_compute_promo_ganada',
        currency_field='currency_id',
    )
    promo_ganada_text = fields.Html(
        string='Observaciones',
        compute='_compute_promo_ganada',
    )

    @api.depends(
        'invoice_line_ids.product_id', 'invoice_line_ids.price_subtotal',
        'invoice_line_ids.quantity', 'invoice_line_ids.display_type',
        'invoice_line_ids.edi_vat_receptor',
        'partner_id', 'invoice_date', 'move_type',
    )
    def _compute_promo_ganada(self):
        mixin = self.env['ztyres_promo.document_promo_mixin']
        for move in self:
            if move.move_type != 'out_invoice':
                move.promo_ganada_amount = 0.0
                move.promo_ganada_text = False
                continue

            product_lines = move.invoice_line_ids.filtered(
                lambda line: line.display_type == 'product'
            )
            amount, text = mixin.compute_promo_ganada(
                move.partner_id,
                move.invoice_date,
                move.invoice_line_ids,
                quantity_field='quantity',
                edi_vat_receptor=(
                    product_lines[:1].edi_vat_receptor or False
                ),
            )
            move.promo_ganada_amount = amount
            move.promo_ganada_text = text
