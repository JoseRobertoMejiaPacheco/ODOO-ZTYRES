# -*- coding: utf-8 -*-

from odoo import models, fields


class ztyres_block_brands(models.Model):
    _name = 'ztyres_block_brands'
    _description = 'Bloqueo de marcas por cliente'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        ondelete='cascade',
    )

    restricted_brand_ids = fields.Many2many(
        'ztyres_products.brand',
        'ztyres_block_brands_brand_rel',
        'block_id',
        'brand_id',
        string='Marcas restringidas',
    )

    _sql_constraints = [
        ('unique_partner',
         'unique(partner_id)',
         'Ya existe una configuración de bloqueo para este cliente.'),
    ]