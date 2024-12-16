from odoo import models, fields, api
from odoo.exceptions import ValidationError
class SaleOrderLineAddProductWizard(models.TransientModel):
    _name = 'sale.order.line.add.product.wizard'
    _description = 'Wizard para agregar productos a sale.order.line'
    #Pasar por contexto
    product_id = fields.Many2one('product.product', string='Producto')
    
    # Relación One2many con las líneas del wizard
    lines = fields.One2many('sale.order.line.add.product.wizard.line', 'wizard_id', string='Líneas de productos')

    total_qty = fields.Float(string='Total De llantas', compute='_compute_total', readonly=True)
    
    
    @api.depends('lines.qty')
    def _compute_total(self):
        self.total_qty = sum(self.lines.mapped('qty'))
    
    def get_lots_and_quantities(self, product):
        grouped_lot_info = []
        
        # Obtener todas las cantidades relacionadas con el producto en ubicaciones 'internal' (stock)
        stock_quants = self.env['stock.quant'].search([
            ('product_id', '=', product.id),
            ('quantity', '>', 0),  # Solo los que tienen cantidad disponible
            ('location_id.usage', '=', 'internal')
        ])
        
        # Buscar los items de la lista de precios (pricelist_item)
        search_domain = [
            ('product_tmpl_id', 'in', product.product_tmpl_id.ids),  # Usar .ids para obtener una lista de ids
            ('pricelist_id', '=', 122)  # Asegúrate de que el ID de la lista de precios esté correctamente asignado
        ]
        
        pricelist_item = self.env['product.pricelist.item'].search(search_domain)
        lot_info = {}
        if pricelist_item:
            # Si hay elementos en la lista de precios, agrupar por 'lot_name'
            

            for quant in stock_quants:
                lot_name = quant.lot_id.name if quant.lot_id else 'Sin lote'

                # Si el lote ya está en el diccionario, actualizamos la cantidad y la relación m2m
                if lot_name in lot_info:
                    lot_info[lot_name]['qty_available'] += (quant.quantity-quant.reserved_quantity)
                    if quant.lot_id:
                        current_ids = lot_info[lot_name]['lots_ids'][0][2]  # Obtener los ids existentes
                        if quant.lot_id.id not in current_ids:  # Evitar duplicados
                            current_ids.append(quant.lot_id.id)
                        lot_info[lot_name]['lots_ids'] = [(6, 0, current_ids)]
                else:
                    if (quant.quantity-quant.reserved_quantity)>0:
                        # Si no está en el diccionario, agregamos una nueva entrada
                        lot_info[lot_name] = {
                            'lots_ids': [(6, 0, [quant.lot_id.id])] if quant.lot_id else [(6, 0, [])],  # Inicializamos la relación m2m
                            'single_dot': lot_name,
                            'product_id': product.id,
                            'qty_available':(quant.quantity-quant.reserved_quantity),
                            'qty': 0,  # Se podría ajustar según la lógica de negocio
                            'origin_list': '',
                            'price': 0,  # Se puede agregar el precio si es necesario
                            'discount_price': 0,  # Lo mismo con los descuentos
                            'subtotal': 0  # Lo mismo con el subtotal
                        }

            # Convertir el diccionario a una lista de tuplas para ser usado en la vista o en otro proceso
            grouped_lot_info = [(0, 0, lot_data) for lot_data in lot_info.values()]

        else:
            # Si hay elementos en la lista de precios, agrupar por 'lot_name'

            for quant in stock_quants:
                lot_name = product.dot_range if product.dot_range else 'Sin lote'

                # Si el lote ya está en el diccionario, actualizamos la cantidad y la relación m2m
                if lot_name in lot_info:
                    lot_info[lot_name]['qty_available'] += (quant.quantity-quant.reserved_quantity)
                else:
                    # Si no está en el diccionario, agregamos una nueva entrada
                    lot_info[lot_name] = {
                        'lots_ids': [],  # Inicializamos la relación m2m
                        'single_dot': lot_name,
                        'product_id': product.id,
                        'qty_available': (quant.quantity-quant.reserved_quantity),
                        'qty': 0,  # Se podría ajustar según la lógica de negocio
                        'origin_list': '',
                        'price': 0,  # Se puede agregar el precio si es necesario
                        'discount_price': 0,  # Lo mismo con los descuentos
                        'subtotal': 0  # Lo mismo con el subtotal
                    }

            # Convertir el diccionario a una lista de tuplas para ser usado en la vista o en otro proceso
            grouped_lot_info = [(0, 0, lot_data) for lot_data in lot_info.values()]
        
        return grouped_lot_info
        #10770003
    
    
    
    @api.onchange('product_id')
    def onchange_field(self):
        self.lines = [(5, 0, 0)]
        self.lines = self.get_lots_and_quantities(self.product_id)
    
    def action_cancel(self):
        # Acción de cancelar, usualmente para deshacer cambios
        # Se puede hacer algo como restablecer valores, o cerrar el formulario sin guardar
        return {'type': 'ir.actions.act_window_close'}        
    
    #Validar la cantidad cuando se escribe una línea para evitar que pongan llantas demás.
    
    def add_products_to_order_line(self):
        # Obtener el contexto con la línea de pedido de venta
        order_line_id = self.env.context.get('active_id')
        if not order_line_id:
            return
        
        # Crear las líneas de pedido de venta para los productos seleccionados
        for line in self.lines:
            product = self.product_id
            if product and line.qty>0:
                # Creación de la línea de pedido
                created_line = self.env['sale.order.line'].create({
                    'product_id': product.id,
                    'order_id': order_line_id,
                    'product_uom_qty': line.qty,
                    'lots_ids': [(6, 0, line.lots_ids.ids)],
                    'single_dot': line.single_dot,
                    'dot_range':''
                })
                created_line._compute_price_unit()
        self.env['sale.order'].browse(order_line_id).quotation_action_confirm()

class SaleOrderLineAddProductWizardLine(models.TransientModel):
    _name = 'sale.order.line.add.product.wizard.line'

    # Relación con el wizard
    wizard_id = fields.Many2one('sale.order.line.add.product.wizard', string='Wizard')
    
    product_id = fields.Many2one('product.product', string='Producto')
    qty_available = fields.Float(string='Disponible')
    qty = fields.Float(string='Cantidad')
    single_dot = fields.Char(string='DOT')
    lots_ids = fields.Many2many('stock.lot')
    origin_list = fields.Char(string='Lista')
    price = fields.Float(string='Precio', digits=(16, 2))
    discount_price = fields.Float(string='Precio con Descuento', digits=(16, 2))
    subtotal = fields.Float(string='Subtotal', digits=(16, 2))
    location_id = fields.Many2one('stock.location', string='Ubicación')
    
    
    @api.onchange('qty')
    def _check_qty(self):
        if not (self.qty>0 and self.qty <= self.qty_available):
            self.qty = 0
            raise ValidationError('No se pueden agregar más llantas de las disponibles')
                
            
    
