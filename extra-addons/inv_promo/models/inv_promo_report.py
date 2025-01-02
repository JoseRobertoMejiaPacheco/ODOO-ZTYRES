# -- coding: utf-8 --

from odoo import models, fields, api

class InvPromo(models.TransientModel):
    _name = 'inv_promo.report'
    _description = 'inv_promo.inv_promo'
    
    product_id = fields.Many2one('product.template', string='Producto')
    default_code = fields.Char(string='Código')
    tire_measure_id = fields.Many2one('ztyres_products.tire_measure', string='Medida')
    layer_id = fields.Many2one('ztyres_products.layer', string='Capas')
    speed_id = fields.Many2one('ztyres_products.speed', string='Indice de Velocidad')
    index_of_load_id = fields.Many2one('ztyres_products.index_of_load', string='Indice de Carga')
    model_id = fields.Many2one('ztyres_products.model', string='Modelo')
    brand_id = fields.Many2one('ztyres_products.brand', string='Marca')
    tier_id = fields.Many2one('ztyres_products.tier', string='Tier')
    total_quantity = fields.Float(string='Cantidad')
    available = fields.Float(string='Cantidad Disponible')
    transit = fields.Float(string='Trans')
    fecha = fields.Date(string='Fecha')
    backorder = fields.Integer(string='Backorder')
    volumen = fields.Float(compute='_compute_volumen', digits=(16, 2), string='Precio Volumen')
    promocion = fields.Float(compute='_compute_promocion', digits=(16, 2), string='Precio promocion')
    promo_dot = fields.Float(digits=(16, 2), string='Precio Promo Dot')
    transito_str = fields.Integer(compute='_compute_transito_str', string='Transito')
    fecha_aprox = fields.Date(compute='_compute_transito_str', string='Fecha_aprox')
    inventario_str = fields.Char(compute='_compute_inventario_str', string='Inventario')
    backorder_str = fields.Integer(compute='_compute_backorder_str', string='Bo')
    lot_name = fields.Char(string='lot_name')
    
    def _get_price(self, product_tmpl_id, outlet_pricelist_id):
        pricelist_item = self.env['product.pricelist.item']
        domain = [
            ('product_tmpl_id', 'in', [product_tmpl_id]),
            ('pricelist_id', 'in', [outlet_pricelist_id])
        ]  
        item = pricelist_item.search(domain, order="fixed_price asc", limit=1)      
        return item.fixed_price 
    

    
    @api.depends('product_id')
    def _compute_volumen(self):
        for record in self:
            record.volumen = 0
            if not record.promo_dot:
                record.volumen = record._get_price(record.product_id.id, 1)
    
    @api.depends('product_id')
    def _compute_promocion(self):
        for record in self:
            record.promocion = 0
            if not record.promo_dot:
                record.promocion = record._get_price(record.product_id.id, 113)
            


    @api.depends('available')
    def _compute_inventario_str(self):
        for record in self:
            if record.available >= 50 and record.available > 0:
                record.inventario_str = '+50'
            elif record.available < 50 and record.available > 0:
                record.inventario_str = "=%s"%(record.available)
            else:
                record.inventario_str = '0'
                

    def _compute_transito_str(self):
        for record in self:
            if record.transit > 0:
                record.transito_str = record.transit
                record.fecha_aprox = record.fecha
            else:
                record.transito_str = None
                record.fecha_aprox = None

    def _compute_backorder_str(self):
        for record in self:
            if record.backorder > 0:
                record.backorder_str = record.backorder
            else:
                record.backorder_str = None