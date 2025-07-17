# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ZtyresPromoElige(models.Model):
    _name = 'ztyres_promo_elige.ztyres_promo_elige'
    _description = 'Promociones Eligé para Ztyres'
    _rec_name = 'nombre'
    
    active = fields.Boolean(default=True)
    start_date = fields.Date(string='Fecha Inicio')
    end_date = fields.Date(string='Fecha Fin')
    status = fields.Selection(
        string="Estado de Envio", 
        selection=[
            ('draft', 'Borrador'),
            ('approve_p', 'Promoción Aprobada'),
            ('done', 'Confirmado'),
            ('cancel', 'Cancelado')
        ],
        default='draft'
    )
    nombre = fields.Char(string="Nombre")
    min_qty = fields.Integer(string='Cantidad Mínima')
    
    # Promoción 1
    property_payment_term_id_1 = fields.Many2one(
        'account.payment.term', 
        string='Términos de pago del cliente (Promo 1)'
    )
    percent_1 = fields.Integer(string='Descuento Financiero (%)')
    
    # Promoción 2
    property_payment_term_id_2 = fields.Many2one(
        'account.payment.term', 
        string='Términos de pago del cliente (Promo 2)'
    )
    percent_2 = fields.Integer(string='Descuento Financiero (%)')
    
    # Marcas participantes
    brand_ids = fields.Many2many(
        'ztyres_products.brand', 
        string='Marcas Participantes'
    )
    
    invoice_ids = fields.Many2many(comodel_name='account.move', string='Facturas Aplicadas',compute='_compute_invoices')
    def _compute_invoices(self):
        for record in self:
            invoices = self.env['account.move'].search([
                ('promo_sel', 'in', [record.id]),
                ('state','in',['posted']),
                ('move_type','in',['out_invoice'])
            ])
            record.invoice_ids = invoices
    
    def action_view_applied_invoices(self):
        self.ensure_one()
        return {
            'name': 'Facturas Aplicadas',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.invoice_ids.ids)],
            'context': {'create': False},
        }
    
class AccountMove(models.Model):
    _inherit = 'account.move'
    promo_sel  = fields.Many2many('ztyres_promo_elige.ztyres_promo_elige')

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    promo_sel  = fields.Many2many('ztyres_promo_elige.ztyres_promo_elige',compute='_compute_promo_sel',store=True,string='Promoción')
    
    @api.depends('order_line', 'order_line.product_id', 'order_line.product_uom_qty', 
                 'order_line.product_id.brand_id')
    def _compute_promo_sel(self):
        for record in self:
            promo_id = self.env['ztyres_promo_elige.ztyres_promo_elige'].search([], limit=1)
            if promo_id:
                # Filtrar líneas válidas (marcas incluidas en la promoción)
                valid_lines = record.order_line.filtered(
                    lambda l: l.product_id.brand_id.id in promo_id.brand_ids.ids
                )
                
                # Calcular cantidades
                valid_qty = sum(valid_lines.mapped('product_uom_qty'))
                total_qty = sum(record.order_line.mapped('product_uom_qty'))
                
                # Verificar condiciones de la promoción
                if valid_qty >= promo_id.min_qty:
                    if valid_qty == total_qty:
                        record.promo_sel = promo_id
                        record.payment_term_id = promo_id.property_payment_term_id_2
                        print(record.payment_term_id)
                    else:
                        raise UserError(
                            _("Se ha detectado la promoción '%s', pero para que sea válida "
                            "el pedido debe contener únicamente productos de las marcas "
                            "participantes.") % promo_id.nombre
                        )
                else:
                    record.promo_sel = False
                    record.payment_term_id = record.partner_id.property_payment_term_id
            else:
                record.promo_sel = False
                record.payment_term_id = record.partner_id.property_payment_term_id

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        return {
            **invoice_vals,
            'promo_sel': self.promo_sel,  # o 'valor_personalizado' si es fijo
        }

# class SaleAdvancePaymentInv(models.TransientModel):
#     _inherit = 'sale.advance.payment.inv'
    
#     def create_invoices(self):
#         # Agregar codigo de validacion aca
#         if len(self.sale_order_ids)>1:
#             raise UserError(_('No es posible realizar una factura de varios pedidos, solicite ayuda a soporte.'))
#         return super(SaleAdvancePaymentInv, self).create_invoices()