# -*- coding: utf-8 -*-
"""
Extiende `sale.order` (cotizaciones y órdenes de venta confirmadas)
con el texto y el monto de las promociones aprobadas
(`ztyres_promo.notas_credito`) que aplican según las líneas de la
orden. Solo considera lo que aporta esta orden (no el acumulado del
cliente en el periodo).

IMPORTANTE (store=False a propósito): estos campos NO se guardan en
la tabla. Si se marcaran `store=True`, al instalar/actualizar el
módulo Odoo recalcularía el campo para TODAS las órdenes existentes
de una sola vez (con miles de cotizaciones históricas, eso es lento y
totalmente innecesario). Al dejarlos sin store, el cálculo se hace
al vuelo únicamente cuando se abre/muestra ese documento puntual —
nunca hay un recálculo masivo sobre el histórico.
"""
from odoo import models, fields, api


class SaleOrderPromo(models.Model):
    _inherit = 'sale.order'

    promo_ganada_amount = fields.Monetary(
        string='Promoción Ganada (NC)',
        compute='_compute_promo_ganada',
        currency_field='currency_id',
    )
    promo_ganada_text = fields.Html(
        string='Promoción Ganada',
        compute='_compute_promo_ganada',
    )

    @api.depends(
        'order_line.product_id', 'order_line.price_subtotal',
        'order_line.product_uom_qty', 'order_line.display_type',
        'partner_id', 'date_order',
    )
    def _compute_promo_ganada(self):
        mixin = self.env['ztyres_promo.document_promo_mixin']
        for order in self:
            doc_date = order.date_order.date() if order.date_order else False
            amount, text = mixin.compute_promo_ganada(
                order.partner_id,
                doc_date,
                order.order_line,
                quantity_field='product_uom_qty',
            )
            order.promo_ganada_amount = amount
            order.promo_ganada_text = text
