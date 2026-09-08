from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EmbarquesDiscountPolicy(models.Model):
    """Opción seleccionable Rango → Descuento, sin cabeceras intermedias."""

    _name = 'embarques.discount.policy'
    _description = 'Opción de Descuento Logístico'
    _order = 'capacity desc, percentage desc, id'

    name = fields.Char(
        string='Opción', compute='_compute_name', store=True, index=True)
    unidad_id = fields.Many2one(
        'embarques.unidad', string='Rango', required=True,
        ondelete='restrict', index=True)
    capacity = fields.Integer(
        related='unidad_id.capacidad_llantas', store=True, readonly=True)
    percentage = fields.Float(
        string='Descuento (%)', required=True, digits=(16, 2))
    zona_ids = fields.Many2many(
        'embarques.zona', 'embarques_policy_zona_rel',
        'policy_id', 'zona_id', string='Zonas de referencia')
    destination_count = fields.Integer(
        string='Destinos', compute='_compute_destination_count')
    seed_code = fields.Char(string='Clave de plantilla', index=True, copy=False)
    company_id = fields.Many2one(
        'res.company', string='Compañía', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('range_percentage_company_uniq',
         'UNIQUE(unidad_id, percentage, company_id)',
         'Ya existe esta combinación de rango y descuento para la compañía.'),
        ('percentage_range',
         'CHECK (percentage >= 0 AND percentage <= 100)',
         'El porcentaje debe estar entre 0 y 100.'),
    ]

    def init(self):
        """Archiva cabeceras de la versión anterior, que no tenían rango."""
        self.env.cr.execute("""
            SELECT 1 FROM information_schema.columns
             WHERE table_name = 'embarques_discount_policy'
               AND column_name = 'unidad_id'
        """)
        if self.env.cr.fetchone():
            self.env.cr.execute("""
                UPDATE embarques_discount_policy
                   SET active = FALSE
                 WHERE unidad_id IS NULL
            """)

    @api.depends('unidad_id.capacidad_llantas', 'percentage')
    def _compute_name(self):
        for rec in self:
            rec.name = (
                '%s → %g%%' % (rec.capacity, rec.percentage)
                if rec.unidad_id else False)

    def _compute_destination_count(self):
        Destination = self.env['embarques.destino']
        for rec in self:
            rec.destination_count = Destination.search_count([
                ('discount_policy_ids', 'in', rec.id), ('active', '=', True),
            ])

    @api.constrains('percentage')
    def _check_percentage(self):
        for rec in self:
            if not 0 <= rec.percentage <= 100:
                raise ValidationError(
                    _('El porcentaje debe estar entre 0 y 100.'))

    @api.constrains('unidad_id', 'percentage', 'company_id', 'active')
    def _check_duplicate_option(self):
        for rec in self.filtered('active'):
            duplicate = self.search_count([
                ('id', '!=', rec.id),
                ('unidad_id', '=', rec.unidad_id.id),
                ('percentage', '=', rec.percentage),
                ('company_id', '=', rec.company_id.id),
                ('active', '=', True),
            ])
            if duplicate:
                raise ValidationError(_(
                    'Ya existe la opción %s → %g%%.') % (
                        rec.capacity, rec.percentage))
