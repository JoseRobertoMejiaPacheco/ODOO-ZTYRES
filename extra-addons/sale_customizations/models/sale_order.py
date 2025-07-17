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

    def action_confirm(self):
        if self.id == 60906:
            return super(SaleOrder, self).action_confirm()
        # Agregar codigo de validacion aca
        for record in self:
            if record.partner_id:
                if record.partner_id.name in locked_names:
                    raise ValidationError('El Cliente bloqueado por falta de reglas de negocio firmadas%s '%(record.partner_id.name))                    
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
    

