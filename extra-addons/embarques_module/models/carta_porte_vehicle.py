from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class L10nMxEdiVehicle(models.Model):
    """Datos logísticos adicionales sobre el vehículo nativo de Carta Porte."""

    _inherit = 'l10n_mx_edi.vehicle'

    embarques_display_name = fields.Char(
        string='Nombre de la Unidad', index=True,
        help='Nombre corto y reconocible para identificar esta unidad en '
             'Embarques; por ejemplo: Unidad León 01.')

    embarques_capacidad_m3 = fields.Float(
        string='Capacidad útil para Embarques (m³)', digits=(16, 3),
        help='Capacidad física usada únicamente para estimar la ocupación.')

    def name_get(self):
        """Prioriza el alias logístico sin alterar la referencia fiscal."""
        native_names = dict(super().name_get())
        return [
            (vehicle.id,
             vehicle.embarques_display_name or native_names.get(
                 vehicle.id, vehicle.name or str(vehicle.id)))
            for vehicle in self
        ]

    @api.depends('embarques_display_name', 'name')
    def _compute_display_name(self):
        """Actualiza inmediatamente el nombre mostrado al editar el alias."""
        return super()._compute_display_name()

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Permite localizar unidades por alias o referencia de Carta Porte."""
        args = list(args or [])
        if not name:
            return super().name_search(
                name=name, args=args, operator=operator, limit=limit)
        vehicles = self.search([
            '|',
            ('embarques_display_name', operator, name),
            ('name', operator, name),
        ] + args, limit=limit)
        return vehicles.name_get()

    @api.constrains('embarques_capacidad_m3')
    def _check_embarques_logistics(self):
        for vehicle in self:
            if vehicle.embarques_capacidad_m3 < 0:
                raise ValidationError(_(
                    'La capacidad útil de %s no puede ser negativa.') %
                    vehicle.display_name)
