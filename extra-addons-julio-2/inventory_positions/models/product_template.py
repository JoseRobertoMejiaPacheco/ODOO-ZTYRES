from odoo import _, api, fields, models
from odoo.osv import expression

class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    estado_conteo_dot = fields.Selection(
        string='Estado de Conteo',
        selection=[('draft', 'Sin Contar'), ('done', 'Contado')],default='draft'
    )
    
    def cambiar_estado_conteo(self):
        for record in self:
            if record.estado_conteo_dot == 'done':
                record.estado_conteo_dot = 'draft'
            elif record.estado_conteo_dot == 'draft':
                record.estado_conteo_dot = 'done'                


