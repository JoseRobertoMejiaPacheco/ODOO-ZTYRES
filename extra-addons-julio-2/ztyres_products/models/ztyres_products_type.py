# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

class Type(models.Model):
	_name = 'ztyres_products.type'
	_description = 'Tipo'

	name = fields.Char(string='Tipo')
