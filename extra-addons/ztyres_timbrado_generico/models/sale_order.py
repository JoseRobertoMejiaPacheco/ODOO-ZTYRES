from odoo import _, api, fields, models

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    payment_promo_text = fields.Html(compute='compute_promo_text', string='Promociones')
    bonificacion = fields.Float(string='Monto Bonificación')
    tipo_de_timbrado = fields.Selection(string='Facturación', selection=[('normal', 'A Razón Social del Cliente'), ('generic', 'A venta mostrador')],tracking=True)
    mostrar_venta_mostrador_rel = fields.Boolean(
        related='partner_id.mostrar_venta_mostrador',
        store=False
    )