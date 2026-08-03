# -*- coding: utf-8 -*-
"""
Tablas de tramos configurables.

Todas comparten la misma convención, que ahora es explícita:

    "Hasta" = 999999999 significa sin límite superior.

Antes se escribía 0 y había que saber que un 0 quería decir infinito.
Los registros viejos se normalizan en `init()` de cada tabla, y el
motor sigue tolerando el 0 para no romper datos a medio migrar.
"""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .ztyres_promo_config import UNLIMITED


class PolicyTierMixin(models.AbstractModel):
    """Comportamiento común de las tablas de tramos."""

    _name = 'ztyres_promo.policy_tier_mixin'
    _description = 'Comportamiento común de tramos de promoción'
    _order = 'lower_limit, id'

    lower_limit = fields.Integer(
        string='Desde',
        help='Acumulado mínimo para alcanzar este nivel.',
    )
    upper_limit = fields.Integer(
        string='Hasta',
        default=UNLIMITED,
        help=(
            'Acumulado máximo de este nivel. Use %s cuando el nivel no '
            'tenga tope.' % UNLIMITED
        ),
    )

    def _normalize_upper_limits(self, table_name):
        """Migra la convención vieja (0 = sin límite) a 999999999."""
        self.env.cr.execute(
            'UPDATE %s SET upper_limit = %%s '
            'WHERE upper_limit IS NULL OR upper_limit <= 0' % table_name,
            (UNLIMITED,),
        )

    @api.constrains('lower_limit', 'upper_limit')
    def _check_limits(self):
        for line in self:
            if line.lower_limit < 0:
                raise ValidationError(
                    _('El límite inferior no puede ser negativo.')
                )
            upper = line.upper_limit or UNLIMITED
            if upper < line.lower_limit:
                raise ValidationError(_(
                    'El límite superior debe ser mayor o igual que el '
                    'inferior. Use %s si el nivel no tiene tope.'
                ) % UNLIMITED)

    @api.onchange('upper_limit')
    def _onchange_upper_limit(self):
        """Nunca dejamos un tope en cero: cero se lee como infinito."""
        for line in self:
            if not line.upper_limit:
                line.upper_limit = UNLIMITED


class CurrentPolicyQuantity(models.Model):
    _name = 'ztyres_promo.current_policy_qty'
    _inherit = 'ztyres_promo.policy_tier_mixin'
    _description = 'Regla de descuento por cantidad'

    min_qty = fields.Integer(
        string='Cantidad mínima de llantas',
        help=(
            'Requisito adicional: piezas participantes mínimas para poder '
            'usar este nivel. Cero significa sin requisito.'
        ),
    )
    discount = fields.Float(string='Porcentaje de Descuento', digits=(16, 2))
    key_size_discount = fields.Float(
        string='% Key Sizes',
        digits=(16, 2),
        help=(
            'Porcentaje que cobran en este nivel los productos marcados '
            'como Key Size. Déjelo en cero si en este nivel cobran el '
            'mismo porcentaje que los demás.'
        ),
    )
    fixed_amount = fields.Float(string='Monto fijo en NC', digits=(16, 2))
    notas_credito_id = fields.Many2one(
        'ztyres_promo.notas_credito',
        ondelete='cascade',
    )

    def init(self):
        self._normalize_upper_limits('ztyres_promo_current_policy_qty')


class CurrentPolicyAmount(models.Model):
    _name = 'ztyres_promo.current_policy_amount'
    _inherit = 'ztyres_promo.policy_tier_mixin'
    _description = 'Regla de descuento por monto'

    min_qty = fields.Integer(
        string='Cantidad mínima de llantas',
        help=(
            'Requisito adicional: piezas participantes mínimas para poder '
            'usar este nivel. Cero significa sin requisito.'
        ),
    )
    discount = fields.Float(string='Porcentaje de Descuento', digits=(16, 2))
    key_size_discount = fields.Float(
        string='% Key Sizes',
        digits=(16, 2),
        help=(
            'Porcentaje que cobran en este nivel los productos marcados '
            'como Key Size. Déjelo en cero si en este nivel cobran el '
            'mismo porcentaje que los demás.'
        ),
    )
    fixed_amount = fields.Float(string='Monto fijo en NC', digits=(16, 2))
    notas_credito_id = fields.Many2one(
        'ztyres_promo.notas_credito',
        ondelete='cascade',
    )

    def init(self):
        self._normalize_upper_limits('ztyres_promo_current_policy_amount')


