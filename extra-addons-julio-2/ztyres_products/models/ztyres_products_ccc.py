# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

class Ccc(models.Model):
	_name = 'ztyres_products.ccc'
	_description = 'Certificado obligatorio de China'

	name = fields.Char(string='CCC',default=False)
	