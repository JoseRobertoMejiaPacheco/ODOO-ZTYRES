# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'
    cie = fields.Char(string='Número de convenio exclusivo(CIE)',default='Sin CIE')
