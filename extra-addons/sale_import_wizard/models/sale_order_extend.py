# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    invoice_policy_override = fields.Selection([
        ('order',    'Cantidad Pedida'),
        ('delivery', 'Cantidad Entregada'),
        ('none',     'Sin cambio (usar politica del producto)'),
    ], string='Politica de Facturacion (pedido)',
        default='none',
        help='Sobreescribe la politica de facturacion para todas las lineas de este pedido.',
        tracking=True,
    )


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    invoice_policy_override = fields.Selection([
        ('order',    'Cantidad Pedida'),
        ('delivery', 'Cantidad Entregada'),
        ('none',     'Sin cambio (usar politica del producto)'),
    ], string='Politica de Facturacion (linea)',
        default='none',
    )

    def _get_invoice_policy(self):
        self.ensure_one()
        if self.invoice_policy_override and self.invoice_policy_override != 'none':
            return self.invoice_policy_override
        if self.order_id.invoice_policy_override and self.order_id.invoice_policy_override != 'none':
            return self.order_id.invoice_policy_override
        return self.product_id.invoice_policy

    @api.depends(
        'qty_invoiced', 'qty_delivered', 'product_uom_qty', 'order_id.state',
        'invoice_policy_override', 'order_id.invoice_policy_override',
    )
    def _compute_qty_to_invoice(self):
        for line in self:
            if line.state in ('draft', 'sent'):
                line.qty_to_invoice = 0.0
                continue
            policy = line._get_invoice_policy()
            if policy == 'order':
                line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
            else:
                line.qty_to_invoice = line.qty_delivered - line.qty_invoiced
