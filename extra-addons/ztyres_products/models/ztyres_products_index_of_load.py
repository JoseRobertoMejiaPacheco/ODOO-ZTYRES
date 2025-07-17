# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

class IndexOfLoad(models.Model):
	_name = 'ztyres_products.index_of_load'
	_description = 'Indice de carga'

	name = fields.Char(string='Carga')
