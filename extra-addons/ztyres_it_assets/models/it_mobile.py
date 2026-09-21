from odoo import api, fields, models


class ItMobile(models.Model):
    _name = 'ztyres.it.mobile'
    _description = 'Celular de TI'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Nombre / Equipo', required=True, tracking=True)
    inventory_number = fields.Char(
        string='Número de inventario',
        readonly=True,
        copy=False,
        default='Nuevo',
    )
    serial_number = fields.Char(string='Número de serie', tracking=True)
    user_id = fields.Many2one('res.users', string='Usuario asignado', tracking=True)
    employee_name = fields.Char(string='Nombre del usuario', related='user_id.name', store=True)
    area = fields.Char(string='Área')
    position = fields.Char(string='Puesto')

    phone_number = fields.Char(string='Número telefónico', tracking=True)
    carrier = fields.Char(string='Compañía telefónica')
    brand_id = fields.Many2one('ztyres.it.brand', string='Marca')
    model = fields.Char(string='Modelo')
    imei_1 = fields.Char(string='IMEI 1')
    imei_2 = fields.Char(string='IMEI 2')
    operating_system = fields.Char(string='Sistema operativo')
    os_version = fields.Char(string='Versión')
    ram = fields.Char(string='RAM')
    storage = fields.Char(string='Almacenamiento')
    acquisition_date = fields.Date(string='Fecha de adquisición')
    state_id = fields.Many2one('ztyres.it.state', string='Estado', tracking=True)
    notes = fields.Text(string='Observaciones')

    assignment_ids = fields.One2many('ztyres.it.assignment', 'mobile_id', string='Asignaciones')
    service_ids = fields.One2many('ztyres.it.service', 'mobile_id', string='Servicios')
    maintenance_ids = fields.One2many('ztyres.it.maintenance', 'mobile_id', string='Mantenimientos')

    assignment_count = fields.Integer(compute='_compute_counts')
    service_count = fields.Integer(compute='_compute_counts')
    maintenance_count = fields.Integer(compute='_compute_counts')

    @api.depends('assignment_ids', 'service_ids', 'maintenance_ids')
    def _compute_counts(self):
        for rec in self:
            rec.assignment_count = len(rec.assignment_ids)
            rec.service_count = len(rec.service_ids)
            rec.maintenance_count = len(rec.maintenance_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('inventory_number') or vals.get('inventory_number') == 'Nuevo':
                vals['inventory_number'] = self.env['ir.sequence'].next_by_code('ztyres.it.mobile') or 'Nuevo'
        return super().create(vals_list)

    def action_view_services(self):
        self.ensure_one()
        action = self.env.ref('ztyres_it_assets.action_it_service').read()[0]
        action['domain'] = [('mobile_id', '=', self.id)]
        action['context'] = {'default_mobile_id': self.id}
        return action

    def action_view_maintenances(self):
        self.ensure_one()
        action = self.env.ref('ztyres_it_assets.action_it_maintenance').read()[0]
        action['domain'] = [('mobile_id', '=', self.id)]
        action['context'] = {'default_mobile_id': self.id}
        return action

    def action_view_assignments(self):
        self.ensure_one()
        action = self.env.ref('ztyres_it_assets.action_it_assignment').read()[0]
        action['domain'] = [('mobile_id', '=', self.id)]
        action['context'] = {'default_mobile_id': self.id}
        return action
