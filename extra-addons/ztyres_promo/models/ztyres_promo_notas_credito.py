# -*- coding: utf-8 -*-
"""
Modelo principal `ztyres_promo.notas_credito`.

Aquí viven los campos y las acciones simples de interfaz. La lógica
pesada se reparte en archivos que extienden este mismo modelo por
`_inherit` (mismo `_name`, misma tabla):

- ztyres_promo_config.py        -> vocabulario del dominio (alcance/política)
- ztyres_promo_reward_engine.py -> tramos, rines, cupones, volumen mensual
- ..._domain.py                 -> alcance -> dominio de búsqueda
- ..._calculo.py                -> orquestación del cálculo histórico
- ..._facturacion.py            -> creación de NC y estatus SAT
- ..._zip.py                    -> descarga de XMLs
- ..._eval.py                   -> evaluación en vivo sobre un documento

Los dos ejes del dominio, que antes estaban revueltos:

    promo_conditions  = ALCANCE   -> qué productos participan
    promo_type        = POLÍTICA  -> cómo se calcula el beneficio

Ninguno de los dos puede hacer el trabajo del otro.
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .ztyres_promo_config import (
    ALLOWED_POLICIES_BY_SCOPE,
    DEFAULT_COUPON_LIMIT_QTY,
    FEATURE_SCOPES,
    FORCED_POLICY_BY_SCOPE,
    POLICY_AMOUNT,
    POLICY_COUPONS,
    POLICY_MONTHLY_VOLUME,
    POLICY_QUANTITY,
    POLICY_RIM_QUANTITY,
    POLICY_SELECTION,
    REWARD_FIXED_AMOUNT,
    REWARD_PERCENTAGE,
    REWARD_SELECTION,
    SCOPE_ATTRIBUTE_COMBINATION,
    SCOPE_COUPONS,
    SCOPE_RIM_POLICY,
    SCOPE_SELECTION,
    SCOPE_SPECIFIC_PRODUCTS,
    SCOPE_TIRE_FEATURE,
    TIER_POLICIES,
    UNLIMITED,
)


class ZtyresVolumen(models.Model):
    _name = 'ztyres_promo.notas_credito'
    _rec_name = 'nombre'
    _description = 'Promoción y cálculo de notas de crédito'
    _order = 'start_date desc, id desc'

    # ------------------------------------------------------------------
    # Encabezado
    # ------------------------------------------------------------------
    nombre = fields.Char(string='Nombre')
    start_date = fields.Date(string='Fecha Inicio')
    end_date = fields.Date(string='Fecha Fin')
    status = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('approve_p', 'Promoción Aprobada'),
            ('approve', 'NC Aprobadas'),
            ('done', 'Confirmado'),
            ('cancel', 'Cancelado'),
        ],
        string='Estado',
        default='draft',
    )

    # ------------------------------------------------------------------
    # EJE 1 - ALCANCE: qué productos participan
    # ------------------------------------------------------------------
    promo_conditions = fields.Selection(
        string='Alcance de Productos',
        selection=SCOPE_SELECTION,
        help=(
            'Define QUÉ productos participan. No define cuánto se otorga.\n'
            '- Característica de Llanta: basta cumplir UNA de las '
            'características marcadas (OR).\n'
            '- Combinación de Características: debe cumplir TODAS las '
            'características marcadas (AND, mínimo dos).\n'
            '- Productos / Códigos Específicos: solo la lista cargada.\n'
            '- Cupones por Producto: solo los productos de la pestaña '
            'Cupones.\n'
            '- Rines de las Políticas: heredado; participan los rines '
            'listados en la tabla de políticas por rin.'
        ),
    )

    brand_ids = fields.Many2many('ztyres_products.brand', 'product_brand_rel', 'product_id', 'brand_id', string='Marcas')
    tier_ids = fields.Many2many('ztyres_products.tier', 'product_tier_rel', 'product_id', 'tier_id', string='Tiers')
    measure_ids = fields.Many2many('ztyres_products.tire_measure', 'product_measure_rel', 'product_id', 'measure_id', string='Medidas')
    segment_ids = fields.Many2many('ztyres_products.segment', 'product_segment_rel', 'product_id', 'segment_id', string='Segmentos')
    rin_ids = fields.Many2many('ztyres_products.rim', 'product_rim_rel', 'product_id', 'rim_id', string='Rines')
    face_ids = fields.Many2many('ztyres_products.face', 'product_face_rel', 'product_id', 'face_id', string='Caras')
    layer_ids = fields.Many2many('ztyres_products.layer', 'product_layer_rel', 'product_id', 'layer_id', string='Capas')
    model_ids = fields.Many2many('ztyres_products.model', 'product_model_rel', 'product_id', 'model_id', string='Modelos')
    product_ids = fields.Many2many('product.template', string='Productos')
    price_list_ids = fields.Many2many('product.pricelist', string='Listas de Precios')
    not_found = fields.Text(string='Códigos no encontrados')

    # ------------------------------------------------------------------
    # EJE 2 - POLÍTICA: cómo se calcula el beneficio
    # ------------------------------------------------------------------
    promo_type = fields.Selection(
        string='Tipo de Política',
        selection=POLICY_SELECTION,
        help=(
            'Define CÓMO se calcula el beneficio sobre los productos que '
            'ya entraron por el alcance. Nunca agrega ni quita productos.'
        ),
    )
    reward_type = fields.Selection(
        string='Tipo de Beneficio',
        selection=REWARD_SELECTION,
        default=REWARD_PERCENTAGE,
        required=True,
        help=(
            'Para políticas por Cantidad o Monto, define si cada nivel '
            'otorga un porcentaje sobre el subtotal o un monto fijo de NC.'
        ),
    )

    policy_line_qty_ids = fields.One2many(
        comodel_name='ztyres_promo.current_policy_qty',
        inverse_name='notas_credito_id',
        string='Políticas de Cantidad',
    )
    policy_line_amount_ids = fields.One2many(
        comodel_name='ztyres_promo.current_policy_amount',
        inverse_name='notas_credito_id',
        string='Políticas de Monto',
    )
    monthly_volume_line_ids = fields.One2many(
        comodel_name='ztyres_promo.monthly_volume_line',
        inverse_name='notas_credito_id',
        string='Políticas de Volumen Mensual',
    )
    rim_policy_line_ids = fields.One2many(
        comodel_name='ztyres_promo.current_policy_rim',
        inverse_name='notas_credito_id',
        string='Políticas por Rin',
    )
    key_size_product_ids = fields.Many2many(
        'product.template',
        'ztyres_promo_key_size_product_rel',
        'notas_credito_id',
        'product_id',
        string='Key Sizes',
        help=(
            'Productos que cobran el porcentaje de la columna "% Key Sizes" '
            'de la tabla de niveles, en lugar del porcentaje general. '
            'Siguen sumando al acumulado como cualquier otra llanta.'
        ),
    )
    coupon_ids = fields.One2many(
        'ztyres_promo.coupon',
        'notas_credito_id',
        string='Cupones',
    )
    coupon_limit_qty = fields.Integer(
        string='Tope de piezas por producto (cupones)',
        default=DEFAULT_COUPON_LIMIT_QTY,
        help=(
            'Máximo de piezas bonificadas por producto y por cliente en '
            'promociones de cupones. El tope se aplica sobre el total del '
            'cliente, no por RFC, para que un cliente con RFC fiscal y '
            'genérico no lo duplique.'
        ),
    )

    # Topes informativos heredados. No intervienen en el cálculo.
    limite_qty = fields.Integer(string='Límite Cantidad (informativo)')
    limite_amount = fields.Integer(string='Límite Monto (informativo)')

    # ------------------------------------------------------------------
    # Reglas de aplicación
    # ------------------------------------------------------------------
    apply_on_groups = fields.Selection(
        string='Aplican Grupos',
        selection=[('si', 'Sí'), ('no', 'No')],
        default='no',
        help=(
            'Sí: el tramo se determina con el acumulado de todo el grupo '
            'de clientes y luego se reparte entre sus integrantes.'
        ),
    )
    apply_volume = fields.Selection(
        string='Aplicar por cantidad global',
        selection=[('si', 'Sí'), ('no', 'No')],
        default='no',
        help=(
            'Sí: para elegir el tramo se cuentan TODAS las llantas '
            'facturadas al cliente en el periodo, participen o no en la '
            'promoción. El beneficio se sigue pagando solo sobre lo que '
            'participa.'
        ),
    )
    generic_edi = fields.Selection(
        string='Incluir RFC Genérico (Mostrador)',
        selection=[('si', 'Sí'), ('no', 'No')],
        default='no',
    )
    excluded_partner_ids = fields.Many2many('res.partner', string='Clientes Excluidos')
    excluded_invoice_ids = fields.Many2many('account.move', string='Facturas Excluidas')
    excluded_invoice_ids_domain = fields.Char(
        compute='_compute_excluded_invoice_ids_domain',
        readonly=True,
        store=False,
    )

    # ------------------------------------------------------------------
    # Presentación
    # ------------------------------------------------------------------
    promo_display_mode = fields.Selection(
        string='Visualización de Promoción Ganada',
        selection=[
            ('none', 'No Mostrar'),
            ('global', 'Global'),
            ('product', 'Por Producto'),
            ('both', 'Ambas'),
        ],
        default='none',
        help=(
            "Cómo se muestra el texto de 'Promoción Ganada' en la "
            "cotización/orden/factura: 'No Mostrar' no aparece en "
            "ningún lado (ni en la cotización, ni en la factura, ni "
            "en sus PDF; es la opción por defecto); 'Global' solo el "
            "total ganado por la promoción; 'Por Producto' el "
            "desglose línea por línea; 'Ambas' muestra las dos cosas."
        ),
    )
    promo_ganada_message = fields.Char(
        string='Observaciones',
        default='¡Ganaste {monto} en NC por la promoción "{promocion}"!',
        help=(
            "Texto que se muestra en la cotización/orden/factura cuando "
            "esta promoción aplica (parte 'Global' de la visualización). "
            "Se puede usar texto libre y los siguientes marcadores, que "
            "se reemplazan automáticamente:\n"
            "{promocion} - nombre de la promoción\n"
            "{monto} - monto ganado en NC, ya formateado como moneda\n"
            "{porcentaje} - porcentaje de descuento, ej. '8.00%' "
            "(vacío en promociones de tipo Cupones, que no tienen %)"
        ),
    )
    promo_explanation = fields.Html(
        string='Qué va a hacer esta promoción',
        compute='_compute_promo_explanation',
        help='Lectura en español de la configuración actual, antes de calcular.',
    )
    config_warning = fields.Text(
        string='Avisos de configuración',
        compute='_compute_promo_explanation',
    )

    # ------------------------------------------------------------------
    # Resultados
    # ------------------------------------------------------------------
    # Sin `domain` en el campo: si el One2many filtra por total_nc_untaxed,
    # el propio cálculo deja de ver las líneas en cero y nunca les aplica
    # el beneficio de grupo. El filtro se hace en la vista.
    line_ids = fields.One2many(
        'ztyres_promo.notas_credito_lines',
        'definitive_nc_id',
        string='Notas de Crédito Definitivas',
        domain=[('total_nc_untaxed', '>', 0)]
    )
    detailed_line_ids = fields.One2many(
        'ztyres_promo.lines',
        'definitive_nc_id',
        string='Detalle',
    )
    missing_partner_vat_warning = fields.Text(
        string='Documentos sin RFC receptor',
        readonly=True,
        copy=False,
    )
    count_line_ids = fields.Integer(
        string='Count Notas de Crédito',
        compute='_compute_count_line_ids',
    )
    count_detailed_line_ids = fields.Integer(
        string='Count Detalle',
        compute='_compute_count_detailed_line_ids',
    )

    # ==================================================================
    # Migración de datos heredados
    # ==================================================================
    def init(self):
        """Normaliza registros creados con el diseño anterior."""
        # Cupones se guardaban como política y no como alcance.
        self.env.cr.execute("""
            UPDATE ztyres_promo_notas_credito
               SET promo_conditions = 'coupons'
             WHERE promo_type = 'coupons'
               AND (promo_conditions IS NULL OR promo_conditions = '')
        """)
        # El alcance heredado 'rim_quantity' siempre implica esa política.
        self.env.cr.execute("""
            UPDATE ztyres_promo_notas_credito
               SET promo_type = 'rim_quantity'
             WHERE promo_conditions = 'rim_quantity'
               AND (promo_type IS NULL OR promo_type = '')
        """)
        self.env.cr.execute("""
            UPDATE ztyres_promo_notas_credito
               SET coupon_limit_qty = %s
             WHERE coupon_limit_qty IS NULL OR coupon_limit_qty <= 0
        """, (DEFAULT_COUPON_LIMIT_QTY,))

    # ==================================================================
    # Lectura del dominio
    # ==================================================================
    def _get_scope(self):
        """Alcance efectivo, incluyendo la inferencia para datos viejos."""
        self.ensure_one()
        if self.promo_conditions:
            return self.promo_conditions
        # Promociones antiguas importadas por Excel sin alcance explícito.
        if self.product_ids:
            return SCOPE_SPECIFIC_PRODUCTS
        return False

    def _get_policy(self):
        """Política efectiva, respetando los alcances que la determinan."""
        self.ensure_one()
        forced = FORCED_POLICY_BY_SCOPE.get(self._get_scope())
        return forced or self.promo_type

    def _is_coupon_promotion(self):
        self.ensure_one()
        return (
            self._get_scope() == SCOPE_COUPONS
            or self.promo_type == POLICY_COUPONS
        )

    def _is_rim_quantity_promotion(self):
        self.ensure_one()
        return self._get_policy() == POLICY_RIM_QUANTITY

    def _has_key_sizes(self):
        """¿Hay productos Key Size con un porcentaje propio que aplicar?

        Hacen falta las dos cosas: la lista de productos y al menos un
        nivel con la columna "% Key Sizes" distinta de cero. Si falta
        cualquiera de las dos, todo cobra el porcentaje general y el
        cálculo sigue el camino de siempre.

        Solo tienen sentido sobre las tablas de tramos (Cantidad/Monto)
        y cuando el beneficio es un porcentaje: un monto fijo por nivel
        no se puede diferenciar por producto.
        """
        self.ensure_one()
        if not self.key_size_product_ids:
            return False
        if self._get_policy() not in TIER_POLICIES:
            return False
        if self._effective_reward_type() != REWARD_PERCENTAGE:
            return False
        return any(
            line.key_size_discount > 0
            for line in self._active_policy_lines()
        )

    def _uses_amount_policy(self):
        self.ensure_one()
        return self._get_policy() == POLICY_AMOUNT

    def _uses_feature_scope(self):
        self.ensure_one()
        return self._get_scope() in FEATURE_SCOPES

    def _effective_reward_type(self):
        """El tipo de beneficio configurable solo existe en tramos."""
        self.ensure_one()
        if self._get_policy() in TIER_POLICIES:
            return self.reward_type
        return REWARD_PERCENTAGE

    def _active_policy_lines(self):
        """Tabla de tramos de la política vigente."""
        self.ensure_one()
        policy = self._get_policy()
        if policy == POLICY_QUANTITY:
            return self.policy_line_qty_ids
        if policy == POLICY_AMOUNT:
            return self.policy_line_amount_ids
        if policy == POLICY_MONTHLY_VOLUME:
            return self.monthly_volume_line_ids
        if policy == POLICY_RIM_QUANTITY:
            return self.rim_policy_line_ids
        return self.env['ztyres_promo.current_policy_qty']

    # ==================================================================
    # Coherencia alcance / política
    # ==================================================================
    @api.constrains('promo_conditions', 'promo_type')
    def _check_scope_policy_combination(self):
        for promotion in self:
            scope = promotion.promo_conditions
            if not scope or not promotion.promo_type:
                continue
            allowed = ALLOWED_POLICIES_BY_SCOPE.get(scope)
            if allowed and promotion.promo_type not in allowed:
                labels = dict(POLICY_SELECTION)
                raise ValidationError(_(
                    'El alcance "%(scope)s" no admite la política '
                    '"%(policy)s". Políticas válidas: %(allowed)s.'
                ) % {
                    'scope': dict(SCOPE_SELECTION).get(scope, scope),
                    'policy': labels.get(
                        promotion.promo_type,
                        promotion.promo_type,
                    ),
                    'allowed': ', '.join(
                        labels.get(item, item) for item in allowed
                    ),
                })

    @api.onchange('promo_conditions')
    def _onchange_promo_conditions(self):
        """Al cambiar el alcance, ajusta la política si dejó de ser válida."""
        for promotion in self:
            scope = promotion.promo_conditions
            forced = FORCED_POLICY_BY_SCOPE.get(scope)
            if forced:
                promotion.promo_type = forced
                continue
            allowed = ALLOWED_POLICIES_BY_SCOPE.get(scope)
            if allowed and promotion.promo_type not in allowed:
                promotion.promo_type = False

    @api.model
    def _sync_forced_policy(self, values):
        scope = values.get('promo_conditions')
        if scope in FORCED_POLICY_BY_SCOPE:
            values['promo_type'] = FORCED_POLICY_BY_SCOPE[scope]
        return values

    @api.model_create_multi
    def create(self, values_list):
        return super().create([
            self._sync_forced_policy(dict(values))
            for values in values_list
        ])

    def write(self, values):
        return super().write(self._sync_forced_policy(dict(values)))

    # ==================================================================
    # Explicación legible de la configuración
    # ==================================================================
    @api.depends(
        'promo_conditions',
        'promo_type',
        'reward_type',
        'apply_on_groups',
        'apply_volume',
        'generic_edi',
        'brand_ids',
        'tier_ids',
        'measure_ids',
        'segment_ids',
        'rin_ids',
        'face_ids',
        'layer_ids',
        'model_ids',
        'product_ids',
        'price_list_ids',
        'rim_policy_line_ids',
        'key_size_product_ids',
        'policy_line_qty_ids',
        'policy_line_amount_ids',
        'monthly_volume_line_ids',
        'coupon_ids',
    )
    def _compute_promo_explanation(self):
        for promotion in self:
            promotion.promo_explanation = promotion._build_explanation_html()
            warnings = promotion._collect_configuration_warnings()
            promotion.config_warning = '\n'.join(warnings) or False

    def _build_explanation_html(self):
        self.ensure_one()
        return (
            '<ul class="mb-0">'
            '<li><b>Participan:</b> %s</li>'
            '<li><b>Beneficio:</b> %s</li>'
            '<li><b>Reglas:</b> %s</li>'
            '</ul>'
        ) % (
            self._describe_scope(),
            self._describe_policy(),
            self._describe_application_rules(),
        )

    def _describe_scope(self):
        self.ensure_one()
        scope = self._get_scope()
        if not scope:
            return 'sin alcance definido (elija uno).'
        if scope == SCOPE_COUPONS:
            return 'los %d producto(s) cargados en la pestaña Cupones.' % len(
                self.coupon_ids
            )
        if scope == SCOPE_SPECIFIC_PRODUCTS:
            return 'los %d producto(s) cargados en la lista.' % len(
                self.product_ids
            )
        if scope == SCOPE_RIM_POLICY:
            rines = self.rim_policy_line_ids.mapped('rim_ids')
            return 'las llantas de los rines de la tabla de políticas (%s).' % (
                ', '.join(rines.mapped('display_name')) or 'sin rines'
            )

        criteria = self._describe_feature_criteria()
        if not criteria:
            return 'nada todavía: no hay características seleccionadas.'
        connector = ' Y ' if scope == SCOPE_ATTRIBUTE_COMBINATION else ' O '
        return 'las llantas que cumplan %s.' % connector.join(criteria)

    def _describe_feature_criteria(self):
        self.ensure_one()
        labels = (
            (self.brand_ids, 'Marca'),
            (self.tier_ids, 'Tier'),
            (self.measure_ids, 'Medida'),
            (self.segment_ids, 'Segmento'),
            (self.rin_ids, 'Rin'),
            (self.face_ids, 'Cara'),
            (self.layer_ids, 'Capa'),
            (self.model_ids, 'Modelo'),
        )
        criteria = []
        for records, label in labels:
            if not records:
                continue
            names = records.mapped('display_name')
            if len(names) > 4:
                names = names[:4] + ['+%d más' % (len(records) - 4)]
            criteria.append('%s (%s)' % (label, ', '.join(names)))
        if self.price_list_ids and self._get_scope() == SCOPE_TIRE_FEATURE:
            criteria.append('Lista de precios (%s)' % ', '.join(
                self.price_list_ids.mapped('name')
            ))
        return criteria

    def _describe_policy(self):
        self.ensure_one()
        policy = self._get_policy()
        if policy == POLICY_COUPONS:
            return (
                'monto fijo por pieza según el cupón de cada producto, '
                'con tope de %d pza por producto y cliente.'
            ) % (self.coupon_limit_qty or DEFAULT_COUPON_LIMIT_QTY)
        if policy == POLICY_RIM_QUANTITY:
            return (
                'se suman todas las llantas participantes para elegir el '
                'tramo; después cada rin cobra su propio porcentaje '
                '(%d tramo(s) configurado(s)).'
            ) % len(self.rim_policy_line_ids)
        if policy == POLICY_MONTHLY_VOLUME:
            return (
                'volumen mensual: valida cantidad total, número de medidas '
                'y mínimo por medida (%d tramo(s)).'
            ) % len(self.monthly_volume_line_ids)
        if policy in TIER_POLICIES:
            base = (
                'cantidad de llantas'
                if policy == POLICY_QUANTITY
                else 'monto facturado'
            )
            reward = (
                'monto fijo en NC'
                if self.reward_type == REWARD_FIXED_AMOUNT
                else 'porcentaje sobre el subtotal'
            )
            description = 'por %s, %s (%d tramo(s))' % (
                base,
                reward,
                len(self._active_policy_lines()),
            )
            if self._has_key_sizes():
                description += (
                    '; %d producto(s) Key Size cobran el porcentaje de su '
                    'propia columna' % len(self.key_size_product_ids)
                )
            return description + '.'
        return 'sin política definida (elija una).'

    def _describe_application_rules(self):
        self.ensure_one()
        rules = [
            'el tramo se calcula por grupo de clientes'
            if self.apply_on_groups == 'si'
            else 'el tramo se calcula por cliente'
        ]
        if self.apply_volume == 'si':
            rules.append(
                'se cuentan todas las llantas facturadas, participen o no'
            )
        rules.append(
            'incluye ventas de mostrador (RFC genérico)'
            if self.generic_edi == 'si'
            else 'excluye ventas de mostrador (RFC genérico)'
        )
        return '; '.join(rules) + '.'

    def _collect_configuration_warnings(self):
        """Detecta configuraciones que dan resultados vacíos o inesperados."""
        self.ensure_one()
        warnings = []
        scope = self._get_scope()
        policy = self._get_policy()

        if not scope:
            warnings.append('Falta elegir el alcance de productos.')
        if not policy:
            warnings.append('Falta elegir el tipo de política.')

        if scope == SCOPE_ATTRIBUTE_COMBINATION and len(
            self._get_product_domains()
        ) < 2:
            warnings.append(
                'La combinación AND necesita al menos dos características '
                'seleccionadas.'
            )
        if scope == SCOPE_TIRE_FEATURE and not self._get_product_domains():
            warnings.append('Seleccione al menos una característica.')
        if scope == SCOPE_SPECIFIC_PRODUCTS and not self.product_ids:
            warnings.append('Cargue al menos un producto.')
        if scope == SCOPE_COUPONS and not self.coupon_ids:
            warnings.append('Cargue al menos un cupón con monto.')

        if policy == POLICY_RIM_QUANTITY:
            warnings.extend(self._collect_rim_scope_warnings())
        if policy in TIER_POLICIES:
            warnings.extend(
                self._collect_tier_warnings(self._active_policy_lines())
            )
        if self.key_size_product_ids:
            warnings.extend(self._collect_key_size_warnings())

        return warnings

    def _collect_key_size_warnings(self):
        """Los cuatro descuidos que dejan un Key Size sin cobrar bien."""
        self.ensure_one()
        warnings = []
        policy = self._get_policy()

        if policy not in TIER_POLICIES:
            return [
                'Los Key Sizes solo aplican con política por Cantidad o por '
                'Monto. Con la política actual se ignoran por completo.'
            ]

        if self.reward_type == REWARD_FIXED_AMOUNT:
            warnings.append(
                'Los Key Sizes son porcentajes y el beneficio está '
                'configurado como monto fijo en NC: se ignoran. Cambie el '
                'Tipo de Beneficio a Porcentaje o quite los Key Sizes.'
            )

        levels = self._active_policy_lines()
        if levels and not any(line.key_size_discount > 0 for line in levels):
            warnings.append(
                'Hay productos marcados como Key Size pero ningún nivel '
                'tiene porcentaje en la columna "% Key Sizes": van a cobrar '
                'el porcentaje general. Capture la columna o quite los '
                'productos.'
            )

        outside = self._key_sizes_outside_scope()
        if outside:
            names = sorted(
                product.default_code or product.name for product in outside
            )
            visible = names[:8]
            warnings.append(
                'Estos Key Sizes no entran por el alcance, así que no '
                'generarán NC ni sumarán al acumulado: %s%s. Agréguelos a '
                'los productos participantes o quítelos de la lista.'
                % (
                    ', '.join(visible),
                    ' y %d más' % (len(names) - len(visible))
                    if len(names) > len(visible)
                    else '',
                )
            )

        return warnings

    def _key_sizes_outside_scope(self):
        """Key Sizes que el alcance deja fuera, cuando se puede saber.

        Solo es comprobable con certeza en el alcance por lista de
        productos. En los alcances por características haría falta
        resolver el dominio contra el catálogo, y un aviso a medias sería
        peor que ninguno.
        """
        self.ensure_one()
        if (
            not self.key_size_product_ids
            or self._get_scope() != SCOPE_SPECIFIC_PRODUCTS
        ):
            return self.env['product.template']
        return self.key_size_product_ids - self.product_ids

    def _collect_rim_scope_warnings(self):
        """Rines que están en la política pero el alcance deja fuera.

        Este es el caso que rompía los cálculos: la tabla de políticas
        listaba R13/R14/R15 mientras el alcance solo admitía R16 y
        superiores. Antes esos rines entraban de todas formas, incluso
        de marcas ajenas a la promoción.
        """
        self.ensure_one()
        policy_rims = self.rim_policy_line_ids.mapped('rim_ids')
        if not policy_rims:
            return ['Configure al menos un tramo en Políticas por Rin.']
        if not self._uses_feature_scope() or not self.rin_ids:
            return []
        excluded = policy_rims - self.rin_ids
        if not excluded:
            return []
        return [
            'Estos rines aparecen en las políticas pero el alcance los deja '
            'fuera, así que no generarán NC: %s. Agréguelos al campo Rines '
            'del alcance o quítelos de la tabla de políticas.'
            % ', '.join(sorted(excluded.mapped('display_name')))
        ]

    def _collect_tier_warnings(self, policies):
        self.ensure_one()
        if not policies:
            return ['Configure al menos un nivel de beneficio.']
        warnings = []
        previous_upper = None
        for policy in policies.sorted('lower_limit'):
            if previous_upper is not None and policy.lower_limit > previous_upper + 1:
                warnings.append(
                    'Hay un hueco entre %s y %s: los acumulados en ese rango '
                    'no reciben beneficio.'
                    % (previous_upper, policy.lower_limit)
                )
            previous_upper = policy.upper_limit or UNLIMITED
        return warnings

    # ==================================================================
    # Validaciones generales
    # ==================================================================
    @api.constrains('start_date', 'end_date')
    def _check_date_range(self):
        for record in self:
            if (
                record.start_date
                and record.end_date
                and record.start_date > record.end_date
            ):
                raise ValidationError(
                    _('La fecha inicial no puede ser posterior a la fecha final.')
                )

    @api.constrains('coupon_limit_qty')
    def _check_coupon_limit(self):
        for record in self:
            if record.coupon_limit_qty < 0:
                raise ValidationError(
                    _('El tope de piezas por producto no puede ser negativo.')
                )

    @api.depends('start_date', 'end_date')
    def _compute_excluded_invoice_ids_domain(self):
        for record in self:
            domain = [
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted'),
            ]
            if record.start_date:
                domain.append(('invoice_date', '>=', record.start_date))
            if record.end_date:
                domain.append(('invoice_date', '<=', record.end_date))
            record.excluded_invoice_ids_domain = str(domain or [])

    @api.depends('line_ids', 'line_ids.total_nc_untaxed')
    def _compute_count_line_ids(self):
        for record in self:
            record.count_line_ids = len(record._result_lines_with_nc())

    @api.depends('detailed_line_ids')
    def _compute_count_detailed_line_ids(self):
        for record in self:
            record.count_detailed_line_ids = len(record.detailed_line_ids)

    def _result_lines_with_nc(self):
        """Resultados que efectivamente generan nota de crédito."""
        self.ensure_one()
        return self.line_ids.filtered(lambda line: line.total_nc_untaxed > 0)

    # ==================================================================
    # Acciones de interfaz
    # ==================================================================
    def action_open_detailed_line_ids(self):
        self.ensure_one()
        action = self.env.ref('ztyres_promo.lines_action').sudo().read()[0]
        action['domain'] = [('definitive_nc_id', '=', self.id)]
        action['context'] = dict(
            form_view_initial_mode='readonly',
            no_create=True,
            no_edit=True,
            no_delete=True,
        )
        return action

    def action_open_line_ids(self):
        self.ensure_one()
        action = self.env.ref(
            'ztyres_promo.action_ztyres_promo_notas_credito_lines'
        ).sudo().read()[0]
        action['domain'] = [
            ('definitive_nc_id', 'in', self.ids),
            ('total_nc_untaxed', '>', 0),
        ]
        action['context'] = dict(
            form_view_initial_mode='readonly',
            no_create=True,
            no_edit=True,
            no_delete=True,
        )
        return action

    def action_approve(self):
        self.ensure_one()
        self.status = 'approve'

    def action_approve_p(self):
        self.ensure_one()
        self.status = 'approve_p'

    def action_open_excel_import(self):
        self.ensure_one()
        return {
            'name': _('Importar Productos desde Excel'),
            'type': 'ir.actions.act_window',
            'res_model': 'ztyres_promo.product_excel_wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
            },
        }

    def action_open_coupon_excel_import(self):
        self.ensure_one()
        return {
            'name': _('Importar Cupones desde Excel'),
            'type': 'ir.actions.act_window',
            'res_model': 'ztyres_promo.coupon_excel_wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_notas_credito_id': self.id,
            },
        }

    def action_open_key_size_excel_import(self):
        self.ensure_one()
        return {
            'name': _('Importar Key Sizes desde Excel'),
            'type': 'ir.actions.act_window',
            'res_model': 'ztyres_promo.key_size_excel_wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_notas_credito_id': self.id,
            },
        }

    def clear_product_relations(self):
        """Limpia los productos participantes y los códigos no encontrados."""
        for record in self:
            record.write({
                'product_ids': [(5, 0, 0)],
                'not_found': False,
            })

    def clear_coupon_product_relations(self):
        """Elimina todos los cupones configurados en la promoción."""
        for record in self:
            record.write({
                'coupon_ids': [(5, 0, 0)],
                'not_found': False,
            })

    def clear_key_size_lines(self):
        """Vacía la lista de Key Sizes. No toca la columna de la tabla."""
        for record in self:
            record.write({'key_size_product_ids': [(5, 0, 0)]})
