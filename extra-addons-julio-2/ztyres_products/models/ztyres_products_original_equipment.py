# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

class OriginalEquipment(models.Model):
	_name = 'ztyres_products.original_equipment'
	_description = 'Equipamiento original'

	name = fields.Char(string='Equipamiento original')
