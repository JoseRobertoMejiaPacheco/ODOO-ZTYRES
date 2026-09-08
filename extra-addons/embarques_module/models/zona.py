from odoo import fields, models


class EmbarquesZona(models.Model):
    """Zona logística de destino (Zona 1, Zona 2, Zona 3).

    Cada destino pertenece a una zona. La zona, cruzada con el rango alcanzado,
    determina el porcentaje de descuento.
    """

    _name = 'embarques.zona'
    _description = 'Zona Logística'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    active = fields.Boolean(string='Activo', default=True)
    note = fields.Char(string='Descripción')
