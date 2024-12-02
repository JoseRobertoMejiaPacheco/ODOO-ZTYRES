# -*- coding: utf-8 -*-
from odoo import _, api, models,fields
from odoo.exceptions import UserError

from odoo.tools.float_utils import float_compare, float_is_zero


# x = self.env['stock.quant'].search([])
# for index, item in enumerate(x, start=1):
#     item.distance = item.location_id.distance
#     try:
#         item.dot_year = int(item.lot_id.name)
#         print(f"{index} de {len(x)}")l
#     except ValueError:
#         pass
    

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    distance = fields.Float(string='Distancia',readonly=True,digits=(16, 5))
    dot_year = fields.Integer(string='DOT')

    def write(self, vals):
        for item in self:
            updated_vals = vals.copy()  # Crea una copia de vals en cada iteración
            updated_vals.update({'distance': item.location_id.distance})
            if item.lot_id:
                try:
                    updated_vals.update({'dot_year': int(item.lot_id.name)})
                except ValueError:
                    updated_vals.update({'dot_year': False})
            print(str(item.id), updated_vals)
            res = super(StockQuant, item).write(updated_vals)  # Usa item en lugar de self
        return res

    @api.model
    def _update_reserved_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, strict=False,order_reverse=True):
        """ Increase the reserved quantity, i.e. increase `reserved_quantity` for the set of quants
        sharing the combination of `product_id, location_id` if `strict` is set to False or sharing
        the *exact same characteristics* otherwise. Typically, this method is called when reserving
        a move or updating a reserved move line. When reserving a chained move, the strict flag
        should be enabled (to reserve exactly what was brought). When the move is MTS,it could take
        anything from the stock, so we disable the flag. When editing a move line, we naturally
        enable the flag, to reflect the reservation according to the edition.
        
        Si order_reverse es True va a reservar de la mayor distancia a la menor. 
        Si order_reverse es False va a reservar de la menor distancia a la mayor. 

        :return: a list of tuples (quant, quantity_reserved) showing on which quant the reservation
            was done and how much the system was able to reserve on it
        """
        self = self.sudo()
        rounding = product_id.uom_id.rounding
        #TODO Fix performance
        #Ordenar quants
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
        for item in quants:
            print('%s %s %s'%(item.location_id.name,item.location_id.distance,item.available_quantity))
        #Funcion AQUI
        reserved_quants = []

        if float_compare(quantity, 0, precision_rounding=rounding) > 0:
            # if we want to reserve
            available_quantity = sum(quants.filtered(lambda q: float_compare(q.quantity, 0, precision_rounding=rounding) > 0).mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
            if float_compare(quantity, available_quantity, precision_rounding=rounding) > 0:
                raise UserError(_('It is not possible to reserve more products of %s than you have in stock.', product_id.display_name))
        elif float_compare(quantity, 0, precision_rounding=rounding) < 0:
            # if we want to unreserve
            available_quantity = sum(quants.mapped('reserved_quantity'))
            if float_compare(abs(quantity), available_quantity, precision_rounding=rounding) > 0:
                raise UserError(_('It is not possible to unreserve more products of %s than you have in stock.', product_id.display_name))
        else:
            return reserved_quants

        for quant in quants:
            if float_compare(quantity, 0, precision_rounding=rounding) > 0:
                max_quantity_on_quant = quant.quantity - quant.reserved_quantity
                if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                    continue
                max_quantity_on_quant = min(max_quantity_on_quant, quantity)
                quant.reserved_quantity += max_quantity_on_quant
                reserved_quants.append((quant, max_quantity_on_quant))
                quantity -= max_quantity_on_quant
                available_quantity -= max_quantity_on_quant
            else:
                max_quantity_on_quant = min(quant.reserved_quantity, abs(quantity))
                quant.reserved_quantity -= max_quantity_on_quant
                reserved_quants.append((quant, -max_quantity_on_quant))
                quantity += max_quantity_on_quant
                available_quantity += max_quantity_on_quant

            if float_is_zero(quantity, precision_rounding=rounding) or float_is_zero(available_quantity, precision_rounding=rounding):
                break
        return reserved_quants


    @api.model
    def _get_removal_strategy_order(self, removal_strategy):
        #README Cambiado tempralmente
        if removal_strategy == 'fifo':
            return 'distance ASC, dot_year ASC'
        elif removal_strategy == 'lifo':
            return 'in_date DESC, id DESC'
        elif removal_strategy == 'closest':
            return 'distance DESC'
        raise UserError(_('Removal strategy %s not implemented.') % (removal_strategy,))

    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        removal_strategy = self._get_removal_strategy(product_id, location_id)
        removal_strategy_order = self._get_removal_strategy_order(removal_strategy)
        domain = self._get_gather_domain(product_id, location_id, lot_id, package_id, owner_id, strict)
        quants_cache = self.env.context.get('quants_cache')
        if quants_cache is not None and strict:
            res = self.env['stock.quant']
            if lot_id:
                res |= quants_cache[
                    product_id.id, location_id.id, lot_id.id,
                    package_id and package_id.id or False,
                    owner_id and owner_id.id or False]
            res |= quants_cache[
                product_id.id, location_id.id, False,
                package_id and package_id.id or False,
                owner_id and owner_id.id or False]
        else:
            res = self.search(domain, order=removal_strategy_order).sorted(lambda q: not q.lot_id)
            sorted_ids = sorted(res.ids, key=lambda id: self.env['stock.quant'].browse(id).location_id.distance)
            res = self.env['stock.quant'].browse(sorted_ids)
        return res