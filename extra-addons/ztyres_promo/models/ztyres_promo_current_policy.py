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
    gift_card_amount = fields.Float(
        string='Promo ZT ($ con IVA)',
        digits=(16, 2),
        help=(
            'Valor de la tarjeta de regalo que se entrega al alcanzar este '
            'nivel. Solo se usa cuando el valor de la tarjeta es fijo por '
            'nivel; si el valor sale de la plantilla por código, esta '
            'columna se ignora y el nivel solo decide si el cliente '
            'califica.'
        ),
    )
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

    # Los límites heredados del mixin ('Desde' / 'Hasta') se capturan
    # CON IVA en esta tabla: es como el negocio expresa la meta
    # ("llegar a 35,000 facturados"). El motor los baja a subtotal al
    # comparar (ver reward_engine._tier_bounds), porque la NC se calcula
    # sobre el subtotal. Con IVA al 16%, un tope de 35,000 se alcanza
    # con 30,172.41 de subtotal.
    lower_limit = fields.Integer(
        string='Desde (con IVA)',
        help=(
            'Monto facturado mínimo, IVA incluido, para alcanzar este '
            'nivel. La nota de crédito se calcula sobre el subtotal, no '
            'sobre este monto.\n\n'
            'Capture aquí la meta tal como está escrita en el convenio, '
            'que normalmente ya viene facturada: "compra mínima de 50 mil '
            'al mes" se captura como 50000. Ojo con la palabra "netos" de '
            'los convenios: casi siempre significa neto de descuentos y '
            'devoluciones, NO sin IVA. Solo si la meta fuera realmente '
            'sin IVA habría que capturar el monto multiplicado por 1.16.'
        ),
    )
    upper_limit = fields.Integer(
        string='Hasta (con IVA)',
        default=UNLIMITED,
        help=(
            'Monto facturado máximo de este nivel, IVA incluido. Use %s '
            'cuando el nivel no tenga tope.' % UNLIMITED
        ),
    )

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
    # Campos legacy conservados para que una actualización no pierda datos.
    # La política amount_rim nueva usa rim_discount_ids; estos ya no se
    # muestran ni intervienen cuando hay rangos configurados.
    r14_r16_discount = fields.Float(string='% R14-R16 (legacy)', digits=(16, 2))
    r17_plus_discount = fields.Float(string='% R17+ (legacy)', digits=(16, 2))
    rim_discount_ids = fields.One2many(
        'ztyres_promo.amount_rim_discount', 'tier_id',
        string='Porcentajes por rango de RIN', copy=True,
    )
    fixed_amount = fields.Float(
        string='Monto fijo en NC ($ con IVA)',
        digits=(16, 2),
        help=(
            'Se captura con IVA. Al generar la nota de crédito se le baja '
            'el IVA, porque el timbrado vuelve a sumarlo: capturar 1,160 '
            'entrega 1,160 al cliente, no 1,345.60.'
        ),
    )
    gift_card_amount = fields.Float(
        string='Promo ZT ($ con IVA)',
        digits=(16, 2),
        help=(
            'Valor fijo de la tarjeta de regalo que se entrega al alcanzar '
            'este nivel, sin importar cuántas piezas se compraron. Se '
            'entrega tal cual se captura.\n\n'
            'Solo se usa cuando el origen del valor es "Valor fijo del '
            'nivel alcanzado". Si el valor sale de la plantilla por '
            'código, esta columna se ignora: el nivel únicamente decide '
            'si el cliente califica.'
        ),
    )
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
    amount = fields.Float(
        string='Monto ($ con IVA)',
        help=(
            'Se captura con IVA, como se le promete al cliente. Al generar '
            'la nota de crédito se le baja el IVA, porque el timbrado '
            'vuelve a sumarlo.'
        ),
    )
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


class GiftCardProductAmount(models.Model):
    """Valor de tarjeta de regalo por código de producto ("Promo ZT").

    Es la tabla que se carga con la plantilla de Excel. Se parece a
    `ztyres_promo.coupon` —código y monto por pieza— pero no es lo
    mismo y por eso vive aparte:

    - El cupón ES la promoción: define el alcance y paga siempre que se
      venda el producto. Aquí el alcance lo define la promoción como
      cualquier otra (marcas, características, lista de códigos) y esta
      tabla solo dice cuánto vale cada código.
    - El cupón siempre genera nota de crédito. Esto normalmente no:
      se entrega como tarjeta.
    - El cupón tiene tope de piezas por producto. Aquí no hay tope: si
      compró 10 llantas de un código de $5, son $50.

    Mezclarlas en un solo modelo obligaba a que un mismo registro
    significara dos cosas según un flag, que es justo como se llega a
    pagar dos veces el mismo beneficio.
    """

    _name = 'ztyres_promo.gift_card'
    _description = 'Valor de tarjeta de regalo por producto (Promo ZT)'
    _order = 'product_id, id'

    product_id = fields.Many2one(
        'product.template',
        string='Producto',
        required=True,
        ondelete='cascade',
    )
    amount = fields.Float(
        string='Monto por pieza ($ con IVA)',
        digits=(16, 2),
        help=(
            'Valor de tarjeta por CADA pieza vendida de este código, tal '
            'como aparece en la columna Promo ZT. Si dice 5 y el cliente '
            'compra 10 llantas, la tarjeta es de 50.'
        ),
    )
    notas_credito_id = fields.Many2one(
        'ztyres_promo.notas_credito',
        string='Promoción',
        required=True,
        ondelete='cascade',
        index=True,
    )

    _sql_constraints = [
        (
            'product_promo_uniq',
            'unique(product_id, notas_credito_id)',
            'Un código solo puede tener un valor de Promo ZT por '
            'promoción. Corrija el archivo: hay un código repetido.',
        ),
    ]

    @api.constrains('amount')
    def _check_amount(self):
        for card in self:
            if card.amount < 0:
                raise ValidationError(
                    _('El monto de la tarjeta de regalo no puede ser negativo.')
                )


