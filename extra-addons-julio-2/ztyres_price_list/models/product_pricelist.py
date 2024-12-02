# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    exclude_from_export_lists = fields.Boolean(string='Excluir de la exportación de listas de precios.',default=True)
    exclude_from_order = fields.Boolean(string='Excluye esta lista de precios en los pedidos de venta.',default=True)
    terms = fields.Text(string='Términos y condiciones')
    
