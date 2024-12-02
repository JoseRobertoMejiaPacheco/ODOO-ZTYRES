# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

class Layer(models.Model):
	_name = 'ztyres_products.layer'
	_description = 'Capas'

	name = fields.Char(string='Capas')
