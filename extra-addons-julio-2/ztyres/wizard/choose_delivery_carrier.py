# -*- coding: utf-8 -*-
from odoo import models, fields, api,_
from datetime import datetime
from odoo.exceptions import UserError

class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'
    _description = 'Delivery Carrier Selection Wizard'
    display_price = fields.Float(string='Cost', readonly=False)
    
    
    def button_confirm(self):
        self.order_id.set_delivery_line(self.carrier_id, self.display_price)
        self.order_id.write({
            'recompute_delivery_price': False,
            'delivery_message': self.delivery_message,
        })

    def _create_delivery_line(self, carrier, price_unit):
        SaleOrderLine = self.env['sale.order.line']
        context = {}
        if self.partner_id:
            # set delivery detail in the customer language
            context['lang'] = self.partner_id.lang
            carrier = carrier.with_context(lang=self.partner_id.lang)

        # Apply fiscal position
        taxes = carrier.product_id.taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
        taxes_ids = taxes.ids
        if self.partner_id and self.fiscal_position_id:
            taxes_ids = self.fiscal_position_id.map_tax(taxes).ids

        # Create the sales order line

        if carrier.product_id.description_sale:
            so_description = '%s: %s' % (carrier.product_id.name,
                                        carrier.product_id.description_sale)
        else:
            so_description = carrier.product_id.name
        values = {
            'order_id': self.id,
            'name': carrier.product_id.name,
            'product_uom_qty': 1,
            'product_uom': carrier.product_id.uom_id.id,
            'product_id': carrier.product_id.id,
            'tax_id': [(6, 0, taxes_ids)],
            'is_delivery': True,
        }
        if carrier.invoice_policy == 'real':
            values['price_unit'] = 0
            values['name'] += _(' (Estimated Cost: %s )', self._format_currency_amount(price_unit))
        else:
            values['price_unit'] = price_unit
        if carrier.free_over and self.currency_id.is_zero(price_unit) :
            values['name'] += '\n' + _('Free Shipping')
        if self.order_line:
            values['sequence'] = self.order_line[-1].sequence + 1
        sol = SaleOrderLine.sudo().create(values)
        del context
        return sol
