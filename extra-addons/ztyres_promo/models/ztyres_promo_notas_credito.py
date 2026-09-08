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
    BASE_INVOICED,
    BASE_PMS,
    DEFAULT_COUPON_LIMIT_QTY,
    FEATURE_SCOPES,
    FORCED_POLICY_BY_SCOPE,
    GIFT_CARD_DELIVERY_NC,
    GIFT_CARD_DELIVERY_NONE,
    GIFT_CARD_DELIVERY_SELECTION,
    GIFT_CARD_SOURCE_PRODUCT,
    GIFT_CARD_SOURCE_SELECTION,
    GIFT_CARD_SOURCE_TIER,
    POLICY_AMOUNT,
    POLICY_AMOUNT_RIM,
    POLICY_COUPONS,
    POLICY_MONTHLY_VOLUME,
    POLICY_QUANTITY,
    POLICY_RIM_QUANTITY,
    POLICY_SELECTION,
    PRICE_TAX_SELECTION,
    PRICE_TAXED,
    PRICE_UNTAXED,
    REWARD_BASE_SELECTION,
    REWARD_FIXED_AMOUNT,
    REWARD_GIFT_CARD,
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
    active = fields.Boolean(
        string='Activo',
        default=True,
        index=True,
        help=(
            'Desactive para archivar la promoción sin borrar su '
            'configuración ni sus resultados históricos.'
        ),
    )
    nombre = fields.Char(string='Nombre')
    # El nombre administrativo ("08-26 Promoción Volumen Mensual
    # Goodyear/Cooper") carga folio, periodo y tipo — información que el
    # vendedor ya ve en otras partes del panel y que en la columna
    # angosta del cotizador se come el ancho antes de llegar a lo único
    # que distingue una promo de otra. Este campo es el nombre corto que
    # se pinta en el cotizador; si se deja vacío, se cae a `nombre` y
    # nada cambia respecto a como estaba.
    cotizador_name = fields.Char(
        string='Nombre en el cotizador',
        help=(
            'Nombre corto que ve el vendedor en el panel de promociones '
            'del cotizador y en los Excel que descarga. Sirve para '
            'quitar el folio y el periodo que ya se muestran aparte: '
            'p. ej. "Goodyear / Cooper" en vez de "08-26 Promoción '
            'Volumen Mensual Goodyear/Cooper". Si se deja vacío se usa '
            'el Nombre de la promoción.'
        ),
    )
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
    key_size_base = fields.Selection(
        string='Base de cálculo del porcentaje',
        selection=REWARD_BASE_SELECTION,
        default=BASE_INVOICED,
        required=True,
        help=(
            'Sobre qué se aplica el porcentaje del nivel.\n\n'
            'Subtotal facturado: lo de siempre. Cada línea cobra sobre lo '
            'que realmente se vendió, así que dos clientes que compraron '
            'el mismo código a distinto precio reciben distinta NC.\n\n'
            'Precio PMS: el porcentaje se aplica sobre el precio de la '
            'tabla PMS multiplicado por las piezas. La NC por pieza es la '
            'misma para todos, sin importar el precio de venta ni los '
            'descuentos que se hayan dado.\n\n'
            'La base NO cambia el nivel alcanzado: el acumulado se sigue '
            'midiendo con lo facturado.'
        ),
    )
    pms_price_taxed = fields.Selection(
        string='El precio PMS se captura',
        selection=PRICE_TAX_SELECTION,
        default=PRICE_UNTAXED,
        required=True,
        help=(
            'Si la columna "pms" del archivo trae precios con IVA o sin '
            'IVA. La nota de crédito se emite sobre el subtotal, así que '
            'un precio capturado con IVA se convierte antes de calcular: '
            'equivocarse aquí cambia la NC un 16%.\n\n'
            'Las listas PMS de las marcas suelen venir SIN IVA, que es el '
            'valor por defecto. Compare un código contra su factura antes '
            'de aprobar la promoción.'
        ),
    )
    pms_price_ids = fields.One2many(
        'ztyres_promo.pms_price',
        'notas_credito_id',
        string='Precios PMS por código',
        help=(
            'Precio de referencia por pieza de cada código, cargado desde '
            'la plantilla de Excel (columnas "codigo" y "pms").'
        ),
    )
    coupon_ids = fields.One2many(
        'ztyres_promo.coupon',
        'notas_credito_id',
        string='Cupones',
    )
    gift_card_ids = fields.One2many(
        'ztyres_promo.gift_card',
        'notas_credito_id',
        string='Valores Promo ZT por código',
        help=(
            'Monto de tarjeta por pieza de cada código, cargado desde la '
            'plantilla de Excel.'
        ),
    )
    gift_card_source = fields.Selection(
        string='Origen del valor de la tarjeta',
        selection=GIFT_CARD_SOURCE_SELECTION,
        default=GIFT_CARD_SOURCE_PRODUCT,
        required=True,
        help=(
            'Valor fijo del nivel: el nivel alcanzado trae el monto en su '
            'columna Promo ZT y no depende de las piezas.\n'
            'Monto por pieza de la plantilla: el nivel solo dice si el '
            'cliente califica; el valor sale de la plantilla por código y '
            'se multiplica por las piezas compradas.'
        ),
    )
    gift_card_delivery = fields.Selection(
        string='Entrega de la tarjeta',
        selection=GIFT_CARD_DELIVERY_SELECTION,
        default=GIFT_CARD_DELIVERY_NONE,
        required=True,
        help=(
            'Solo aviso: el valor se calcula y se muestra en los '
            'resultados, pero no se emite ni se timbra ninguna nota de '
            'crédito; la tarjeta se entrega por fuera.\n'
            'Nota de crédito: además se emite una NC por ese importe. Al '
            'importe se le baja el IVA antes de facturarlo, porque el '
            'timbrado vuelve a sumarlo.'
        ),
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
            "{monto} - monto ganado en NC, ya formateado como moneda. En "
            "una promoción de tarjeta de regalo que no emite NC, trae el "
            "valor de la tarjeta: si trajera el de la NC diría $0.00\n"
            "{tarjeta} - valor de la tarjeta de regalo, o vacío si la "
            "promoción no entrega tarjeta\n"
            "{porcentaje} - porcentaje de descuento, ej. '7.5%' u '8%' "
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
    )
    winning_line_ids = fields.One2many(
        'ztyres_promo.notas_credito_lines',
        'definitive_nc_id',
        compute='_compute_winning_line_ids',
        string='Resultados con recompensa',
        readonly=True,
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
        engine = self.env['ztyres_promo.reward_engine']
        return any(
            not engine.is_zero_percent(line.key_size_discount)
            for line in self._active_policy_lines()
        )

    def _uses_pms_base(self):
        """¿El porcentaje se cobra sobre la tabla de precios PMS?

        Hacen falta las tres cosas, igual que con los Key Sizes: la base
        elegida, la tabla cargada y una política que realmente aplique un
        porcentaje. Sin la tabla no hay sobre qué calcular y se seguiría
        pagando sobre el subtotal facturado sin avisar; por eso se
        comprueba aquí y además se avisa en la configuración.
        """
        self.ensure_one()
        if self.key_size_base != BASE_PMS:
            return False
        if not self.pms_price_ids:
            return False
        if self._get_policy() not in TIER_POLICIES:
            return False
        return self._effective_reward_type() == REWARD_PERCENTAGE

    def _uses_key_size_engine(self):
        """¿El cálculo va renglón por renglón en vez de subtotal x %?

        Dos cosas distintas obligan a bajar al detalle de cada línea:
        que unos productos cobren otro porcentaje (Key Sizes) o que la
        base no sea el subtotal facturado (precios PMS). Cualquiera de
        las dos usa el mismo camino, y por eso conviene una sola pregunta:
        antes cada consumidor preguntaba `_has_key_sizes()` y agregar la
        base PMS habría significado tocar los cinco lugares y olvidar uno.
        """
        self.ensure_one()
        if self._is_amount_rim_promotion():
            return False
        return self._has_key_sizes() or self._uses_pms_base()

    def _pms_unit_price_captured(self):
        """dict {product_tmpl_id: precio PMS TAL COMO SE CAPTURÓ}.

        Sin convertir el IVA. La conversión se hace al final, sobre el
        importe de la línea, y no aquí sobre el precio: el convenio fija
        el descuento por pieza sobre su propio precio de lista, y
        redondear un precio intermedio que el convenio nunca menciona
        desvía la liquidación por centavos.
        """
        self.ensure_one()
        return {
            record.product_id.id: (record.price or 0.0)
            for record in self.pms_price_ids
        }

    def _pms_tax_factor(self):
        """Divisor de IVA para los importes calculados sobre el PMS.

        1.16 cuando los precios se capturaron con IVA —hay que llevar el
        beneficio a subtotal, que es como se emite la NC— y 1.0 cuando
        ya venían sin IVA.
        """
        self.ensure_one()
        if self.pms_price_taxed != PRICE_TAXED:
            return 1.0
        return self.env['ztyres_promo.reward_engine']._tier_tax_factor()

    def _pms_unit_by_line(self, lines):
        """Precio PMS de UNA pieza por línea, tal como se capturó.

        Devuelve ``(unitario_por_linea, productos_sin_precio)``.

        Se devuelve el precio unitario y no `precio x piezas` porque el
        motor tiene que redondear el descuento POR PIEZA antes de
        multiplicarlo: el convenio fija "$120.95 por llanta", y esa es
        la cifra que la marca multiplica en su liquidación.

        Una línea cuyo código no esté en la tabla NO entra al
        diccionario, y el motor la deja cobrando sobre su subtotal
        facturado. Es deliberado: la alternativa —base cero— le quitaría
        la NC a ese cliente sin que nadie se entere hasta que reclame.
        Los códigos que faltan se devuelven para poder avisarlos.
        """
        self.ensure_one()
        engine = self.env['ztyres_promo.reward_engine']
        price_by_product = self._pms_unit_price_captured()
        unit_by_line = {}
        missing = self.env['product.template']

        for line in lines:
            template = engine._template_of(line.product_id)
            if template.id not in price_by_product:
                missing |= template
                continue
            unit_by_line[line.id] = price_by_product[template.id]

        return unit_by_line, missing

    def _key_size_unit_by_line(self, lines):
        """Unitarios para el motor, o None si la base es la de siempre.

        `None` no es lo mismo que un diccionario vacío: el motor lo lee
        como "usa el subtotal facturado de cada línea". Un diccionario
        vacío significaría "ninguna línea tiene precio", que con el
        fallback termina en el mismo sitio pero por accidente.
        """
        self.ensure_one()
        if not self._uses_pms_base():
            return None
        unit_by_line, _missing = self._pms_unit_by_line(lines)
        return unit_by_line

    def _pms_base_label(self):
        """Etiqueta para el detalle auditable. Vacía si la base es la normal."""
        self.ensure_one()
        if not self._uses_pms_base():
            return ''
        return 'bases tomadas del precio PMS, capturado %s IVA' % (
            'con' if self.pms_price_taxed == PRICE_TAXED else 'sin'
        )

    def _is_gift_card_promotion(self):
        """¿El beneficio de esta promoción es una tarjeta de regalo?"""
        self.ensure_one()
        return self._effective_reward_type() == REWARD_GIFT_CARD

    def _gift_card_uses_product_table(self):
        """¿El valor sale de la plantilla por código?"""
        self.ensure_one()
        return (
            self._is_gift_card_promotion()
            and self.gift_card_source == GIFT_CARD_SOURCE_PRODUCT
        )

    def _gift_card_generates_nc(self):
        """La tarjeta/cupón nunca genera nota de crédito."""
        self.ensure_one()
        return False

    def _gift_card_amount_for_lines(self, lines, quantity_field='quantity'):
        """Valor de tarjeta (CON IVA) que generan estas líneas.

        Solo tiene sentido con la plantilla por código: el valor fijo
        por nivel no se reparte entre líneas, es uno por resultado.

        :return: ``(total, {line_id: monto})``
        """
        self.ensure_one()
        return self.env['ztyres_promo.reward_engine'].gift_card_product_amounts(
            self.gift_card_ids,
            lines,
            quantity_field,
        )

    def _uses_amount_policy(self):
        self.ensure_one()
        return self._get_policy() in (POLICY_AMOUNT, POLICY_AMOUNT_RIM)

    def _is_amount_rim_promotion(self):
        self.ensure_one()
        return self._get_policy() == POLICY_AMOUNT_RIM

    def _uses_feature_scope(self):
        self.ensure_one()
        return self._get_scope() in FEATURE_SCOPES

    def _effective_reward_type(self):
        """El tipo de beneficio configurable solo existe en tramos."""
        self.ensure_one()
        if self._get_policy() == POLICY_AMOUNT_RIM:
            return REWARD_PERCENTAGE
        if self._get_policy() in TIER_POLICIES:
            return self.reward_type
        return REWARD_PERCENTAGE

    def _active_policy_lines(self):
        """Tabla de tramos de la política vigente."""
        self.ensure_one()
        policy = self._get_policy()
        if policy == POLICY_QUANTITY:
            return self.policy_line_qty_ids
        if policy in (POLICY_AMOUNT, POLICY_AMOUNT_RIM):
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

    @api.onchange('promo_type')
    def _onchange_promo_type_amount_rim(self):
        for promotion in self:
            if promotion.promo_type == POLICY_AMOUNT_RIM:
                promotion.reward_type = REWARD_PERCENTAGE
                # Esta política se liquida por código contra su precio PMS.
                # El monto real facturado solo determina el tramo alcanzado.
                promotion.key_size_base = BASE_PMS

    @api.onchange('reward_type')
    def _onchange_reward_type_gift_card(self):
        """La Promo ZT vigente siempre toma el valor del Excel por código."""
        for promotion in self:
            if promotion.reward_type == REWARD_GIFT_CARD:
                promotion.gift_card_source = GIFT_CARD_SOURCE_PRODUCT
                promotion.gift_card_delivery = GIFT_CARD_DELIVERY_NONE

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
        'key_size_base',
        'pms_price_taxed',
        'pms_price_ids',
        'policy_line_qty_ids',
        'policy_line_amount_ids',
        'monthly_volume_line_ids',
        'coupon_ids',
        'gift_card_ids',
        'gift_card_source',
        'gift_card_delivery',
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
            accumulated_scope = (
                'todas las llantas facturadas, participen o no'
                if self.apply_volume == 'si'
                else 'todas las llantas participantes'
            )
            return (
                'se suman %s para elegir el '
                'tramo; después cada rin cobra su propio porcentaje '
                '(%d tramo(s) configurado(s)).'
            ) % (accumulated_scope, len(self.rim_policy_line_ids))
        if policy == POLICY_MONTHLY_VOLUME:
            return (
                'volumen mensual: valida cantidad total, número de medidas '
                'y mínimo por medida (%d tramo(s)).'
            ) % len(self.monthly_volume_line_ids)
        if policy == POLICY_AMOUNT_RIM:
            return (
                'por monto facturado: el tramo se elige con el acumulado y '
                'cada línea cobra según su rin (R14-R16 o R17+); los Key '
                'Sizes usan su porcentaje propio (%d tramo(s)).'
            ) % len(self.policy_line_amount_ids)
        if policy in TIER_POLICIES:
            base = (
                'cantidad de llantas'
                if policy == POLICY_QUANTITY
                else 'monto facturado'
            )
            if self.reward_type == REWARD_GIFT_CARD:
                return self._describe_gift_card(base)
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
            if self._uses_pms_base():
                description += (
                    '; el porcentaje NO se cobra sobre lo facturado sino '
                    'sobre el precio PMS x piezas (%d código(s) con precio, '
                    'capturados %s IVA)' % (
                        len(self.pms_price_ids),
                        'con' if self.pms_price_taxed == PRICE_TAXED else 'sin',
                    )
                )
            return description + '.'
        return 'sin política definida (elija una).'

    def _describe_gift_card(self, base):
        """Frase de la tarjeta de regalo: valor, origen y si genera NC."""
        self.ensure_one()
        entrega = (
            'se emite nota de crédito por ese valor'
            if self.gift_card_delivery == GIFT_CARD_DELIVERY_NC
            else 'no genera nota de crédito: la tarjeta se entrega por fuera'
        )
        if self.gift_card_source == GIFT_CARD_SOURCE_PRODUCT:
            return (
                'el nivel por %s solo dice si el cliente califica '
                '(%d tramo(s)); el valor de la tarjeta es el monto por '
                'pieza de cada código de la plantilla (%d código(s) '
                'cargado(s)) multiplicado por las piezas compradas. %s.'
            ) % (
                base,
                len(self._active_policy_lines()),
                len(self.gift_card_ids),
                entrega[0].upper() + entrega[1:],
            )
        return (
            'tarjeta de regalo por %s: el nivel alcanzado entrega su valor '
            'fijo de la columna Promo ZT, sin importar las piezas '
            '(%d tramo(s)). %s.'
        ) % (
            base,
            len(self._active_policy_lines()),
            entrega[0].upper() + entrega[1:],
        )

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
        if self.key_size_base == BASE_PMS or self.pms_price_ids:
            warnings.extend(self._collect_pms_warnings())
        if self.reward_type == REWARD_GIFT_CARD:
            warnings.extend(self._collect_gift_card_warnings())

        return warnings

    def _collect_gift_card_warnings(self):
        """Los descuidos que dejan la tarjeta en cero o la pagan de más."""
        self.ensure_one()
        warnings = []
        policy = self._get_policy()

        if policy not in TIER_POLICIES:
            return [
                'La tarjeta de regalo solo aplica con política por Cantidad '
                'o por Monto: son las únicas que tienen niveles para decidir '
                'si el cliente califica. Con la política actual se ignora.'
            ]

        levels = self._active_policy_lines()

        if self.gift_card_source == GIFT_CARD_SOURCE_PRODUCT:
            if not self.gift_card_ids:
                warnings.append(
                    'El valor de la tarjeta sale de la plantilla por código '
                    'pero no hay ningún código cargado: todos los clientes '
                    'que califiquen recibirían tarjeta de cero. Cargue la '
                    'plantilla en la pestaña Tarjeta de regalo.'
                )
            elif not any(card.amount > 0 for card in self.gift_card_ids):
                warnings.append(
                    'Todos los códigos cargados tienen monto cero: la '
                    'tarjeta siempre saldría en cero.'
                )
            outside = self._gift_cards_outside_scope()
            if outside:
                names = sorted(
                    product.default_code or product.name for product in outside
                )
                visible = names[:8]
                warnings.append(
                    'Estos códigos tienen valor de Promo ZT pero el alcance '
                    'los deja fuera, así que no van a pagar tarjeta: %s%s. '
                    'Agréguelos a los productos participantes o quítelos de '
                    'la plantilla.' % (
                        ', '.join(visible),
                        ' y %d más' % (len(names) - len(visible))
                        if len(names) > len(visible)
                        else '',
                    )
                )
        else:
            if levels and not any(
                getattr(level, 'gift_card_amount', 0.0) > 0
                for level in levels
            ):
                warnings.append(
                    'Ningún nivel tiene valor en la columna "Promo ZT": la '
                    'promoción no entregaría tarjeta. Capture el valor por '
                    'nivel, o cambie el origen a la plantilla por código.'
                )
            if self.gift_card_ids:
                warnings.append(
                    'Hay %d código(s) cargados en la plantilla de Promo ZT, '
                    'pero el origen del valor es el nivel: esos montos se '
                    'están ignorando.' % len(self.gift_card_ids)
                )

        if policy in (POLICY_AMOUNT, POLICY_AMOUNT_RIM) and levels:
            # Aquí no hay un valor "correcto" que el sistema pueda
            # adivinar: depende de cómo esté escrita la meta en el
            # convenio. Por eso el aviso NO recomienda un número —
            # informa qué significa el que ya está capturado y deja la
            # decisión en quien conoce el convenio.
            #
            # El caso normal es que la meta ya venga facturada, con IVA
            # ("compra mínima de 50 mil"), y entonces lo capturado es
            # correcto tal cual. Ojo con la palabra "netos" del
            # convenio: casi siempre significa neto de descuentos y
            # devoluciones, NO sin IVA.
            factor = self.env[
                'ztyres_promo.reward_engine'
            ]._tier_tax_factor()
            minimum = min(levels.mapped('lower_limit') or [0])
            if minimum > 0:
                warnings.append(
                    'Nivel mínimo capturado: %s CON IVA, o sea que se '
                    'alcanza con %s de subtotal. Si la meta del convenio '
                    'ya viene facturada (lo habitual, aunque diga '
                    '"netos": eso suele ser neto de descuentos y '
                    'devoluciones, no sin IVA), está correcto así. Solo '
                    'si la meta fuera sin IVA habría que capturar %s.' % (
                        '{:,.0f}'.format(minimum),
                        '{:,.2f}'.format(minimum / factor),
                        '{:,.0f}'.format(minimum * factor),
                    )
                )

        if self.gift_card_delivery == GIFT_CARD_DELIVERY_NC:
            warnings.append(
                'Esta promoción está configurada para EMITIR Y TIMBRAR una '
                'nota de crédito por el valor de la tarjeta. Si la tarjeta '
                'se entrega por fuera, cambie "Entrega de la tarjeta" a '
                '"Solo aviso".'
            )

        return warnings

    def _gift_cards_outside_scope(self):
        """Códigos con valor de tarjeta que el alcance deja fuera.

        Igual que con los Key Sizes, solo es comprobable con certeza en
        el alcance por lista de productos; en los alcances por
        características habría que resolver el dominio contra el
        catálogo y un aviso a medias confunde más de lo que ayuda.
        """
        self.ensure_one()
        if (
            not self.gift_card_ids
            or self._get_scope() != SCOPE_SPECIFIC_PRODUCTS
        ):
            return self.env['product.template']
        return self.gift_card_ids.mapped('product_id') - self.product_ids

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

    def _collect_pms_warnings(self):
        """Los descuidos que hacen que la NC salga sobre la base equivocada.

        El más caro es silencioso: dejar la base en PMS sin cargar la
        tabla. La promoción calcula igual, no falla, y paga sobre el
        subtotal facturado — que es justo lo que se quería evitar.
        """
        self.ensure_one()
        warnings = []
        policy = self._get_policy()
        chosen = self.key_size_base == BASE_PMS

        if chosen and policy not in TIER_POLICIES:
            return [
                'La base "Precio PMS" solo aplica con política por Cantidad '
                'o por Monto. Con la política actual se ignora y el '
                'beneficio se calcula sobre lo facturado.'
            ]

        if chosen and self._effective_reward_type() != REWARD_PERCENTAGE:
            warnings.append(
                'La base "Precio PMS" solo tiene sentido con Tipo de '
                'Beneficio Porcentaje: un monto fijo o una tarjeta no se '
                'multiplican por ninguna base. Se está ignorando.'
            )

        if chosen and not self.pms_price_ids:
            warnings.append(
                'La base es "Precio PMS" pero no hay ningún precio '
                'cargado: la promoción está pagando sobre el subtotal '
                'facturado. Cargue la plantilla (columnas "codigo" y '
                '"pms") en la pestaña Precios PMS.'
            )

        if self.pms_price_ids and not chosen:
            warnings.append(
                'Hay %d precio(s) PMS cargados, pero la base de cálculo es '
                'el subtotal facturado: esos precios no se están usando. '
                'Cambie la base a "Precio PMS x piezas" o limpie la '
                'tabla.' % len(self.pms_price_ids)
            )

        if self.pms_price_ids and not any(
            record.price > 0 for record in self.pms_price_ids
        ):
            warnings.append(
                'Todos los precios PMS cargados están en cero: la nota de '
                'crédito saldría en cero para esos códigos.'
            )

        if chosen and self.pms_price_ids:
            warnings.append(
                'Los precios PMS están capturados %s IVA. La NC se calcula '
                'sobre el subtotal, así que %s. Verifique un código contra '
                'su factura antes de aprobar.' % (
                    'CON' if self.pms_price_taxed == PRICE_TAXED else 'SIN',
                    'a cada precio se le baja el IVA antes de aplicar el '
                    'porcentaje'
                    if self.pms_price_taxed == PRICE_TAXED
                    else 'los precios se usan tal cual'
                )
            )

        outside = self._participants_without_pms_price()
        if outside:
            names = sorted(
                product.default_code or product.name for product in outside
            )
            visible = names[:8]
            warnings.append(
                'Estos productos participan pero no tienen precio PMS, así '
                'que van a cobrar sobre su subtotal facturado: %s%s. '
                'Agréguelos al archivo o quítelos del alcance.' % (
                    ', '.join(visible),
                    ' y %d más' % (len(names) - len(visible))
                    if len(names) > len(visible)
                    else '',
                )
            )

        return warnings

    def _participants_without_pms_price(self):
        """Participantes sin precio PMS, cuando se puede saber con certeza.

        Misma limitación que en Key Sizes y tarjetas: solo es
        comprobable con el alcance por lista de productos. En los
        alcances por características habría que resolver el dominio
        contra todo el catálogo, y un aviso a medias confunde más de lo
        que ayuda.
        """
        self.ensure_one()
        empty = self.env['product.template']
        if not self._uses_pms_base():
            return empty
        if self._get_scope() != SCOPE_SPECIFIC_PRODUCTS:
            return empty
        return self.product_ids - self.pms_price_ids.mapped('product_id')

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

    @api.depends(
        'line_ids',
        'line_ids.has_reward',
    )
    def _compute_count_line_ids(self):
        for record in self:
            record.count_line_ids = len(
                record.line_ids.filtered('has_reward')
            )

    @api.depends('line_ids', 'line_ids.has_reward')
    def _compute_winning_line_ids(self):
        for record in self:
            record.winning_line_ids = record.line_ids.filtered('has_reward')

    @api.depends('detailed_line_ids')
    def _compute_count_detailed_line_ids(self):
        for record in self:
            record.count_detailed_line_ids = len(record.detailed_line_ids)

    def _result_lines_with_nc(self):
        """Resultados que efectivamente generan nota de crédito."""
        self.ensure_one()
        return self.line_ids.filtered(
            lambda line: line.has_reward and line.total_nc_untaxed > 0
        )

    def _result_lines_visible(self):
        """Resultados con algo que mostrar: NC o tarjeta.

        No es lo mismo que `_result_lines_with_nc`, y la diferencia
        importa: una promoción de tarjeta entregada por fuera tiene
        importe de NC cero en todos sus renglones. Si el contador y la
        lista usaran el filtro de NC, la promoción se calcularía bien y
        se vería vacía.
        """
        self.ensure_one()
        return self.line_ids.filtered('has_reward')

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
            ('has_reward', '=', True),
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

    def action_open_pms_price_excel_import(self):
        self.ensure_one()
        return {
            'name': _('Importar precios PMS desde Excel'),
            'type': 'ir.actions.act_window',
            'res_model': 'ztyres_promo.pms_price_excel_wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_notas_credito_id': self.id,
            },
        }

    def action_open_gift_card_excel_import(self):
        self.ensure_one()
        return {
            'name': _('Importar valores Promo ZT desde Excel'),
            'type': 'ir.actions.act_window',
            'res_model': 'ztyres_promo.gift_card_excel_wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_notas_credito_id': self.id,
            },
        }

    def clear_gift_card_lines(self):
        """Vacía la plantilla de valores Promo ZT."""
        for record in self:
            record.write({'gift_card_ids': [(5, 0, 0)]})

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

    def clear_pms_price_lines(self):
        """Vacía la tabla de precios PMS. No cambia la base elegida."""
        for record in self:
            record.write({'pms_price_ids': [(5, 0, 0)]})

    def clear_key_size_lines(self):
        """Vacía la lista de Key Sizes. No toca la columna de la tabla."""
        for record in self:
            record.write({'key_size_product_ids': [(5, 0, 0)]})
