# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

class Usage(models.Model):
	_name = 'ztyres_products.usage'
	_description = 'New Description'

	name = fields.Char(string='Uso')
