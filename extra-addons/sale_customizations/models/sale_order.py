# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import itertools
from collections import defaultdict
import random
import math
from odoo.osv import expression
from odoo import api, fields, models, _
from odoo.exceptions import UserError,ValidationError
from odoo.fields import Command
from odoo.tools.float_utils import float_is_zero, float_round
from .bsr_partner_lock import locked_names

class SaleOrder(models.Model):
    _inherit = "sale.order"    
    def check_qty_shipping(self):
        # Agregar código de validación aquí
        for record in self:
            product_uom_qty = sum(record.order_line.mapped('product_uom_qty'))
            
            # Se ha mejorado la legibilidad y la claridad de las condiciones
            if (
                not (float(product_uom_qty) < 30) and
                not(50959 not in record.order_line.mapped('product_id').ids) and
                (
                    record.x_studio_forma_envi == 'Se envia' or
                    (record.x_studio_forma_envi == 'Paqueteria' and
                     record.x_studio_tipo_de_paqueteria == 'Paqueteria interna')
                )
            ):
                raise ValidationError(
                    'Es necesario agregar gastos de envío para compras menores a 30 llantas\n%s %s %s %s' % (
                        product_uom_qty,
                        record.order_line.mapped('product_id').ids,
                        record.x_studio_forma_envi,
                        record.x_studio_tipo_de_paqueteria
                    )
                )
        return

    def action_confirm(self):
        if self.id == 60906:
            return super(SaleOrder, self).action_confirm()
        # Agregar codigo de validacion aca
        for record in self:
            if record.partner_id:
                if record.partner_id.name in locked_names:
                    raise ValidationError('El Cliente bloqueado por falta de reglas de negocio firmadas%s '%(record.partner_id.name))                    
            record.check_qty_shipping()
        return super(SaleOrder, self).action_confirm()
    
    @api.onchange('partner_id')
    def _onchange_check_partner_discount(self):
        res = self._onchange_partner_id_warning()
        if res:
            return res
        
        if self.partner_id:
            if self.partner_id.name in locked_names:
                raise ValidationError('El Cliente bloqueado por falta de reglas de negocio firmadas%s '%(self.partner_id.name))
            if not self.sudo().partner_id.volume_profile:
                raise ValidationError('El Cliente %s no tiene ningun Perfil configurado, por favor revise con Finanzas\nSi no tiene descuento debe ser 0'%(self.partner_id.name))


