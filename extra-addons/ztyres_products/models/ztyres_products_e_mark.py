# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

class EMark(models.Model):
	_name = 'ztyres_products.e_mark'
	_description = 'Certificación E-Mark'

	name = fields.Char(string='E-Mark',default=False)
