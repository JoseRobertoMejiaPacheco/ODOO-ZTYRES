# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

class Tier(models.Model):
	_name = 'ztyres_products.tier'
	_description = 'Tier'

	name = fields.Char(string='Tier')
