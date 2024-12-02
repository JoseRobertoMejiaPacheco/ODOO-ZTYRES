# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

class Face(models.Model):
	_name = 'ztyres_products.face'
	_description = 'Cara'

	name = fields.Char(string='Cara')
