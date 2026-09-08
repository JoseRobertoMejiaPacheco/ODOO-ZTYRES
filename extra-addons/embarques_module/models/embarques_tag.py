from odoo import fields, models


class EmbarquesTag(models.Model):
    _name = 'embarques.tag'
    _description = 'Etiqueta de Embarque'

    name = fields.Char(string='Nombre', required=True)
    color = fields.Integer(string='Color', default=0)
