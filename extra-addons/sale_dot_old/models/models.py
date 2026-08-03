from odoo import models,fields,api
from odoo.tools import float_compare
from odoo.exceptions import ValidationError, UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    promo_onyx = fields.Boolean(string='Promoción Onyx 500 llantas')
    
    total_deliver_qty = fields.Integer(compute='_compute_get_deliver_qty',store=True)
    
    cubic_volume = fields.Float(compute='_compute_cubic_volume', string='Cubicaje', store=True)
    
    @api.depends('order_line.product_id', 'order_line.product_uom_qty')
    def _compute_cubic_volume(self):
        for order in self:
            total_volume = sum(
                line.product_id.volume * line.product_uom_qty
                for line in order.order_line
                if line.product_id.volume
            )
            order.cubic_volume = total_volume
    
    @api.depends('order_line.product_uom_qty')
    def _compute_get_deliver_qty(self):
        for record in self:
            product_lines = record.order_line.filtered(lambda l: l.product_id.type == 'product')
            record.total_deliver_qty = sum(product_lines.mapped('product_uom_qty'))
    
    @api.onchange('order_line.product_uom_qty')
    def onchange_field(self):
        pass
    
    def action_open_add_product_wizard(self):
        return {
            'name': 'Agregar Productos',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line.add.product.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id,'is_expo':self.is_expo},  # Pasa el ID de la línea activa al wizard
        }

    # def write(self, vals):
    #     return res
        # res = super().write(vals)
        # if self.env.context.get('skip_shipping_price',False):
        #     return res
        # if vals.get('order_line',False) or vals.get('forma_envio',False):
        #     if self.total_deliver_qty <=7:
        #         self._remove_delivery_z()
        #         product_lines = self.order_line.filtered(lambda l: l.product_id.id == 50959)
        #         if product_lines:
        #             product_lines.update({'product_uom_qty': self.total_deliver_qty})
        #         else:
        #             product = self.env['product.product'].browse(50959)
        #             vals_line = {
        #             'product_id': 50959,
        #             'order_id': self.id,
        #             'product_uom_qty': self.total_deliver_qty,
        #             'lots_ids': [],
        #             'dot_range':'',
        #             'price_unit':product.standard_price
        #         }
        #             if self.forma_envio not in ['Paqueteria del cliente','Cliente Recoge','Vendedor Lleva']:
        #                 created_line = self.env['sale.order.line'].create(vals_line)
        #             else:
        #                 self._remove_delivery_z()
        #     if self.total_deliver_qty >7:
        #         self._remove_delivery_z()
        # return res

    forma_envio = fields.Selection(
        selection=[
            ('Se envia', 'Se envia'),
            ('Paqueteria del cliente', 'Paqueteria del cliente'),
            ('Paqueteria interna', 'Paqueteria interna'),
            ('Cliente Recoge', 'Cliente Recoge'),
            ('Vendedor Lleva', 'Vendedor Lleva')
        ],
        string='Forma de Envío'
    )

    
    def _check_forma_envio(self):
        """
        Este método es un simple ejemplo.
        Ajusta la lógica según necesites.
        """
        for record in self:
            if record.forma_envio in ['Cliente Recoge','Vendedor Lleva']:
                continue
            
            if record.total_deliver_qty <= 7 and record.forma_envio not in ['Paqueteria del cliente','Paqueteria interna']:
                raise UserError('La forma de envio no es valida para esa cantidad de llantas')
            elif record.total_deliver_qty >= 8 and record.forma_envio in ['Paqueteria del cliente','Paqueteria interna']:
                raise UserError('La forma de envio no es valida para esa cantidad de llantas')
            elif record.forma_envio in ['Paqueteria del cliente'] and (not record.x_studio_nombre_paqueteria or not record.x_studio_guas):
                    raise UserError('Falta agregar el número de guía')
            

    def _remove_delivery_z(self):
        product_lines = self.order_line.filtered(lambda l: l.product_id.id == 50959)
        if product_lines:
            self.order_line = [(2, line.id, 0) for line in product_lines]
    

    def action_confirm(self):
        for record in self:
            record._check_forma_envio()
        return super(SaleOrder, self).action_confirm()
    
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

    class StockPicking(models.Model):
        _inherit = 'stock.picking'
        
        forma_envio = fields.Selection(
            selection=[
                ('Se envia', 'Se envia'),
                ('Paqueteria del cliente', 'Paqueteria del cliente'),
                ('Paqueteria interna', 'Paqueteria interna'),
                ('Cliente Recoge', 'Cliente Recoge'),
                ('Vendedor Lleva', 'Vendedor Lleva')
            ],
            store=True,
            compute='_compute_forma_envio',
            inverse='_inverse_forma_envio',
            readonly=False,
            string='Forma de Envío'
        )
        
        @api.depends('sale_id.forma_envio')
        def _compute_forma_envio(self):
            for record in self:
                if record.sale_id:
                    record.forma_envio = record.sale_id.forma_envio
                else:
                    record.forma_envio = False
        
        def _inverse_forma_envio(self):
            for record in self:
                if record.sale_id:
                    record.sale_id.forma_envio = record.forma_envio