from odoo import fields, models


class ItBrand(models.Model):
    _name = 'ztyres.it.brand'
    _description = 'Marca de equipo TI'
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)


class ItProgram(models.Model):
    _name = 'ztyres.it.program'
    _description = 'Programa o sistema'
    _order = 'name'

    name = fields.Char(required=True)
    description = fields.Text()
    active = fields.Boolean(default=True)


class ItAccessoryType(models.Model):
    _name = 'ztyres.it.accessory.type'
    _description = 'Tipo de accesorio'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)


class ItState(models.Model):
    _name = 'ztyres.it.state'
    _description = 'Estado de equipo TI'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
