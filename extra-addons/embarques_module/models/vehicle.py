from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EmbarquesVehicle(models.Model):
    """Unidad física usada por Embarques, propia o externa."""

    _name = 'embarques.vehicle'
    _description = 'Vehículo de Embarques'
    _order = 'name, id'

    name = fields.Char(string='Nombre', required=True, index=True)
    capacity_m3 = fields.Float(
        string='Cubicaje (m³)', required=True, digits=(16, 3),
        help='Capacidad útil utilizada para calcular la ocupación del embarque.')
    active = fields.Boolean(default=True)
    legacy_carta_porte_vehicle_id = fields.Many2one(
        'l10n_mx_edi.vehicle', string='Vehículo anterior de Carta Porte',
        readonly=True, copy=False, ondelete='set null')

    _sql_constraints = [
        ('legacy_carta_porte_vehicle_unique',
         'unique(legacy_carta_porte_vehicle_id)',
         'El vehículo anterior de Carta Porte ya fue migrado.'),
    ]

    @api.model
    def migrate_legacy_vehicles(self):
        """Conserva las unidades ya usadas al actualizar desde la versión anterior."""
        CartaVehicle = self.env['l10n_mx_edi.vehicle'].sudo()
        old_vehicles = CartaVehicle.search([
            ('embarques_capacidad_m3', '>', 0),
        ])
        for old in old_vehicles:
            vehicle = self.sudo().search([
                ('legacy_carta_porte_vehicle_id', '=', old.id),
            ], limit=1)
            if not vehicle:
                vehicle = self.sudo().create({
                    'name': old.embarques_display_name or old.display_name,
                    'capacity_m3': old.embarques_capacidad_m3,
                    'legacy_carta_porte_vehicle_id': old.id,
                })
            self.env.cr.execute(
                """
                UPDATE embarques_embarques
                   SET vehicle_id = %s
                 WHERE vehicle_id IS NULL
                   AND carta_porte_vehicle_id = %s
                """,
                (vehicle.id, old.id),
            )
        return True

    @api.constrains('capacity_m3')
    def _check_capacity_m3(self):
        for vehicle in self:
            if vehicle.capacity_m3 <= 0:
                raise ValidationError(_(
                    'El cubicaje del vehículo "%s" debe ser mayor que cero.') %
                    vehicle.display_name)
