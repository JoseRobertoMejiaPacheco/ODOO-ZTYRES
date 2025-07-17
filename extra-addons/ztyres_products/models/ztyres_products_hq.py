# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

class Hq(models.Model):
	_name = 'ztyres_products.hq'
	_description = 'HQ'

	name = fields.Float(string='HQ')