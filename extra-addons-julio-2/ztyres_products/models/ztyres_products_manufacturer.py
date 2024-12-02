# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

class Manufacturer(models.Model):
	_name = 'ztyres_products.manufacturer'
	_description = 'Fabricante'

	name = fields.Char(string='Fabricante')
