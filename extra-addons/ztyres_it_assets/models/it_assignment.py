from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


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

    # Datos que pide el formato Z-FO-TI-01 (asignación y resguardo)
    physical_condition = fields.Selection([
        ('new', 'Nuevo'),
        ('reassigned', 'Reasignado'),
        ('other', 'Otro'),
    ], string='Condición física',
        help='Si se deja vacío, el formato marca "Nuevo" cuando es la primera '
             'asignación del equipo y "Reasignado" cuando ya tuvo otra.')
    physical_condition_other = fields.Char(string='Otra condición')
    return_reason = fields.Selection([
        ('termination', 'Baja de la empresa'),
        ('position_change', 'Cambio de puesto'),
        ('equipment_change', 'Cambio de equipo'),
        ('repair', 'Reparación'),
        ('renewal', 'Renovación'),
        ('other', 'Otro'),
    ], string='Motivo de devolución')
    return_reason_other = fields.Char(string='Otro motivo de devolución')
    return_condition = fields.Selection([
        ('normal', 'Con desgaste normal de uso'),
        ('damaged', 'Dañado por mal uso'),
        ('incomplete', 'Incompleto'),
    ], string='Estado al devolver')
    return_notes = fields.Text(string='Observaciones de devolución')

    @api.constrains('equipment_id', 'mobile_id')
    def _check_asset(self):
        for rec in self:
            if bool(rec.equipment_id) == bool(rec.mobile_id):
                raise ValidationError('La asignación debe tener un equipo o un celular, pero no ambos.')

    def action_print_resguardo(self):
        """Descarga el formato Z-FO-TI-01 (Excel) lleno con esta asignación."""
        self.ensure_one()
        if not self.equipment_id:
            raise UserError(_(
                'Este formato es solo para equipo de cómputo. '
                'La asignación no tiene un equipo.'))
        return {
            'type': 'ir.actions.act_url',
            'url': '/ztyres_it_assets/resguardo/assignment/%d' % self.id,
            'target': 'self',
        }
