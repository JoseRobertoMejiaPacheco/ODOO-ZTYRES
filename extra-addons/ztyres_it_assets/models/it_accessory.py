from odoo import api, fields, models


class ItAccessory(models.Model):
    _name = 'ztyres.it.accessory'
    _description = 'Accesorio de TI'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Accesorio', required=True, tracking=True)
    inventory_number = fields.Char(
        string='Número de inventario',
        readonly=True,
        copy=False,
        default='Nuevo',
    )
    serial_number = fields.Char(string='Número de serie')
    type_id = fields.Many2one('ztyres.it.accessory.type', string='Tipo')
    brand_id = fields.Many2one('ztyres.it.brand', string='Marca')
    model = fields.Char(string='Modelo')
    acquisition_date = fields.Date(string='Fecha de adquisición')
    user_id = fields.Many2one('res.users', string='Usuario')
    equipment_id = fields.Many2one('ztyres.it.equipment', string='Equipo asignado')
    state_id = fields.Many2one('ztyres.it.state', string='Estado')
    notes = fields.Text(string='Observaciones')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('inventory_number') or vals.get('inventory_number') == 'Nuevo':
                vals['inventory_number'] = self.env['ir.sequence'].next_by_code('ztyres.it.accessory') or 'Nuevo'
        return super().create(vals_list)
