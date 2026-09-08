from odoo import _, api, fields, models
from odoo.fields import Command
class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    payment_promo_text = fields.Html(compute='compute_promo_text', string='Promociones')
    bonificacion = fields.Float(string='Monto Bonificación')
    tipo_de_timbrado = fields.Selection(string='Facturación', selection=[('normal', 'A Razón Social del Cliente'), ('generic', 'A venta mostrador')],tracking=True)
    mostrar_venta_mostrador_rel = fields.Boolean(
        related='partner_id.mostrar_venta_mostrador',
        store=False
    )
    
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        
        return {
            'generic_edi': True if self.tipo_de_timbrado == 'generic' else False,
            'ref': self.client_order_ref or '',
            'move_type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id._get_fiscal_position(self.partner_invoice_id)).id,
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_user_id': self.user_id.id,
            'payment_reference': self.reference,
            'transaction_ids': [Command.set(self.transaction_ids.ids)],
            'company_id': self.company_id.id,
            'invoice_line_ids': [],
            'user_id': self.user_id.id,
        }      