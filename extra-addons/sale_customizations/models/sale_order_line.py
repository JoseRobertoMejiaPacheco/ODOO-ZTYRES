# -*- coding: utf-8 -*-
from odoo import api, models, SUPERUSER_ID, _
from odoo.exceptions import  ValidationError
from odoo import models,api,fields, _
from datetime import date, timedelta, datetime
from odoo.addons.inv_promo.models.inv_promo_variables import PAQUETES as PROMO_MARZO

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    price_unit_discount = fields.Float(compute='_compute_price_unit_discount', string='Precio Unitario con descuento', digits=(6, 2))    
    list_origin = fields.Char(string='Lista de Origen')
    pricelist_id = fields.Many2one('product.pricelist', string='Lista de Precios')
    def _compute_price_unit_discount(self):
        for record in self:
            record.price_unit_discount = record.price_unit -(record.price_unit * ((record.discount/100)))  

    @api.onchange('product_uom_qty', 'product_id')
    def _onchange_check_product_availability(self):
        for product in self:
            if product.product_id.detailed_type == 'product' and product.product_uom_qty:            
                if product.product_uom_qty > product.product_id.free_qty:
                    warning_msg = {
                        'title': _('¡Inventario insuficiente!'),
                        'message': _('Estás intentando vender %s de %s pero solo tienes %s disponibles (después de considerar otras reservaciones).') % (product.product_uom_qty, product.product_id.name, product.product_id.free_qty)
                    }
                    return {'warning': warning_msg}

    @api.constrains('product_uom_qty')
    def _constrains_check_product_availability(self):
        for record in self:
            if record.product_id.detailed_type == 'product' and record.product_uom_qty:
                if record.product_uom_qty > record.product_id.free_qty:
                    raise ValidationError(_('Estás intentando vender %s de %s pero solo tienes %s disponibles (después de considerar otras reservaciones).') % (record.product_uom_qty, record.product_id.name, record.product_id.free_qty))
    
    def _get_valid_pricelists(self):
        return [1,108,113,116]
    
    def get_item_with_min_price_after_discount(self):
        if self.order_id.is_expo:
            domain = [
            ('product_tmpl_id', 'in', self.product_id.product_tmpl_id.ids),
            ('pricelist_id', 'in', self.order_id.pricelist_id.ids)]
            return self.pricelist_item_id.search(domain)
        else:
            domain = [
                ('product_tmpl_id', 'in', self.product_id.product_tmpl_id.ids),
                ('pricelist_id', 'in', self._get_valid_pricelists())
            ]
        # Buscar los items de la lista de precios según el dominio definido
        pricelist_items = self.pricelist_item_id.search(domain)
        
        # Inicializar variables para rastrear el ítem con el menor precio después del descuento
        min_price = float('inf')
        min_price_item = None
        
        # Iterar sobre los items encontrados para calcular el precio con descuento y encontrar el mínimo
        for item in pricelist_items:
            discounted_price = None
            
            if item.pricelist_id.id == 1:
                # Suponiendo que item.fixed_price contiene el precio original
                discounted_price = item.fixed_price * (1 - (self.order_partner_id.volume_profile.percent / 100))
            elif item.pricelist_id.id == 116 and self.product_uom_qty >= 250:
                return item
            elif item.pricelist_id.id in [108, 113]:
                discounted_price = item.fixed_price
            
            # Comparar con el precio mínimo encontrado hasta ahora, si discounted_price fue definido
            if discounted_price is not None and discounted_price < min_price:
                min_price = discounted_price
                min_price_item = item
        
        # Devolver el ítem con el menor precio después del descuento
        return min_price_item
        
    def _get_pricelist_price(self):
        """Compute the price given by the pricelist for the given line information.

        :return: the product sales price in the order currency (without taxes)
        :rtype: float
        """
        self.ensure_one()
        self.product_id.ensure_one()

        # pricelist_rule = self.pricelist_item_id
        order_date = self.order_id.date_order or fields.Date.today()
        product = self.product_id.with_context(**self._get_product_price_context())
        qty = self.product_uom_qty or 1.0
        uom = self.product_uom or self.product_id.uom_id
        currency = self.currency_id or self.order_id.company_id.currency_id
        
        search_domain = [
            ('product_tmpl_id', 'in', self.product_template_id.ids),('additional_prod_id.active','=',True),('additional_prod_id.is_mix','=',False)
        ]
        x = self.env['additional_discounts.products_line'].search(search_domain)
        
        if x:
            self.discount = 0
            x.ensure_one()
            if qty >= x.qty:
                self.list_origin = 'PAQUETE'
                return x.price
        
        self.pricelist_item_id = self.get_item_with_min_price_after_discount()
        self.list_origin = self.pricelist_item_id.pricelist_id.name
        self.pricelist_id = self.pricelist_item_id.pricelist_id.id
        if not (self.product_id.id == 50959) and (self.pricelist_item_id.pricelist_id.id in self.order_id.partner_id.volume_profile.pricelist_ids.ids):
            self.discount = self.order_id.partner_id.volume_profile.percent
        else:
            self.discount = 0
        
        price = self.pricelist_item_id._compute_price(
            product, qty, uom, order_date, currency=currency)
        
        return price