class PromotionPmsPrice(models.Model):
    """Precio PMS por código: la base sobre la que se paga el porcentaje.

    Es la tercera tabla "código + número" del módulo, y otra vez no es
    ninguna de las otras dos. La diferencia está en qué papel juega el
    número:

    - `ztyres_promo.coupon`    -> el número ES la NC por pieza.
    - `ztyres_promo.gift_card` -> el número ES el valor de tarjeta por pieza.
    - aquí                     -> el número es un PRECIO. No se entrega
      nada por él: se multiplica por las piezas para formar la base y
      sobre esa base se aplica el porcentaje del nivel.

    Por eso el importe de un cupón se captura siempre con IVA y este no
    necesariamente: un cupón es dinero prometido, un PMS es un precio de
    lista, y las listas de las marcas circulan de las dos formas. Cómo
    viene capturado se dice UNA vez por promoción, en
    `pms_price_taxed`, y no código por código: un archivo mezclado no
    existe en la práctica y ofrecer la opción por renglón solo invita a
    equivocarse.
    """

    _name = 'ztyres_promo.pms_price'
    _description = 'Precio PMS por producto (base de cálculo de la promoción)'
    _order = 'product_id, id'

    product_id = fields.Many2one(
        'product.template',
        string='Producto',
        required=True,
        ondelete='cascade',
    )
    price = fields.Float(
        string='Precio PMS',
        digits='Product Price',
        help=(
            'Precio de referencia por UNA pieza de este código. La nota '
            'de crédito se calcula como precio x piezas x porcentaje del '
            'nivel, sin mirar a qué precio se facturó realmente.\n\n'
            'Si viene con IVA o sin IVA se indica en la promoción, en '
            '"El precio PMS se captura".'
        ),
    )
    notas_credito_id = fields.Many2one(
        'ztyres_promo.notas_credito',
        string='Promoción',
        required=True,
        ondelete='cascade',
        index=True,
    )

    _sql_constraints = [
        (
            'product_promo_uniq',
            'unique(product_id, notas_credito_id)',
            'Un código solo puede tener un precio PMS por promoción. '
            'Corrija el archivo: hay un código repetido.',
        ),
    ]

    @api.constrains('price')
    def _check_price(self):
        for record in self:
            if record.price < 0:
                raise ValidationError(
                    _('El precio PMS no puede ser negativo.')
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


class AmountRimDiscount(models.Model):
    _name = 'ztyres_promo.amount_rim_discount'
    _description = 'Porcentaje por rango de RIN y tramo de monto'
    _order = 'rim_from, rim_to, id'

    tier_id = fields.Many2one(
        'ztyres_promo.current_policy_amount', required=True, ondelete='cascade',
        index=True, string='Tramo de monto',
    )
    rim_from = fields.Integer(string='RIN desde', required=True)
    rim_to = fields.Integer(
        string='RIN hasta', required=True, default=99,
        help='Use 99 para representar R17+, R20+, etc.',
    )
    discount = fields.Float(string='Descuento (%)', required=True, digits=(16, 2))
    key_size_discount = fields.Float(
        string='Key Size (%)', related='tier_id.key_size_discount',
        readonly=False, digits=(16, 2),
        help='Porcentaje Key Size del tramo. Es el mismo valor del nivel de monto.',
    )

    def name_get(self):
        result = []
        for rec in self:
            end = '+' if rec.rim_to >= 99 else str(rec.rim_to)
            result.append((rec.id, 'R%s-%s: %s%%' % (rec.rim_from, end, rec.discount)))
        return result

    @api.constrains('rim_from', 'rim_to', 'discount')
    def _check_values(self):
        for rec in self:
            if rec.rim_from <= 0 or rec.rim_to < rec.rim_from:
                raise ValidationError(_('El rango de RIN no es válido.'))
            if rec.discount < 0 or rec.discount > 100:
                raise ValidationError(_('El descuento debe estar entre 0 y 100.'))

    @api.constrains('rim_from', 'rim_to', 'tier_id')
    def _check_overlap(self):
        for rec in self:
            overlap = self.search_count([
                ('id', '!=', rec.id), ('tier_id', '=', rec.tier_id.id),
                ('rim_from', '<=', rec.rim_to), ('rim_to', '>=', rec.rim_from),
            ])
            if overlap:
                raise ValidationError(_('Los rangos de RIN del mismo tramo no pueden traslaparse.'))
