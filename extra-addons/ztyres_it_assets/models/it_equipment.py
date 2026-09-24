from odoo import api, fields, models


class ItEquipment(models.Model):
    _name = 'ztyres.it.equipment'
    _description = 'Equipo de TI'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Nombre del equipo', required=True, tracking=True)
    inventory_number = fields.Char(
        string='Número de inventario',
        readonly=True,
        copy=False,
        default=lambda self: 'Nuevo',
    )
    serial_number = fields.Char(string='Número de serie', tracking=True)
    active = fields.Boolean(default=True)

    user_id = fields.Many2one('res.users', string='Usuario asignado', tracking=True)
    employee_name = fields.Char(string='Nombre del usuario', related='user_id.name', store=True)
    area = fields.Char(string='Área', tracking=True)
    position = fields.Char(string='Puesto', tracking=True)

    equipment_type = fields.Selection([
        ('laptop', 'Laptop'),
        ('desktop', 'Escritorio'),
    ], string='Tipo de equipo', default='laptop', required=True, tracking=True)

    brand_id = fields.Many2one('ztyres.it.brand', string='Marca')
    model = fields.Char(string='Modelo')
    acquisition_date = fields.Date(string='Fecha de adquisición')
    acquisition_year = fields.Integer(string='Año de adquisición')

    processor = fields.Char(string='Procesador')
    ram = fields.Char(string='RAM')
    storage = fields.Char(string='Almacenamiento')
    disk_type = fields.Selection([
        ('hdd', 'HDD'),
        ('ssd', 'SSD'),
        ('nvme', 'NVMe'),
        ('hybrid', 'Híbrido'),
        ('other', 'Otro'),
    ], string='Tipo de disco')

    operating_system = fields.Char(string='Sistema operativo')
    os_version = fields.Char(string='Versión')

    state_id = fields.Many2one('ztyres.it.state', string='Estado', tracking=True)

    battery_state = fields.Selection([
        ('good', 'Buena'),
        ('regular', 'Regular'),
        ('bad', 'Mala'),
        ('replace', 'Requiere cambio'),
        ('na', 'No aplica'),
    ], string='Estado de batería', default='na')

    battery_health = fields.Integer(string='Salud de batería (%)')
    battery_cycles = fields.Integer(string='Ciclos de batería')

    mac_address = fields.Char(string='MAC')
    hostname = fields.Char(string='Hostname')
    ip_address = fields.Char(string='IP')

    notes = fields.Text(string='Observaciones')

    program_ids = fields.Many2many(
        'ztyres.it.program',
        'ztyres_it_equipment_program_rel',
        'equipment_id',
        'program_id',
        string='Programas / Sistemas',
    )

    accessory_ids = fields.One2many(
        'ztyres.it.accessory', 'equipment_id', string='Accesorios'
    )
    assignment_ids = fields.One2many(
        'ztyres.it.assignment', 'equipment_id', string='Asignaciones'
    )
    service_ids = fields.One2many(
        'ztyres.it.service', 'equipment_id', string='Servicios'
    )
    maintenance_ids = fields.One2many(
        'ztyres.it.maintenance', 'equipment_id', string='Mantenimientos'
    )

    service_count = fields.Integer(compute='_compute_counts')
    maintenance_count = fields.Integer(compute='_compute_counts')
    accessory_count = fields.Integer(compute='_compute_counts')
    assignment_count = fields.Integer(compute='_compute_counts')

    @api.depends('service_ids', 'maintenance_ids', 'accessory_ids', 'assignment_ids')
    def _compute_counts(self):
        for rec in self:
            rec.service_count = len(rec.service_ids)
            rec.maintenance_count = len(rec.maintenance_ids)
            rec.accessory_count = len(rec.accessory_ids)
            rec.assignment_count = len(rec.assignment_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('inventory_number') or vals.get('inventory_number') == 'Nuevo':
                vals['inventory_number'] = self.env['ir.sequence'].next_by_code('ztyres.it.equipment') or 'Nuevo'
        return super().create(vals_list)

    def action_view_services(self):
        self.ensure_one()
        action = self.env.ref('ztyres_it_assets.action_it_service').read()[0]
        action['domain'] = [('equipment_id', '=', self.id)]
        action['context'] = {'default_equipment_id': self.id}
        return action

    def action_view_maintenances(self):
        self.ensure_one()
        action = self.env.ref('ztyres_it_assets.action_it_maintenance').read()[0]
        action['domain'] = [('equipment_id', '=', self.id)]
        action['context'] = {'default_equipment_id': self.id}
        return action

    def action_view_accessories(self):
        self.ensure_one()
        action = self.env.ref('ztyres_it_assets.action_it_accessory').read()[0]
        action['domain'] = [('equipment_id', '=', self.id)]
        action['context'] = {'default_equipment_id': self.id}
        return action

    def action_view_assignments(self):
        self.ensure_one()
        action = self.env.ref('ztyres_it_assets.action_it_assignment').read()[0]
        action['domain'] = [('equipment_id', '=', self.id)]
        action['context'] = {'default_equipment_id': self.id}
        return action

    def _get_current_assignment(self):
        """Asignación vigente (sin fecha de fin) o, si no hay, la más reciente."""
        self.ensure_one()
        assignments = self.assignment_ids  # ordenadas por date_from desc, id desc
        return (assignments.filtered(lambda a: not a.date_to) or assignments)[:1]

    def action_print_resguardo(self):
        """Descarga el formato Z-FO-TI-01 (Excel) lleno para este equipo."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/ztyres_it_assets/resguardo/equipment/%d' % self.id,
            'target': 'self',
        }
