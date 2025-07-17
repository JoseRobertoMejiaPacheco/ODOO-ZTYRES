from odoo import _, api, fields, models


class Groups(models.Model):
    _name = 'ztyres_volumen.group'
    _description = 'Grupos'
    name = fields.Char(string='Nombre del Grupo')
    partner_ids = fields.Many2many('res.partner', string='Clientes')