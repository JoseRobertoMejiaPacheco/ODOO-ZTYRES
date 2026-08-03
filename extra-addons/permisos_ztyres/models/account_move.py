# -*- coding: utf-8 -*-

from odoo import models

class AccountMove(models.Model):
    
    _inherit = 'account.move'

    def _post(self, soft=True):
        
        # Si pertenece a tu grupo especial, ejecuta como sudo
        if self.env.user.has_group('permisos_ztyres.group_permisos_especiales_facturacion'):
            return super(AccountMove, self.sudo())._post(soft=soft)
        
        # Si no, flujo normal
        return super()._post(soft=soft)