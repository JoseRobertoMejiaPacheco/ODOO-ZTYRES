# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare

from werkzeug.urls import url_encode
from odoo import models, fields,api, _
from odoo.tools import  float_compare
from odoo.exceptions import UserError

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    dot_range = fields.Char(related='product_id.dot_range')
    rangos_dots = fields.Char(string='Rango Dot', compute='_compute_rangos_dots')

    def _ztyres_action_launch_stock_rule(self, previous_product_uom_qty=False):
        """
        Launch procurement group run method with required/custom fields genrated by a
        sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
        depending on the sale order line product rule.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        procurements = []
        for line in self:
            line = line.with_company(line.company_id)
            if not line.product_id.type in ('consu','product'):
                continue
            qty = line._get_qty_procurement(previous_product_uom_qty)
            if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
                continue

            group_id = line._get_procurement_group()
            if not group_id:
                group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
                line.order_id.procurement_group_id = group_id
            else:
                # In case the procurement group is already created and the order was
                # cancelled, we need to update certain values of the group.
                updated_vals = {}
                if group_id.partner_id != line.order_id.partner_shipping_id:
                    updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
                if group_id.move_type != line.order_id.picking_policy:
                    updated_vals.update({'move_type': line.order_id.picking_policy})
                if updated_vals:
                    group_id.write(updated_vals)

            values = line._prepare_procurement_values(group_id=group_id)
            product_qty = line.product_uom_qty - qty

            line_uom = line.product_uom
            quant_uom = line.product_id.uom_id
            product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
            procurements.append(self.env['procurement.group'].Procurement(
                line.product_id, product_qty, procurement_uom,
                line.order_id.partner_shipping_id.property_stock_customer,
                line.name, line.order_id.name, line.order_id.company_id, values))
        if procurements:
            self.env['procurement.group'].run(procurements)
        return True    

    # @api.onchange('product_uom_qty', 'product_id')
    # def _onchange_check_product_availability(self):
        
    #     for product in self:
    #         if product.product_id.detailed_type == 'product' and product.product_uom_qty:            
    #             if product.product_uom_qty > product.product_id.free_qty:
    #                 warning_msg = {
    #                     'title': _('¡Inventario insuficiente!'),
    #                     'message': _('Estás intentando vender %s de %s pero solo tienes %s disponibles (después de considerar otras reservaciones).') % (product.product_uom_qty, product.product_id.name, product.product_id.free_qty)
    #                 }
    #                 return {'warning': warning_msg}

    # @api.constrains('price_unit')
    # def _constrains_check_price(self):
    #     for product in self:
    #         if float(product.price_unit) == 0.0:
    #             raise ValidationError(_('El producto %s tiene precio de 0.0') % product.product_id.name)

    @api.constrains('product_uom_qty')
    def _constrains_check_product_availability(self):
        for record in self:
            if record.product_id.detailed_type == 'product' and record.product_uom_qty:
                if record.product_uom_qty > record.product_id.free_qty:
                    raise ValidationError(_('Estás intentando vender %s de %s pero solo tienes %s disponibles (después de considerar otras reservaciones).') % (record.product_uom_qty, record.product_id.name, record.product_id.free_qty))
                
    def rango_fechas(self, anos):
        # Filtrar solo los años que tengan el formato correcto (4 dígitos)
        anos_validos = [ano for ano in anos if ano.isdigit() and len(ano) == 4]
        if len(anos_validos) == 0:
            return "N/A"
        elif len(anos_validos) == 1:
            return anos_validos[0]  # Si solo hay un año válido, devolverlo directamente
        elif len(anos_validos) < 1:
            return anos_validos
            # Ordenar los años válidos
        anos_validos.sort()
        # Tomar la fecha más antigua y la más reciente
        fecha_mas_antigua = anos_validos[0]
        fecha_mas_reciente = anos_validos[-1]
        print(f"Fecha más antigua: {fecha_mas_antigua}")
        print(f"Fecha más reciente: {fecha_mas_reciente}")
        return f"{fecha_mas_antigua}-{fecha_mas_reciente}"

    def _compute_rangos_dots(self):
        for sol in self:
                sol.rangos_dots = self.rango_fechas(sol.order_id.picking_ids.move_line_ids_without_package.filtered(lambda x: x.product_id.id == sol.product_id.id).mapped('lot_id').mapped('name'))
                print (sol.order_id.picking_ids.move_line_ids_without_package.filtered(lambda x: x.product_id.id == sol.product_id.id).mapped('lot_id').mapped('name'))
