# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ZtyresVolumenLines(models.Model):
    _name = 'ztyres_promo.lines'
    definitive_nc_id = fields.Many2one('ztyres_promo.notas_credito')
    group_id = fields.Many2one('ztyres_volumen.group', string='Grupo')
    move_type = fields.Char(string='Move Type')
    move_id = fields.Many2one('account.move',string='Move Name')
    product_name = fields.Char(string='Product Name')
    name = fields.Char(string='Name')
    product_id = fields.Many2one('product.template', string='Producto')
    product_code = fields.Char(string='Product Code')
    product_brand = fields.Char(string='Brand')
    date = fields.Date(string='Date')
    quantity = fields.Float(string='Quantity')
    price_subtotal = fields.Float(string='Subtotal')
    partner_id = fields.Many2one('res.partner', string='Partner')
    sale_origin = fields.Char(string='Sale Origin')
    list_origin = fields.Char(string='List Origin')
    state = fields.Char(string='Status')
    rfc = fields.Char(string='RFC')