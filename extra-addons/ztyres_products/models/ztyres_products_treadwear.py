# -*- coding: utf-8 -*-
from odoo import api, fields, models


class FloorDepth(models.Model):
    _name = 'ztyres_products.treadwear'
    _description = 'Índice treadwear'
    _rec_name = 'name'

    name = fields.Char(
        string='Nombre',
        compute='_compute_name',
        store=True
    )
    number = fields.Float(string='Valor treadwear')

    @api.depends('number')
    def _compute_name(self):
        for record in self:
            if record.number:
                if float(record.number).is_integer():
                    record.name = f"{int(record.number)}"
                else:
                    record.name = f"{record.number}"
            else:
                record.name = ''
