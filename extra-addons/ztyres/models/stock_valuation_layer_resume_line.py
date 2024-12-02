from odoo import _, api, fields, models


class Svl(models.TransientModel):
    _name = 'stock.valuation.layer.resume.line'
    _description = 'Valoración de Inventario Resumido'

    product_id = fields.Many2one('product.product', readonly=True, required=True, check_company=True, auto_join=True,string="Producto")
    x_studio_marca = fields.Char(compute='_compute_x_studio_marca', string='Marca',
    store=True
    )
    
    @api.depends('product_id')
    def _compute_x_studio_marca(self):
        for record in self:
            record.x_studio_marca = record.product_id.brand_id.name
            
    
    # x_studio_marca = fields.Char(related='product_id.x_studio_marca', readonly=True)
    product_id_count = fields.Integer()
    quantity = fields.Integer(string='Cantidad')
    value = fields.Float(string="Total")
    svl_resume_history_id = fields.Many2one('stock.valuation.layer.resume.history')