class CurrentPolicyRim(models.Model):
    _name = 'ztyres_promo.current_policy_rim'
    _inherit = 'ztyres_promo.policy_tier_mixin'
    _description = 'Regla de descuento por cantidad acumulada y rin'

    lower_limit = fields.Integer(
        string='Cantidad acumulada desde',
        required=True,
    )
    upper_limit = fields.Integer(
        string='Cantidad acumulada hasta',
        default=UNLIMITED,
        help='Use %s cuando el tramo no tenga límite superior.' % UNLIMITED,
    )
    rim_ids = fields.Many2many(
        'ztyres_products.rim',
        'ztyres_promo_policy_rim_rel',
        'policy_id',
        'rim_id',
        string='Rines',
        required=True,
    )
    discount = fields.Float(
        string='Porcentaje de Descuento',
        digits=(16, 2),
        required=True,
    )
    notas_credito_id = fields.Many2one(
        'ztyres_promo.notas_credito',
        required=True,
        ondelete='cascade',
    )

    def init(self):
        self._normalize_upper_limits('ztyres_promo_current_policy_rim')

    @api.constrains('lower_limit', 'upper_limit', 'rim_ids', 'discount')
    def _check_values(self):
        for line in self:
            if line.lower_limit <= 0:
                raise ValidationError(
                    _('La cantidad acumulada debe ser mayor que cero.')
                )
            if not line.rim_ids:
                raise ValidationError(
                    _('Seleccione al menos un rin para cada regla.')
                )
            if not 0 < line.discount <= 100:
                raise ValidationError(_(
                    'El descuento debe ser mayor que cero y no superar 100%.'
                ))

    @api.constrains('lower_limit', 'upper_limit', 'rim_ids', 'notas_credito_id')
    def _check_no_overlap(self):
        """Un mismo rin no puede estar en dos tramos que se traslapen.

        Si se traslapan, el porcentaje aplicado depende del orden en que
        se leen las reglas, que es justo el tipo de resultado que no se
        puede explicar al cliente.
        """
        for line in self:
            siblings = line.notas_credito_id.rim_policy_line_ids - line
            upper = line.upper_limit or UNLIMITED
            for other in siblings:
                other_upper = other.upper_limit or UNLIMITED
                overlaps = (
                    line.lower_limit <= other_upper
                    and other.lower_limit <= upper
                )
                shared = line.rim_ids & other.rim_ids
                if overlaps and shared:
                    raise ValidationError(_(
                        'Los rines %s aparecen en dos tramos que se '
                        'traslapan (%s-%s y %s-%s). Ajuste los rangos para '
                        'que cada rin tenga un solo porcentaje por tramo.'
                    ) % (
                        ', '.join(shared.mapped('display_name')),
                        line.lower_limit,
                        upper,
                        other.lower_limit,
                        other_upper,
                    ))


class CurrentPolicyCoupon(models.Model):
    _name = 'ztyres_promo.coupon'
    _description = 'Cupón por producto'

    product_id = fields.Many2one('product.template', string='Producto')
    amount = fields.Float(string='Monto')
    notas_credito_id = fields.Many2one(
        'ztyres_promo.notas_credito',
        ondelete='cascade',
    )

    @api.constrains('amount')
    def _check_amount(self):
        for coupon in self:
            if coupon.amount < 0:
                raise ValidationError(
                    _('El monto del cupón no puede ser negativo.')
                )


class PromotionMonthlyVolumeLine(models.Model):
    _name = 'ztyres_promo.monthly_volume_line'
    _inherit = 'ztyres_promo.policy_tier_mixin'
    _description = 'Regla de volumen mensual'

    lower_limit = fields.Integer(string='Límite Inferior', required=True)
    upper_limit = fields.Integer(
        string='Límite Superior',
        default=UNLIMITED,
        help='Use %s para indicar que no existe límite superior.' % UNLIMITED,
    )
    minimum_products = fields.Integer(
        string='Cantidad de Medidas',
        required=True,
    )
    minimum_qty_per_measure = fields.Integer(
        string='Mínimo por Medida',
        required=True,
    )
    discount = fields.Float(
        string='Porcentaje de Descuento',
        digits=(16, 2),
        required=True,
    )
    notas_credito_id = fields.Many2one(
        'ztyres_promo.notas_credito',
        required=True,
        ondelete='cascade',
    )

    def init(self):
        self._normalize_upper_limits('ztyres_promo_monthly_volume_line')

    @api.constrains(
        'lower_limit',
        'minimum_products',
        'minimum_qty_per_measure',
        'discount',
    )
    def _check_values(self):
        for line in self:
            if line.lower_limit <= 0:
                raise ValidationError(
                    _('El límite inferior debe ser mayor que cero.')
                )
            if line.minimum_products <= 0:
                raise ValidationError(
                    _('La cantidad de medidas debe ser mayor que cero.')
                )
            if line.minimum_qty_per_measure <= 0:
                raise ValidationError(
                    _('El mínimo por medida debe ser mayor que cero.')
                )
            if not 0 < line.discount <= 100:
                raise ValidationError(_(
                    'El descuento debe ser mayor que cero y no superar 100%.'
                ))
