from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EmbarquesUnidad(models.Model):
    """Rango comercial usado para capacidad mínima y política.

    La cantidad de llantas del cliente se compara contra este rango. La unidad
    física se captura por separado y sólo aporta sus datos operativos y m³.
    """

    _name = 'embarques.unidad'
    _description = 'Rango de Llantas'
    _order = 'capacidad_llantas desc, id'

    name = fields.Char(
        string='Rango', compute='_compute_name', store=True, readonly=True)
    capacidad_llantas = fields.Integer(
        string='Cantidad de Llantas',
        required=True,
        help='Cantidad mínima de llantas requerida para que aplique el '
             'descuento de este rango.',
    )
    sequence = fields.Integer(string='Secuencia', default=10)
    active = fields.Boolean(string='Activo', default=True)

    @api.depends('capacidad_llantas')
    def _compute_name(self):
        for rec in self:
            rec.name = str(rec.capacidad_llantas) if rec.capacidad_llantas else ''

    @api.constrains('capacidad_llantas')
    def _check_capacidad(self):
        for rec in self:
            if rec.capacidad_llantas <= 0:
                raise ValidationError(
                    _('La capacidad de "%s" debe ser mayor a cero.') % rec.name)

    @api.constrains('capacidad_llantas', 'active')
    def _check_unique_active_range(self):
        for rec in self.filtered('active'):
            duplicate = self.search([
                ('id', '!=', rec.id), ('active', '=', True),
                ('capacidad_llantas', '=', rec.capacidad_llantas),
            ], limit=1)
            if duplicate:
                raise ValidationError(_(
                    'El rango "%s" duplica la cantidad de "%s".')
                    % (rec.name, duplicate.display_name))

    def name_get(self):
        return [
            (rec.id, str(rec.capacidad_llantas))
            for rec in self
        ]

    def write(self, vals):
        res = super().write(vals)
        # La capacidad en llantas es parte del cálculo. Al corregirla se
        # actualiza los embarques que evalúan este rango, sin botón manual.
        if 'capacidad_llantas' in vals:
            embarques = self.env['embarques.embarques'].search([])
            embarques.action_calculate_discount()
        return res
