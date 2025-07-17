# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

class Speed(models.Model):
	_name = 'ztyres_products.speed'
	_description = 'Velocidad'

	name = fields.Char(string='Velocidad')
