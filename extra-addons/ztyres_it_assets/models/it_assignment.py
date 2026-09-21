from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ItAssignment(models.Model):
    _name = 'ztyres.it.assignment'
    _description = 'Asignación de equipo TI'
    _order = 'date_from desc, id desc'

    equipment_id = fields.Many2one('ztyres.it.equipment', string='Equipo')
    mobile_id = fields.Many2one('ztyres.it.mobile', string='Celular')
    user_id = fields.Many2one('res.users', string='Usuario', required=True)
    area = fields.Char(string='Área')
    position = fields.Char(string='Puesto')
    date_from = fields.Date(string='Desde', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='Hasta')
    reason = fields.Char(string='Motivo')
    notes = fields.Text(string='Observaciones')

    @api.constrains('equipment_id', 'mobile_id')
    def _check_asset(self):
        for rec in self:
            if bool(rec.equipment_id) == bool(rec.mobile_id):
                raise ValidationError('La asignación debe tener un equipo o un celular, pero no ambos.')
