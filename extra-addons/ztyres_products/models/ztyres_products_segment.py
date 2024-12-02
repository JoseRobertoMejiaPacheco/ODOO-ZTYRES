# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

class Segment(models.Model):
	_name = 'ztyres_products.segment'
	_description = 'Segmento'

	name = fields.Char(string='Segmento')
