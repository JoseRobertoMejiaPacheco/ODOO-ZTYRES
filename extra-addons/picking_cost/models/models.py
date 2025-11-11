# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'
    
    sol_currency_id = fields.Many2one(
        'res.currency',
        compute='_compute_sol_currency_id',
        string='Moneda (Pedido)',
        store=False,
    )
    
    product_price_total_sol = fields.Monetary(
        string='Precio Total (Pedido)',
        currency_field='sol_currency_id',
        compute='_compute_product_price_sol',
        store=False,
    )
    
    # Evitamos depender de campos que pueden no existir (sale_line_id, sale_id)
    @api.depends('move_id', 'company_id.currency_id')
    def _compute_sol_currency_id(self):
        for line in self:
            move = line.move_id
            # 1) Si existe sale_line_id -> order_id.currency_id
            sol = getattr(move, 'sale_line_id', False)
            order = getattr(sol, 'order_id', False) if sol else False
            currency = getattr(order, 'currency_id', False)
            # 2) Fallback: si el picking tiene sale_id -> su moneda
            if not currency:
                picking = getattr(move, 'picking_id', False)
                sale = getattr(picking, 'sale_id', False) if picking else False
                currency = getattr(sale, 'currency_id', False)
            # 3) Último recurso: moneda de la compañía
            line.sol_currency_id = currency or line.company_id.currency_id
    
    @api.depends('qty_done', 'reserved_uom_qty', 'move_id')
    def _compute_product_price_sol(self):
        for line in self:
            move = line.move_id
            sol = getattr(move, 'sale_line_id', False)
            # Tomamos price_unit de la línea de venta si existe
            price_unit = getattr(sol, 'price_unit', 0.0) if sol else 0.0
            sol_qty = getattr(sol, 'product_uom_qty', 0.0) if sol else 0.0
            
            if sol and sol_qty:
                qty = line.qty_done or line.reserved_uom_qty or 0.0
                line.product_price_total_sol = qty * price_unit
            else:
                line.product_price_total_sol = 0.0


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    sol_currency_id = fields.Many2one(
        'res.currency',
        compute='_compute_sol_currency_id',
        string='Moneda (Pedido)',
        store=False,
    )
    
    total_price_sale = fields.Monetary(
        string='Total Pedido (Picking)',
        currency_field='sol_currency_id',
        compute='_compute_total_price_sale',
        store=False,
    )
    
    @api.depends('move_line_ids.product_price_total_sol')
    def _compute_total_price_sale(self):
        for picking in self:
            picking.total_price_sale = sum(
                picking.move_line_ids.mapped('product_price_total_sol')
            )
    
    # Solo dependemos de campos que sí existen siempre
    @api.depends('move_line_ids.sol_currency_id', 'company_id.currency_id')
    def _compute_sol_currency_id(self):
        for picking in self:
            currencies = picking.move_line_ids.mapped('sol_currency_id')
            if currencies and len(set(currencies.ids)) == 1:
                picking.sol_currency_id = currencies[0]
            else:
                picking.sol_currency_id = picking.company_id.currency_id