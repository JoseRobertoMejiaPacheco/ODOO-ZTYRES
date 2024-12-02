# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

class FloorDepth(models.Model):
    _name = 'ztyres_products.floor_depth'
    _description = 'Profundidad del Dibujo'
    
    name = fields.Char(string='Nombre', compute='_compute_rec_name', store=True)
    depth = fields.Float(string='Profundidad')
    @api.depends('depth')
    def _compute_rec_name(self):
        for record in self:
            if record.depth.is_integer():
                record._rec_name = str(int(record.depth)) + 'mm'
            else:
                record._rec_name = str(record.depth) + 'mm'

    
