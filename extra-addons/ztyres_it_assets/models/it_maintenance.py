from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ItMaintenance(models.Model):
    _name = 'ztyres.it.maintenance'
    _description = 'Mantenimiento de equipo TI'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'planned_date asc, id desc'

    name = fields.Char(string='Folio', required=True, copy=False, readonly=True, default='Nuevo')
    equipment_id = fields.Many2one('ztyres.it.equipment', string='Equipo')
    mobile_id = fields.Many2one('ztyres.it.mobile', string='Celular')
    planned_date = fields.Date(string='Fecha programada', required=True, default=fields.Date.context_today)
    maintenance_type = fields.Selection([
        ('preventive', 'Preventivo'),
        ('corrective', 'Correctivo'),
        ('review', 'Revisión'),
    ], string='Tipo', default='preventive', required=True)
    frequency_months = fields.Integer(string='Frecuencia (meses)', default=6)
    responsible_id = fields.Many2one('res.users', string='Responsable')
    description = fields.Text(string='Descripción')
    state = fields.Selection([
        ('planned', 'Programado'),
        ('progress', 'En proceso'),
        ('done', 'Realizado'),
        ('cancelled', 'Cancelado'),
    ], string='Estado', default='planned', required=True, tracking=True)
    completion_date = fields.Date(string='Fecha de realización')
    result = fields.Text(string='Resultado')
    next_maintenance_id = fields.Many2one('ztyres.it.maintenance', string='Siguiente mantenimiento', readonly=True)

    @api.constrains('equipment_id', 'mobile_id')
    def _check_asset(self):
        for rec in self:
            if bool(rec.equipment_id) == bool(rec.mobile_id):
                raise ValidationError('El mantenimiento debe tener un equipo o un celular, pero no ambos.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('ztyres.it.maintenance') or 'Nuevo'
        return super().create(vals_list)

    def action_progress(self):
        self.write({'state': 'progress'})
        return True

    def action_done(self):
        for rec in self:
            vals = {
                'state': 'done',
                'completion_date': fields.Date.context_today(rec),
            }
            rec.write(vals)

            if (
                rec.frequency_months
                and rec.planned_date
                and not rec.next_maintenance_id
            ):
                next_date = rec.planned_date + relativedelta(months=rec.frequency_months)
                next_vals = {
                    'equipment_id': rec.equipment_id.id or False,
                    'mobile_id': rec.mobile_id.id or False,
                    'planned_date': next_date,
                    'maintenance_type': rec.maintenance_type,
                    'frequency_months': rec.frequency_months,
                    'responsible_id': rec.responsible_id.id or False,
                    'description': rec.description,
                    'state': 'planned',
                }
                next_maintenance = self.create(next_vals)
                rec.next_maintenance_id = next_maintenance.id
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        return True

    @api.model
    def _cron_maintenance_activities(self):
        today = fields.Date.context_today(self)
        limit_date = today + relativedelta(days=7)
        records = self.search([
            ('state', '=', 'planned'),
            ('planned_date', '>=', today),
            ('planned_date', '<=', limit_date),
            ('responsible_id', '!=', False),
        ])
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            return True

        for rec in records:
            existing = self.env['mail.activity'].search_count([
                ('res_model', '=', rec._name),
                ('res_id', '=', rec.id),
                ('activity_type_id', '=', activity_type.id),
                ('user_id', '=', rec.responsible_id.id),
                ('summary', '=', 'Mantenimiento próximo'),
            ])
            if not existing:
                self.env['mail.activity'].create({
                    'activity_type_id': activity_type.id,
                    'res_model_id': self.env['ir.model']._get(rec._name).id,
                    'res_id': rec.id,
                    'user_id': rec.responsible_id.id,
                    'summary': 'Mantenimiento próximo',
                    'note': 'El mantenimiento está programado para el %s.' % rec.planned_date,
                    'date_deadline': rec.planned_date,
                })
        return True
