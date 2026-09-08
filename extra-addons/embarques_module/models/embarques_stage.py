from odoo import fields, models


class EmbarquesStage(models.Model):
    _name = 'embarques.stage'
    _description = 'Etapa de Embarque'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre de la etapa', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    fold = fields.Boolean(string='Plegado en Kanban', default=False)
