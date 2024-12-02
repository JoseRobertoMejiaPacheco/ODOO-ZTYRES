# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import math

from lxml import etree

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools import parse_date



try:
    from num2words import num2words
except ImportError:
    _logger.warning("The num2words python library is not installed, amount-to-text features won't be fully available.")
    num2words = None


class Currency(models.Model):
    _inherit = "res.currency"
    _sql_constraints = [
        ('unique_name', 'Check(1=1)', 'The currency code must be unique!'),
        ('rounding_gt_zero', 'CHECK (rounding>0)', 'The rounding factor must be greater than 0!')
    ]
    
    type = fields.Selection(
        string='Tipo de Registro',
        selection=[('custom', 'Personalizado')]
    )
    
    def name_get(self):
        return [(currency.id, '%s %s'%(tools.ustr(currency.name),tools.ustr(currency.full_name))) for currency in self]

#/usr/lib/python3/dist-packages/odoo/addons/currency_rate_live/models/res_config_settings.py