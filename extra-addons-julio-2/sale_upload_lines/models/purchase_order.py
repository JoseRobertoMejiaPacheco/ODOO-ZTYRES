from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def import_purchase_lines(self):
        # view = self.env.ref('')
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cargar líneas de pedido',
            'res_model': 'purchase.import_order_lines',
            'view_mode': 'form',
            # 'view_id' : view.id,
            'target': 'new',
            'context' : {'order_id':self}
        }
