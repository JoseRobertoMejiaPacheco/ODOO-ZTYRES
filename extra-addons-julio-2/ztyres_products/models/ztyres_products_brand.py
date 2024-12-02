# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

class Brand(models.Model):
	_name = 'ztyres_products.brand'
	_description = 'Marca'

	name = fields.Char(string='Marca')
