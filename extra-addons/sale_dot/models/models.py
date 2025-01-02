from odoo import models,fields,api
from odoo.tools import float_compare
from odoo.exceptions import ValidationError, UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    def action_open_add_product_wizard(self):
        return {
            'name': 'Agregar Productos',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line.add.product.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},  # Pasa el ID de la línea activa al wizard
        }


 
    
class SaleOrderLine(models.Model):
    _inherit = 'product.pricelist.item'
    lot_name = fields.Char(string='DOT')
    lots_ids = fields.Many2many('stock.lot', string='Lotes')
    
    def _get_lots(self,dot_name):
        for record in self:
            # Obtenemos el producto relacionado con el item de la lista de precios
            # product_template = record.product_tmpl_id
            
            # Filtramos los lotes por el nombre, el producto, la ubicación interna y el stock disponible
            lots = self.env['stock.lot'].search([
                ('product_id', '=', self.product_variant_id.id),  # Producto relacionado
                ('name', '=', dot_name),  # Filtramos por el nombre del lote
                ('quant_ids.location_id.usage', '=', 'internal'),  # Ubicación interna
                ('quant_ids.quantity', '>', 0)  # Aseguramos que haya stock disponible
            ])
            
            # Asignamos los lotes encontrados al campo lots_ids
            record.lots_ids = lots.ids
    