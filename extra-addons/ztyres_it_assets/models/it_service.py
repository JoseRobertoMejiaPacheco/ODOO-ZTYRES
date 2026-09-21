from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ItService(models.Model):
    _name = 'ztyres.it.service'
    _description = 'Servicio de equipo TI'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Folio', required=True, copy=False, readonly=True, default='Nuevo')
    equipment_id = fields.Many2one('ztyres.it.equipment', string='Equipo')
    mobile_id = fields.Many2one('ztyres.it.mobile', string='Celular')
    date = fields.Date(string='Fecha', required=True, default=fields.Date.context_today)
    service_type = fields.Selection([
        ('preventive', 'Preventivo'),
        ('corrective', 'Correctivo'),
        ('software', 'Software'),
        ('diagnostic', 'Diagnóstico'),
        ('other', 'Otro'),
    ], string='Tipo de servicio', default='corrective', required=True)
    requested_by = fields.Many2one('res.users', string='Solicitado por')
    attended_by = fields.Many2one('res.users', string='Atendido por')
    description = fields.Text(string='Descripción')
    work_done = fields.Text(string='Trabajo realizado')
    result = fields.Text(string='Resultado')
    cost = fields.Monetary(string='Costo')
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        required=True,
        default=lambda self: self.env.company.currency_id.id,
    )
    state = fields.Selection([
        ('draft', 'Pendiente'),
        ('progress', 'En proceso'),
        ('done', 'Realizado'),
        ('cancelled', 'Cancelado'),
    ], string='Estado', default='draft', required=True, tracking=True)

    @api.constrains('equipment_id', 'mobile_id')
    def _check_asset(self):
        for rec in self:
            if bool(rec.equipment_id) == bool(rec.mobile_id):
                raise ValidationError('El servicio debe tener un equipo o un celular, pero no ambos.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('ztyres.it.service') or 'Nuevo'
        return super().create(vals_list)

    def action_progress(self):
        self.write({'state': 'progress'})
        return True

    def action_done(self):
        self.write({'state': 'done'})
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        return True
