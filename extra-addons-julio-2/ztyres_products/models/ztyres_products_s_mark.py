# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

class SMark(models.Model):
	_name = 'ztyres_products.s_mark'
	_description = 'S-Mark'

	name = fields.Char(string='S-Mark')
