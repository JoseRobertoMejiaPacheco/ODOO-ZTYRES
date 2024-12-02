# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class apply_payments(models.Model):
#     _name = 'apply_payments.apply_payments'
#     _description = 'apply_payments.apply_payments'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
