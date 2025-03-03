# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

class Model(models.Model):
	_name = 'ztyres_products.model'
	_description = 'Modelo'

	name = fields.Char(string='Modelo')
