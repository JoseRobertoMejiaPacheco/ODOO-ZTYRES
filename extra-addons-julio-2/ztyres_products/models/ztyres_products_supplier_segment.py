# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

class SupplierSegment(models.Model):
	_name = 'ztyres_products.supplier_segment'
	_description = 'Segmento de proveedor'

	name = fields.Char(string='Segmento de proveedor')
