from datetime import timedelta
from odoo import models, fields, api
import calendar
from datetime import datetime

class PaymentDiscountMixin(models.AbstractModel):
    _inherit = 'payment.discount.mixin'
    
    
    def get_row_values_descuento(self, record):
        if record.promo_sel:
            return self.get_discounts_list_promo_sel(record)
        else:
            return self.get_discounts_list(record)
    
    def get_discounts_list(self,record):
        descuentos = []
        if record.partner_id.financial_profile:
            shipping_with_taxes = self._calculate_without_shipping_price(record)
            descuentos_cliente = record.partner_id.financial_profile.line_ids
            for profile_line in descuentos_cliente:
                monto_descuento, fecha_vencimiento = self._calculate_discount(record, shipping_with_taxes, profile_line)
                descuentos.append((profile_line.discount, profile_line.upper_limit, fecha_vencimiento, monto_descuento))
        return descuentos

    def get_discounts_list_promo_sel(self,record):
        descuentos = []
        shipping_with_taxes = self._calculate_without_shipping_price(record)
        if record.promo_sel.percent_1 > 0 and record.promo_sel.property_payment_term_id_1:
            monto_descuento_1, fecha_vencimiento_1 = self._calculate_discount_promo_sel(record, shipping_with_taxes, record.promo_sel.percent_1,record.promo_sel.property_payment_term_id_1.line_ids.days)
            descuentos.append((record.promo_sel.percent_1, record.promo_sel.property_payment_term_id_1.line_ids.days, fecha_vencimiento_1, monto_descuento_1))
        if record.promo_sel.percent_2 > 0 and record.promo_sel.property_payment_term_id_2:
            monto_descuento_2, fecha_vencimiento_2 = self._calculate_discount_promo_sel(record, shipping_with_taxes, record.promo_sel.percent_2,record.promo_sel.property_payment_term_id_2.line_ids.days)
            descuentos.append((record.promo_sel.percent_2, record.promo_sel.property_payment_term_id_2.line_ids.days, fecha_vencimiento_2, monto_descuento_2))
        return descuentos
    
    def _calculate_discount(self, record, shipping_with_taxes, profile_line):
        discount = ((profile_line.discount / 100.0))
        BS = record.bs_nc_amount*1.16
        MT = record.amount_total
        ST = MT  - shipping_with_taxes
        NL = record.logistic_nc_amount*1.16
        MF = ST * discount
        TOTAL_PAGAR = ST - NL - MF - BS+ shipping_with_taxes
        
        if hasattr(record, 'invoice_line_ids'):
            fecha_vencimiento =  record.invoice_date + timedelta(days=profile_line.upper_limit)
            return TOTAL_PAGAR, fecha_vencimiento
        else:
            fecha_vencimiento = record.date_order + timedelta(days=profile_line.upper_limit)
            return TOTAL_PAGAR, fecha_vencimiento
    
    def _calculate_discount_promo_sel(self, record, shipping_with_taxes, discount,days):
        discount = ((discount / 100.0))
        BS = record.bs_nc_amount*1.16
        MT = record.amount_total
        ST = MT  - shipping_with_taxes
        NL = record.logistic_nc_amount*1.16
        MF = ST * discount
        TOTAL_PAGAR = ST - NL - MF - BS+ shipping_with_taxes
        
        if hasattr(record, 'invoice_line_ids'):
            fecha_vencimiento =  record.invoice_date + timedelta(days=days)
            return TOTAL_PAGAR, fecha_vencimiento
        else:
            fecha_vencimiento = record.date_order + timedelta(days=days)
            return TOTAL_PAGAR, fecha_vencimiento
    
 