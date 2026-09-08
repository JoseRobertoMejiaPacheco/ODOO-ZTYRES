from odoo import fields, models


class RutasEmbarques(models.Model):
    _name = 'rutas_embarques'
    _description = 'Rutas Embarques'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True)
    active = fields.Boolean(string='Activo', default=True)
    sequence = fields.Integer(string='Secuencia', default=10)
