# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class ext_l10n_mx_currency_multirate(models.Model):
#     _name = 'ext_l10n_mx_currency_multirate.ext_l10n_mx_currency_multirate'
#     _description = 'ext_l10n_mx_currency_multirate.ext_l10n_mx_currency_multirate'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
