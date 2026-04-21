from odoo import models, fields,api

class StockQuant(models.Model):
    _inherit = 'stock.quant'
    
    inventory_quantity_auto_apply = fields.Float(
        'Inventoried Quantity', digits='Product Unit of Measure',
        compute='_compute_inventory_quantity_auto_apply',
        inverse='_set_inventory_quantity', groups='stock.group_stock_manager,permisos_ztyres.group_permisos_especiales_facturacion'
    )
    @api.depends('quantity')
    def _compute_inventory_quantity_auto_apply(self):
        for quant in self:
            quant.inventory_quantity_auto_apply = quant.quantity
    
    def _set_inventory_quantity(self):
        """ Inverse method to create stock move when `inventory_quantity` is set
        (`inventory_quantity` is only accessible in inventory mode).
        """
        if not self._is_inventory_mode():
            return
        for quant in self:
            quant.inventory_quantity = quant.inventory_quantity_auto_apply
        self.action_apply_inventory()