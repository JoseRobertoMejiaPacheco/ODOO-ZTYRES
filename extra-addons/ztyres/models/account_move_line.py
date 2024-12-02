# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    dot_range = fields.Char(related='product_id.dot_range')
    currency_price_subtotal = fields.Float(compute='_compute_currency_price_subtotal', string='Conversión a moneda Local')
    price_unit_discount = fields.Float(compute='_compute_price_unit_discount', string='Precio Unitario con descuento', digits=(6, 2))
    sol_id = fields.Many2many(
    'sale.order.line',           # Modelo relacionado
    'sale_order_line_invoice_rel',  # Nombre de la tabla relacional
    'invoice_line_id',           # Columna en la tabla relacional que referencia a este modelo
    'order_line_id',             # Columna en la tabla relacional que referencia al modelo relacionado
    string='Sol'
    )

    rangos_dots = fields.Char("Rangos Dots", compute="_compute_rangos_dots_from_sale")

    @api.depends('sol_id')  # Asegúrate de tener la relación adecuada para obtener las líneas de pedido de venta.
    def _compute_rangos_dots_from_sale(self):
        for record in self:
            sale_order_lines = record.sol_id  # Asegúrate de tener esta relación configurada.
            if sale_order_lines:
                # Si tienes múltiples líneas, puedes ajustarlo según tu lógica.
                # Por ejemplo, concatenar los valores de rangos_dots de todas las líneas de venta.
                record.rangos_dots = ', '.join(sale_order_lines.mapped('rangos_dots'))
            else:
                record.rangos_dots = False
    
    def _compute_currency_price_subtotal(self):
        for record in self:
            record.currency_price_subtotal = record.currency_id._convert(record.price_subtotal,record.company_currency_id,record.company_id,record.date)


    def _compute_price_unit_discount(self):
        for record in self:
            record.price_unit_discount =record.price_unit -(record.price_unit * ((record.discount/100)))
            
    def _check_reconciliation(self):
        for line in self:
            if line.matched_debit_ids or line.matched_credit_ids:
                pass
                # raise UserError(_("You cannot do this modification on a reconciled journal entry. "
                #                   "You can just change some non legal fields or you must unreconcile first.\n"
                #                   "Journal Entry (id): %s (%s)") % (line.move_id.name, line.move_id.id))