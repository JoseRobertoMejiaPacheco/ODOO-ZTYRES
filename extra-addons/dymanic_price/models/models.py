from odoo import _, api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from pytz import timezone
import pytz
OUTLET = []
PAQUETES = []
class SaleOrder(models.Model):
    _inherit = 'sale.order'
    #Poner Variable para ver si aparece o no en el reporte
    total_dymamic_price = fields.Float(compute='_compute_total_dymamic_price', string='Total a Pagar',
    digits=(16, 2)
    )
    
    @api.depends('order_line.price_subtotal', 'order_line.tax_id.amount')  # Asegúrate de que la función dependa de los subtotales de las líneas y de las cantidades de impuestos
    def _compute_total_dymamic_price(self):
        for record in self:
            total_with_tax = 0
            for line in record.order_line:
                subtotal = line.dynamyc_price * line.product_qty
                taxes = line.tax_id.amount / 100  # Divide por 100 para obtener la tasa decimal de impuestos
                total_with_tax += subtotal * (1 + taxes)  # Calcula el total con impuestos sumando el subtotal y su impuesto
            record.total_dymamic_price = total_with_tax  # Asigna el resultado al campo total_dynamic_price en el registro actual
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'  
    
    dynamyc_price = fields.Float(string='Precio Dinamico',digits=(16, 2))
    origin_list = fields.Char(string='Lista de Origen')