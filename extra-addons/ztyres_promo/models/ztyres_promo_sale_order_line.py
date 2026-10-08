# -*- coding: utf-8 -*-
"""
Extiende `sale.order.line` con la promoción ganada correspondiente a
ESA línea puntual (no el agregado de todo el pedido, que ya vive en
`sale.order.promo_ganada_amount`/`promo_ganada_text`).

Lo que importa aquí es `promo_ganada_text` (Text, texto plano): usa el
mismo `promo_ganada_message` configurado en la promoción, pero con el
monto ganado de ESTA línea. `promo_ganada_amount` existe para el
cálculo interno, pero se mantiene siempre oculto en la vista (ver
ztyres_promo_sale_account_views.xml) — lo que se muestra es el texto.

Mismas simplificaciones que el cálculo a nivel de documento (ver
ztyres_promo_notas_credito_eval.py): no considera `apply_on_groups`/
`apply_volume`, ni el tope de 200 unidades en promociones de cupones.

store=False a propósito: mismo motivo que en sale.order/account.move
(ver esos archivos) — evitar recalcular sobre miles de líneas
históricas al instalar el módulo.
"""
from odoo import models, fields, api


class SaleOrderLinePromo(models.Model):
    _inherit = 'sale.order.line'

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
        'order_id.partner_id', 'order_id.date_order',
        'order_id.order_line.product_id', 'order_id.order_line.price_subtotal',
        'order_id.order_line.product_uom_qty', 'order_id.order_line.display_type',
    )
    def _compute_promo_ganada(self):
        mixin = self.env['ztyres_promo.document_promo_mixin']
        # Agrupar por orden para evaluar cada promoción una sola vez
        # por pedido, no una vez por cada línea.
        details_by_order = {}
        for order in self.mapped('order_id'):
            doc_date = order.date_order.date() if order.date_order else False
            details_by_order[order.id] = mixin.compute_promo_ganada_line_details(
                order.partner_id,
                doc_date,
                order.order_line,
                quantity_field='product_uom_qty',
            )

        for line in self:
            details = details_by_order.get(line.order_id.id, {})
            amount, text = details.get(line.id, (0.0, False))
            line.promo_ganada_amount = amount
            line.promo_ganada_text = text
