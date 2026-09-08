# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

from .promo_line import PromoLine

_logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Adaptador para el motor de ztyres_promo (Notas de Crédito).
#
# `ztyres_promo.notas_credito.evaluate_document()` está pensado para
# recordsets de sale.order.line / account.move.line — usa .filtered(),
# .mapped(), line.product_id, line.price_subtotal, line[qty_field] y
# line.display_type. El cotizador NO tiene un sale.order (todavía no
# hay ni orden ni factura: es una cotización en vivo), así que estas
# dos clases imitan exactamente esa interfaz con las PromoLine crudas
# del carrito. Con esto el mixin de ztyres_promo evalúa el carrito
# como si fuera una cotización real — mismo motor, mismas reglas,
# cero duplicación de lógica.
# ----------------------------------------------------------------------
class _NcEvalLine:
    """Línea falsa que imita sale.order.line / account.move.line
    para que _promo_line_matches y evaluate_document la acepten.
    Necesita: product_id, product_uom_qty, price_subtotal,
    display_type, list_origin, sale_line_ids (para price_list check)."""
    display_type = False

    def __init__(self, line_id, product, qty=0, price_unit=0):
        self.id = line_id
        self.product_id = product
        self.product_uom_qty = qty
        self.quantity = qty
        self.price_subtotal = (price_unit or 0.0) * (qty or 0.0)
        # _get_line_price_list_origin busca estos dos atributos
        self.list_origin = False
        self.sale_line_ids = []

    def __getitem__(self, name):
        return getattr(self, name, 0)


class _NcEvalLines(list):
    def filtered(self, fn):
        return _NcEvalLines(l for l in self if fn(l))

    def mapped(self, name):
        return [l[name] for l in self]


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ------------------------------------------------------------------
    # Adaptador: traduce las líneas de la cotización al formato interno
    # PromoLine con el que trabaja el preview del cotizador. Si el día
    # de mañana sale.order.line cambia de forma, solo este método se
    # toca.
    # ------------------------------------------------------------------
    def _promo_lines(self):
        return [
            PromoLine(
                id=line.id,
                product_id=line.product_id,
                qty=line.product_uom_qty,
                price_unit=line.price_unit,
            )
            for line in self.order_line
            if line.product_id
        ]

    @api.model
    def get_promotions_preview(self, partner_id, lines):
        """Punto de entrada del cotizador externo. 'lines' son objetos
        sueltos que NO son registros de Odoo — vienen del HTML/JS como
        [{'product_id': 123, 'qty': 50}, ...]. product_id sí debe ser
        un product.product real (de get_tire_catalog), porque las
        reglas necesitan su brand_id/tier_id/tire_measure_id.

        Ya no se crea un sale.order falso con .new(): se construyen las
        PromoLine directamente desde el payload. El motor de
        promociones es el mismo que usan sale.order y account.move,
        pero no necesita que finjamos que esto es un pedido.
        """
        product_ids = [l['product_id'] for l in lines]
        products_by_id = {
            p.id: p for p in self.env['product.product'].browse(product_ids)
        }
        # price_unit viene de las listas de precios válidas
        # (sale_dot.get_catalog_price_for_product), NO de lst_price:
        # en varios productos lst_price está en 0, el precio real vive
        # en los pricelist items. Mismo método que usa get_tire_catalog
        # para que el precio que ve el vendedor antes de cotizar sea
        # el mismo que entra al motor de promociones.
        sol_model = self.env['sale.order.line']
        promo_lines = [
            PromoLine(
                id=i,
                product_id=products_by_id[l['product_id']],
                qty=l['qty'],
                price_unit=sol_model.get_catalog_price_for_product(
                    products_by_id[l['product_id']]
                ),
            )
            for i, l in enumerate(lines)
        ]
        # int(partner_id): si esto llega como string (p. ej. "11296")
        # en vez de int, browse() lo trata como un ITERABLE — cada
        # carácter por separado ('1','1','2','9','6') — en vez de un
        # solo id, y truena más adelante con "Expected singleton"
        # apenas algo necesite un solo partner. Pasaba justo al
        # cambiar de cliente en el cotizador: el <select> del
        # frontend mandaba el value como texto.
        partner = self.env['res.partner'].browse(int(partner_id))

        # ------------------------------------------------------------
        # ÚNICO MOTOR DE PROMOCIONES: ztyres_promo (Notas de Crédito).
        # El motor viejo (ztyres_promotions.rule) fue ELIMINADO del
        # módulo — las líneas del quote salen a precio de lista limpio
        # y todo lo que "premia" viene del bloque promo_ganada de
        # abajo (informativo: la NC se emite al facturar, no descuenta
        # el total de la cotización).
        # ------------------------------------------------------------
        lines_out = []
        for pl in promo_lines:
            unit_price = pl.price_unit or 0.0
            lines_out.append({
                'product_id': pl.product_id.id,
                'product_name': pl.product_id.display_name,
                'qty': pl.qty,
                'unit_price': unit_price,
                'final_unit_price': unit_price,
                'subtotal': unit_price * pl.qty,
            })
        serialized = {
            'lines': lines_out,
            'order_total': sum(l['subtotal'] for l in lines_out),
        }

        # ------------------------------------------------------------
        # Cantidad libre de usar y rango de DOT — SOLO para el
        # cotizador externo. No se agrega dentro de
        # _serialize_promotion_result porque ese método también lo
        # se agrega al armar las líneas porque el precio/stock es un
        # dato de catálogo, no del cálculo de promociones.
        #
        # Fuente del dato: sale.order.line.get_free_qty_and_dot_range_
        # for_product() (módulo sale_dot), que lee stock.quant
        # directamente (quantity - reserved_quantity en ubicaciones
        # internal) y agrupa los lotes por año con rango_fechas().
        # Requiere que el módulo sale_dot esté instalado.
        #
        # Es informativo: no participa en el cálculo de precio ni de
        # descuentos, que sigue siendo el mismo de siempre
        # ------------------------------------------------------------
        sol_model = self.env['sale.order.line']
        for line_out, pl in zip(serialized['lines'], promo_lines):
            free_qty, dot_range = sol_model.get_free_qty_and_dot_range_for_product(
                pl.product_id
            )
            line_out['free_qty'] = free_qty
            line_out['dot_range'] = dot_range

        # ------------------------------------------------------------
        # Promociones vigentes de ztyres_promo (Notas de Crédito) —
        # se evalúan AQUÍ MISMO, sobre el carrito, sin necesidad de
        # que exista orden ni factura: el propio ztyres_promo trae un
        # mixin "en vivo" (document_promo_mixin) hecho justo para eso.
        # Es informativo, igual que en la cotización de Odoo: muestra
        # cuánto se ganaría en NC; la NC real se sigue emitiendo desde
        # el flujo normal de ztyres_promo al facturar.
        # ------------------------------------------------------------
        serialized['promo_ganada'] = self._ztyres_promo_nc_preview(partner, promo_lines)

        return serialized

    @api.model
    def get_cotizador_promos(self):
        """Promociones vigentes de ztyres_promo, serializadas para las
        facetas del cotizador: nombre, tipo, sus RANGOS (tramos de
        descuento por cantidad o monto, o cupones por producto) y los
        product_id del catálogo que cumplen sus condiciones — con eso
        el frontend puede simular el precio con promo sobre las
        llantas que aplican, sin duplicar la lógica de matching (se
        reutiliza _promo_line_matches del propio ztyres_promo).

        Devuelve [] si ztyres_promo no está instalado o algo falla:
        el cotizador simplemente muestra "Sin promociones vigentes".
        """
        if 'ztyres_promo.notas_credito' not in self.env:
            return []
        try:
            today = fields.Date.context_today(self)
            Promo = self.env['ztyres_promo.notas_credito'].sudo()
            promos = Promo.search([
                ('active', '=', True),
                # Coincide con EVAL_VALID_STATUSES del motor real. El estado
                # ``approve`` significa que las NC ya fueron aprobadas, no
                # que la promoción deba ofrecerse en una cotización nueva.
                ('status', 'in', ('approve_p', 'done')),
                '|', ('start_date', '=', False), ('start_date', '<=', today),
                '|', ('end_date', '=', False), ('end_date', '>=', today),
            ])
            # No filtrar por promo_display_mode — el cotizador muestra
            # TODAS las promos aprobadas/vigentes como opciones de
            # simulación. El display_mode es para la vista de factura,
            # no para el cotizador.
            if not promos:
                return []

            # Variantes del catálogo cotizable (mismo universo que
            # get_tire_catalog). El match se evalúa por variante con
            # el MISMO método que usa el cálculo real de la promo.
            templates = self.env['product.template'].sudo().search([('tire', '=', True)])
            variants = [t.product_variant_id for t in templates if t.product_variant_id]

            out = []
            for promo in promos:
                matched = []
                matched_variants = {}
                for v in variants:
                    try:
                        if promo._promo_line_matches(_NcEvalLine(0, v)):
                            matched.append(v.id)
                            matched_variants[v.id] = v
                    except Exception:
                        # Si un producto falla el match (campo faltante,
                        # relación rota), se ignora — mejor devolver la
                        # promo sin ese producto que no devolver nada.
                        pass
                # Los nombres efectivos importan para registros heredados:
                # el alcance puede inferirse de product_ids y Cupones/Rin
                # fuerzan su política. Es la misma resolución que usa el
                # motor de ztyres_promo.
                scope = promo._get_scope()
                policy = promo._get_policy()
                reward_type = promo._effective_reward_type()
                unlimited = 999999999

                def tier_dict(line):
                    return {
                        'min': line.lower_limit,
                        'max': line.upper_limit or unlimited,
                        'discount': line.discount,
                        # Columna "% Key Sizes" del nivel. Sin esto el
                        # simulador mostraba el porcentaje general para
                        # productos que la NC real paga a otro precio.
                        'key_size_discount': (
                            getattr(line, 'key_size_discount', 0.0) or 0.0
                        ),
                        'fixed_amount': getattr(line, 'fixed_amount', 0.0) or 0.0,
                        'min_qty': getattr(line, 'min_qty', 0) or 0,
                    }

                tiers = []
                if policy == 'quantity':
                    tiers = [tier_dict(l) for l in promo.policy_line_qty_ids]
                elif policy == 'amount':
                    tiers = [tier_dict(l) for l in promo.policy_line_amount_ids]
                elif policy == 'amount_rim':
                    # Tramo por MONTO, pero el porcentaje se determina por
                    # producto: Key Size tiene prioridad y, si no lo es, se
                    # busca el rango de RIN configurado en ese mismo tramo.
                    # Se precalcula el mapa por product_id para que pantalla
                    # y XLSX usen exactamente el mismo porcentaje.
                    key_templates = set(promo.key_size_product_ids.ids)
                    tiers = []
                    for line in promo.policy_line_amount_ids:
                        data = tier_dict(line)
                        data['rim_discounts'] = []
                        data['product_discounts'] = {}
                        for rule in line.rim_discount_ids.sorted(
                            lambda r: (r.rim_from, r.rim_to, r.id)
                        ):
                            data['rim_discounts'].append({
                                'rim_from': rule.rim_from,
                                'rim_to': rule.rim_to,
                                'rims': 'R%s-R%s' % (
                                    rule.rim_from,
                                    '+' if rule.rim_to >= 99 else rule.rim_to,
                                ),
                                'discount': rule.discount,
                            })
                        for product_id, variant in matched_variants.items():
                            tmpl = variant.product_tmpl_id
                            if tmpl.id in key_templates:
                                discount = line.key_size_discount or 0.0
                            else:
                                rim = variant.tire_measure_id.rim_id
                                try:
                                    rim_number = float(rim.number or 0.0) if rim else 0.0
                                except (TypeError, ValueError):
                                    rim_number = 0.0
                                rule = line.rim_discount_ids.filtered(
                                    lambda r: r.rim_from <= rim_number <= r.rim_to
                                )[:1]
                                discount = rule.discount if rule else 0.0
                            data['product_discounts'][str(product_id)] = discount
                        # No existe un porcentaje general en amount_rim;
                        # este máximo solo sirve como valor resumen visual.
                        candidates = [
                            float(row.get('discount') or 0.0)
                            for row in data['rim_discounts']
                        ]
                        candidates.append(float(data.get('key_size_discount') or 0.0))
                        data['discount'] = max(candidates or [0.0])
                        tiers.append(data)
                elif policy == 'monthly_volume':
                    tiers = [
                        dict(
                            tier_dict(l),
                            minimum_products=l.minimum_products,
                            minimum_qty_per_measure=l.minimum_qty_per_measure,
                        )
                        for l in promo.monthly_volume_line_ids
                    ]
                elif policy == 'rim_quantity':
                    # La selección representa el ACUMULADO global. Dentro de
                    # ese mismo escenario cada rin puede tener un porcentaje
                    # distinto, por lo que se agrupan las filas Desde/Hasta y
                    # se envía el porcentaje correspondiente a cada producto.
                    grouped = {}
                    for line in promo.rim_policy_line_ids:
                        key = (line.lower_limit, line.upper_limit or unlimited)
                        scenario = grouped.setdefault(key, {
                            'min': key[0],
                            'max': key[1],
                            'discount': 0.0,
                            'fixed_amount': 0.0,
                            'min_qty': 0,
                            'rim_discounts': [],
                            'product_discounts': {},
                        })
                        scenario['rim_discounts'].append({
                            'rims': ', '.join(line.rim_ids.mapped('display_name')),
                            'discount': line.discount,
                        })
                        scenario['discount'] = max(
                            scenario['discount'], line.discount
                        )
                        rim_ids = set(line.rim_ids.ids)
                        for product_id, variant in matched_variants.items():
                            rim = variant.tire_measure_id.rim_id
                            if rim and rim.id in rim_ids:
                                scenario['product_discounts'][str(product_id)] = (
                                    line.discount
                                )
                    tiers = list(grouped.values())
                tiers.sort(key=lambda t: (t['min'], t['max'], t['discount']))
                coupons = []
                if policy == 'coupons':
                    coupons = [
                        {'tmpl_id': c.product_id.id, 'amount': c.amount}
                        for c in promo.coupon_ids if c.product_id
                    ]
                elif reward_type == 'gift_card':
                    # Promo ZT: el tramo de monto solo habilita el beneficio;
                    # el descuento unitario del cotizador sale del Excel
                    # código→valor. ``amount`` se captura CON IVA, mientras
                    # catálogo y simulador trabajan SIN IVA, por eso se baja
                    # aquí. Al volver a mostrar con IVA, 84.07 seguirá siendo
                    # exactamente 84.07 y no 97.52.
                    engine = self.env['ztyres_promo.reward_engine']
                    coupons = [
                        {
                            'tmpl_id': card.product_id.id,
                            'amount': engine.untaxed(card.amount),
                            'amount_with_tax': card.amount,
                        }
                        for card in promo.gift_card_ids
                        if card.product_id and card.amount > 0
                    ]
                policy_labels = {
                    'quantity': 'Cantidad',
                    'amount': 'Monto',
                    'amount_rim': 'Monto por Rin / Key Sizes',
                    'monthly_volume': 'Volumen mensual',
                    'rim_quantity': 'Cantidad acumulada por rin',
                    'coupons': 'Cupones',
                }
                out.append({
                    'id': promo.id,
                    'name': promo.nombre or promo.display_name,
                    # Rótulo corto para pantalla y Excel. El `name`
                    # administrativo se conserva porque sigue siendo el
                    # que identifica la promo en tooltips y soporte.
                    'display_label': (
                        promo.cotizador_name
                        or promo.nombre
                        or promo.display_name
                    ),
                    'promo_type': policy,
                    'promo_conditions': scope,
                    'policy_label': policy_labels.get(policy, policy or 'Sin política'),
                    'reward_type': reward_type,
                    'start_date': str(promo.start_date or ''),
                    'end_date': str(promo.end_date or ''),
                    'tiers': tiers,
                    'coupons': coupons,
                    'coupon_limit_qty': promo.coupon_limit_qty or 0,
                    # Variantes cuyo template está marcado como Key Size.
                    # Se manda la lista, no un mapa por nivel: son pocos
                    # productos y el payload no crece con cada tramo.
                    'key_size_product_ids': [
                        v.id for v in matched_variants.values()
                        if v.product_tmpl_id in promo.key_size_product_ids
                    ],
                    'uses_pms_base': promo._uses_pms_base(),
                    'pms_price_by_product': {
                        str(record.product_id.product_variant_id.id): (
                            record.price or 0.0
                        )
                        for record in promo.pms_price_ids
                        if record.product_id.product_variant_id and record.price > 0
                    } if promo._uses_pms_base() else {},
                    'pms_tax_factor': (
                        promo._pms_tax_factor() if promo._uses_pms_base()
                        else 1.0
                    ),
                    'product_ids': matched,
                    'product_count': len(matched),
                })
            return out
        except Exception:
            _logger.exception('Fallo serializando promos vigentes para el cotizador')
            return []

    # ==================================================================
    # Descarga XLSX del cotizador — lista completa y pedido
    # ==================================================================
    # Ambos métodos devuelven bytes del .xlsx listos para stream desde
    # el controlador. Reciben un dict `state` con lo mismo que el
    # cotizador ya usa para calcular:
    #   partner_id, profile ({volumen, logistico, financiero}),
    #   promo_sim ({promo_id: {on, tier}}), show_iva (bool), cart
    #   ({product_id: qty}, solo para el pedido).
    # Se apoyan en get_tire_catalog y get_cotizador_promos (mismos
    # datos que ve el usuario en pantalla) para que el Excel NUNCA
    # difiera de lo que se muestra.

    @staticmethod
    def _format_dot(val):
        """DOT compacto: '2025-2026' → '25/26', '2025' → '25'.
        Misma lógica que formatDot() del frontend (constants.js)."""
        import re as _re
        if not val or val == 'N/A':
            return val or ''
        years = _re.findall(r'\d{2,4}', str(val))
        if not years:
            return str(val)
        shorts = list(dict.fromkeys(y[-2:] for y in years))  # unique, order preserved
        return '/'.join(shorts)

    IVA_RATE_MX = 0.16

    # Paleta de tintes para pintar renglones y celdas de promociones
    # en el XLSX — misma intención que promoColorFor del frontend
    # (constants.js): 10 colores perceptualmente distintos. El texto
    # oscuro se usa para el nombre de la promo en el encabezado del
    # Excel; el tinte claro (fill), para los renglones que aplican.
    PROMO_XLSX_COLORS = [
        {'fill': 'FBE0E4', 'text': 'B01F35'},  # rojo
        {'fill': 'DDF0E1', 'text': '1F6A34'},  # verde
        {'fill': 'DBE7FA', 'text': '234F9F'},  # azul
        {'fill': 'FCE4C8', 'text': 'B95E15'},  # naranja
        {'fill': 'EADCF3', 'text': '6A3D9E'},  # violeta
        {'fill': 'D3ECEC', 'text': '206060'},  # teal
        {'fill': 'F5DCEA', 'text': 'A3357E'},  # magenta
        {'fill': 'E7EACF', 'text': '5E6820'},  # oliva
        {'fill': 'DFDFF3', 'text': '3F439E'},  # índigo
        {'fill': 'FADED5', 'text': 'B33B21'},  # coral
    ]

    @api.model
    def _cotizador_promo_color(self, promo_id):
        n = (int(promo_id) if promo_id else 0) % len(self.PROMO_XLSX_COLORS)
        return self.PROMO_XLSX_COLORS[n]  # Mismo que IVA_RATE del frontend (constants.js)

    @api.model
    def _cotizador_policy_value(self, key, raw_value):
        """Devuelve únicamente porcentajes autorizados por categoría."""
        allowed = {
            'volumen': {0.0, 1.0, 2.0, 3.0},
            'logistico': {0.0, 2.0, 4.0},
            'financiero': {0.0, 2.0, 3.0},
        }
        try:
            value = float(raw_value or 0)
        except (TypeError, ValueError):
            return 0.0
        return value if value in allowed.get(key, {0.0}) else 0.0

    @api.model
    def _cotizador_policy_total_pct(self, profile):
        # ADITIVO, no cascada — coincide con policyFactor del frontend.
        p = profile or {}
        return sum(
            self._cotizador_policy_value(key, p.get(key))
            for key in ('volumen', 'logistico', 'financiero')
        )

    @api.model
    def _cotizador_active_promos(self, promo_sim, cart=None):
        # Filtra get_cotizador_promos por las que el usuario tiene
        # activadas EN EL SIMULADOR (radio seleccionado en el panel).
        # Devuelve [(promo_dict, tier_dict_or_None)].
        promo_sim = promo_sim or {}
        cart = cart or {}
        active = []
        for pr in self.get_cotizador_promos():
            sel = promo_sim.get(str(pr['id']))
            if not sel or not sel.get('on'):
                continue
            tier = None
            if pr['tiers']:
                idx = sel.get('tier')
                if idx is not None and 0 <= idx < len(pr['tiers']):
                    tier = pr['tiers'][idx]
            active.append((pr, tier))
        return active

    @api.model
    def _cotizador_promo_discount(self, product_row, promo, tier):
        """Descuento en $ que aporta UNA promo a UN producto (sobre
        lista). Devuelve 0 si el producto no aplica. Es la misma
        aritmética del simulador del frontend (_promoMaps)."""
        pid = product_row.get('product_id')
        if pid not in promo.get('product_ids', []):
            return 0.0
        lista = product_row.get('price') or 0.0
        pms_price = promo.get('pms_price_by_product', {}).get(str(pid))

        def percent_discount(percent):
            if pms_price is None:
                return lista * (percent / 100.0)
            engine = self.env['ztyres_promo.reward_engine']
            unit_reward = engine.percent_amount(pms_price, percent)
            return engine.round_money(
                unit_reward / (promo.get('pms_tax_factor') or 1.0)
            )
        if promo['promo_type'] == 'coupons':
            tmpl_id = product_row.get('tmpl_id')
            for c in promo.get('coupons', []):
                if c['tmpl_id'] == tmpl_id and c['amount'] > 0:
                    return c['amount']
            return 0.0
        # Tarjeta de regalo: NO es descuento sobre la llanta. El cliente
        # recibe una tarjeta por ese valor (docs/TARJETA_REGALO.md); con
        # gift_card_delivery='none', que es el default, ni siquiera se
        # emite NC. Va en su propia columna del Excel, vía
        # _cotizador_gift_card_amount. Misma regla en el frontend
        # (promoUnitDiscount, components.js) — si cambia una, cambia la
        # otra o el XLSX deja de cuadrar con la pantalla.
        if promo.get('reward_type') == 'gift_card':
            return 0.0
        # Un monto fijo pertenece al pedido/NC completo. Repartirlo aquí
        # por pieza inventaría un descuento unitario sin conocer cantidades
        # ni subtotales; por eso solo se explica en la barra izquierda.
        if promo.get('reward_type') == 'fixed_amount':
            return 0.0
        if tier and tier.get('product_discounts'):
            discount = tier['product_discounts'].get(str(pid), 0.0)
            return percent_discount(discount)
        # Key Size: en este nivel cobra su propia columna. Debe ir ANTES
        # del porcentaje general, y la misma regla vive en el frontend
        # (promoPercentForProduct, components.js).
        if (
            tier
            and tier.get('key_size_discount', 0) > 0
            and pid in promo.get('key_size_product_ids', [])
        ):
            return percent_discount(tier['key_size_discount'])
        if tier and tier.get('discount', 0) > 0:
            return percent_discount(tier['discount'])
        return 0.0

    @api.model
    def _cotizador_base_price(self, product_row):
        """Precio BASE de una llanta: lista menos Mayoreo. Es el precio
        que realmente se cotiza (no lista "pelona", que el cliente
        Bridgestone/Firestone nunca paga).

        OJO: política comercial y promociones NO se calculan sobre este
        número — se calculan sobre `lista`, cada una por su lado, y se
        restan junto con Mayoreo al final (ver `_cotizador_build_xlsx`).
        Calcularlas sobre `base` encadenaría Mayoreo con las demás
        (cascada) en vez de sumarlas (directo), cobrando de más. Mismo
        criterio que ``basePriceOf`` en components.js.
        """
        lista = float(product_row.get('price') or 0.0)
        mayoreo = lista * (float(product_row.get('mayoreo_discount') or 0.0) / 100.0)
        return max(lista - mayoreo, 0.0)

    @api.model
    def _cotizador_gift_card_amount(self, product_row, promo):
        """Monto de tarjeta de regalo por pieza para este producto.

        Beneficio aparte: el cliente recibe una tarjeta por ese valor y
        el precio de la llanta no cambia. Por eso NO entra a
        ``_cotizador_promo_discount`` y sí tiene columna propia.
        """
        if promo.get('reward_type') != 'gift_card':
            return 0.0
        if product_row.get('product_id') not in promo.get('product_ids', []):
            return 0.0
        tmpl_id = product_row.get('tmpl_id')
        for card in promo.get('coupons', []):
            if card['tmpl_id'] == tmpl_id and card['amount'] > 0:
                return float(card['amount'])
        return 0.0

    @api.model
    def _cotizador_promo_detail(self, promo, tier):
        """Descripción del tramo con la misma redacción del cotizador.

        Mantener este método sincronizado con ``PromoStrip.tierLabel`` en
        ``components.js``. El vendedor debe leer la misma frase en pantalla
        y en cualquiera de los dos Excel.
        """
        def whole(value):
            return int(round(float(value or 0)))

        def number(value):
            return f'{whole(value):,}'

        def percent(value):
            value = float(value or 0)
            return f'{value:g}%'

        if promo['promo_type'] == 'coupons':
            limit = promo.get('coupon_limit_qty') or 0
            suffix = f' (tope {whole(limit)} pzas).' if whole(limit) > 1 else '.'
            return 'Obtén un cupón por cada producto participante' + suffix
        if promo.get('reward_type') == 'gift_card':
            if not tier:
                return 'Selecciona una condición para simular el cupón.'
        if not tier:
            return 'Selecciona una condición para simular la promoción.'

        minimum = whole(tier.get('min'))
        maximum = whole(tier.get('max') or 999999999)
        unlimited = maximum >= 999999999
        if promo.get('reward_type') == 'fixed_amount':
            reward = f"${number(tier.get('fixed_amount'))} en nota de crédito"
        elif promo.get('reward_type') == 'gift_card':
            reward = 'un cupón'
        else:
            reward = percent(tier.get('discount'))

        qty_range = (
            f'{number(minimum)} pzas o más' if unlimited
            else f'de {number(minimum)} a {number(maximum)} pzas'
        )
        amount_range = (
            f'${number(minimum)} o más' if unlimited
            else f'de ${number(minimum)} a ${number(maximum)}'
        )

        if promo['promo_type'] == 'amount':
            min_qty = whole(tier.get('min_qty'))
            qty_rule = f' (mínimo {number(min_qty)} pzas)' if min_qty > 1 else ''
            return f'Obtén {reward} en compras {amount_range}{qty_rule}.'

        if promo['promo_type'] == 'amount_rim':
            rows = []
            for row in tier.get('rim_discounts', []):
                rim_from = whole(row.get('rim_from'))
                rim_to = whole(row.get('rim_to'))
                if rim_from <= 0:
                    continue
                rim_label = (
                    f'R{number(rim_from)}+' if rim_to >= 99
                    else (f'R{number(rim_from)}' if rim_from == rim_to
                          else f'R{number(rim_from)} a R{number(rim_to)}')
                )
                rows.append(f"{percent(row.get('discount'))} en {rim_label}")
            key_pct = float(tier.get('key_size_discount') or 0.0)
            if key_pct > 0:
                rows.append(f'{percent(key_pct)} en Key Sizes')
            breakdown = ' · '.join(rows)
            return (
                f'Compras {amount_range}: {breakdown}. Cálculo sobre PMS por código.' if breakdown
                else f'Compras {amount_range}: porcentaje según el rin, calculado sobre PMS por código.'
            )

        if promo['promo_type'] == 'monthly_volume':
            measures = whole(tier.get('minimum_products'))
            per_measure = whole(tier.get('minimum_qty_per_measure'))
            return (
                f'Obtén {reward} comprando {qty_range} '
                f'({number(measures)} medidas × {number(per_measure)} pzas c/u).'
            )

        if promo['promo_type'] == 'rim_quantity':
            import re
            rows = []
            for row in tier.get('rim_discounts', []):
                rims = [whole(value) for value in re.findall(r'\d+(?:\.\d+)?', str(row.get('rims') or ''))]
                if rims:
                    rows.append((min(rims), max(rims), float(row.get('discount') or 0)))
            rows.sort(key=lambda item: item[0])
            parts = []
            for index, (rim_min, rim_max, discount) in enumerate(rows):
                if index == len(rows) - 1 and rim_min >= 16:
                    rim_label = f'R{number(rim_min)}+'
                elif rim_min == rim_max:
                    rim_label = f'R{number(rim_min)}'
                else:
                    rim_label = f'R{number(rim_min)} a R{number(rim_max)}'
                parts.append(f'{percent(discount)} en {rim_label}')
            breakdown = ' y '.join(parts)
            return (
                f'Obtén {breakdown} comprando {qty_range}.' if breakdown
                else f'Obtén un porcentaje según el rin comprando {qty_range}.'
            )

        min_qty = whole(tier.get('min_qty'))
        qty_rule = f' (mínimo {number(min_qty)} pzas)' if min_qty > minimum else ''
        purchase = f'de {qty_range}' if unlimited else qty_range
        return f'Obtén {reward} en la compra {purchase}{qty_rule}.'

    @api.model
    def download_pricelist_xlsx(self, state):
        return self._cotizador_build_xlsx(state, mode='list')

    @api.model
    def download_order_xlsx(self, state):
        return self._cotizador_build_xlsx(state, mode='order')

    # Ruta del logo del módulo — PNG con fondo transparente (el JPEG
    # original traía fondo blanco que se veía como caja rectangular
    # encima del texto de las celdas vecinas; el PNG sin fondo se
    # apoya limpio sobre el color de la hoja).
    _COTIZADOR_LOGO_REL = 'ztyres_promotions/static/src/img/ztyres_logo.png'

    def _cotizador_build_xlsx(self, state, mode):
        """Construye el .xlsx del cotizador. `mode` es 'list' (todo el
        catálogo) o 'order' (solo las llantas del carrito). Todo el
        estilo va aquí para tener una sola fuente de verdad y evitar
        ramas divergentes entre lista y pedido.

        REDISEÑO v2.11 — claridad sobre qué es cada precio:
        - "Precio de lista" = precio publicado (sin política ni promo).
        - "Precio con condiciones aplicadas" = precio que quedaría SI
          se cumplen las condiciones de las promociones seleccionadas
          (tramo elegido) y aplicando la política comercial. NO es un
          "total con descuento" a secas — se aclara en el encabezado
          y en la leyenda debajo del título.
        - En el pedido, "Total si se cumplen las condiciones" es el
          subtotal del pedido a ese precio (mismo criterio).
        """
        from io import BytesIO
        from datetime import date
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        from openpyxl.utils import get_column_letter
        from openpyxl.drawing.image import Image as XLImage
        from odoo.modules.module import get_module_resource

        state = state or {}
        partner_id = int(state.get('partner_id') or 0)
        profile = state.get('profile') or {}
        promo_sim = state.get('promo_sim') or {}
        show_iva = bool(state.get('show_iva'))
        cart = {int(k): float(v) for k, v in (state.get('cart') or {}).items()}

        # partner_id=0 legítimo al descargar sin cliente.
        partner = self.env['res.partner'].sudo().browse(partner_id) if partner_id else self.env['res.partner']
        partner_name = partner.name if partner else ''
        partner_rfc = (partner.vat if partner else '') or ''

        catalog = self.env['product.template'].sudo().get_tire_catalog()
        if mode == 'list':
            catalog = self._cotizador_filter_catalog(catalog, state)
        active_promos = self._cotizador_active_promos(promo_sim, cart)
        policy_pct = self._cotizador_policy_total_pct(profile)
        iva_factor = 1 + self.IVA_RATE_MX if show_iva else 1.0

        # --- Paleta y estilos ------------------------------------------
        BRAND = 'F59E0B'   # ámbar (ztyres)
        BAND = 'FEF3C7'    # amarillo suave (banda del header de la tabla)
        ROW = 'FFFBEB'     # alterno de filas
        INK = '1F2937'     # texto principal
        SOFT = '6B7280'    # texto secundario
        LEG = 'FEF9C3'     # fondo de la leyenda
        LINE = 'E5E7EB'    # rejilla

        thin = Side(style='thin', color='E5E7EB')
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        title_font = Font(name='Arial', size=22, bold=True, color=INK)
        subtitle_font = Font(name='Arial', size=10, italic=True, color=SOFT)
        legend_font = Font(name='Arial', size=9, italic=True, color=INK)
        label_font = Font(name='Arial', size=9, bold=True, color=SOFT)
        value_font = Font(name='Arial', size=10, color=INK)
        strong_font = Font(name='Arial', size=10, bold=True, color=INK)
        head_font = Font(name='Arial', size=10, bold=True, color=INK)
        cell_font = Font(name='Arial', size=10, color=INK)
        promo_font = Font(name='Arial', size=10, color=INK)
        head_fill = PatternFill('solid', fgColor=BAND)
        row_fill = PatternFill('solid', fgColor=ROW)
        legend_fill = PatternFill('solid', fgColor=LEG)

        currency_fmt = '#,##0.00'  # Número plano, sin símbolo $

        wb = Workbook()
        ws = wb.active
        if mode == 'list':
            ws.title = 'Precios Con IVA' if show_iva else 'Precios Sin IVA'
        else:
            ws.title = 'Pedido Con IVA' if show_iva else 'Pedido Sin IVA'
        ws.sheet_view.showGridLines = False
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.page_margins.left = 0.25
        ws.page_margins.right = 0.25
        ws.page_margins.top = 0.45
        ws.page_margins.bottom = 0.45

        # --- Columnas de la tabla --------------------------------------
        # Cambio de nombres para evitar la ambigüedad de "total con
        # descuento" — cada columna dice exactamente qué contiene.
        headers = [
            'Código', 'Tier', 'Medida', 'Marca', 'Modelo',
            'Cap/Cara', 'Vel/Ind', 'Seg', 'Tipo', 'DOT', 'Eq. Original',
        ]
        # "Precio" (antes "Precio de lista") porque en Bridgestone/
        # Firestone de la lista Mayoreo ya trae aplicado el −10%: es el
        # precio desde el que se calcula todo, no el publicado.
        # "Tarjeta de regalo" va en columna propia y NUNCA dentro del
        # precio — el cliente recibe la tarjeta, la llanta no baja.
        if mode == 'list':
            headers += [
                'Inv.',
                'Precio',
                'Pr Promo',
                'Tarjeta de regalo',
            ]
        else:
            headers += [
                'Cant.',
                'Precio',
                'Pr Promo',
                '% Desc.',
                'Subtotal',
                'Tarjeta de regalo',
                'NC estimada',
            ]
        n_cols = len(headers)
        last_col_letter = get_column_letter(n_cols)

        # --- Encabezado con logo y título ------------------------------
        # Alineación del logo — tres reglas para que NUNCA invada el
        # texto del título:
        # (a) Se fija el ANCHO de columnas A-D antes de embeber el
        #     logo (Excel calcula el ancho en "character units" ≈ 7px).
        # (b) Se escala el logo para que quepa exactamente en A1:D3
        #     (4 cols × ancho, 3 filas × alto).
        # (c) Título arranca en la columna E — nunca se solapa con la
        #     imagen porque las columnas A-D están reservadas para ella.
        LOGO_COL_WIDTH = 12        # ancho de A, B, C y D
        LOGO_ROW_HEIGHT = 28       # alto de filas 1, 2 y 3
        for col_letter in ('A', 'B', 'C', 'D'):
            ws.column_dimensions[col_letter].width = LOGO_COL_WIDTH
        for row_i in (1, 2, 3):
            ws.row_dimensions[row_i].height = LOGO_ROW_HEIGHT

        logo_path = get_module_resource(*self._COTIZADOR_LOGO_REL.split('/'))
        if logo_path:
            try:
                img = XLImage(logo_path)
                # Logo al 55% del box — chico y proporcionado.
                box_w = LOGO_COL_WIDTH * 4 * 7
                box_h = LOGO_ROW_HEIGHT * 3 * 1.33
                scale = min(box_w / img.width, box_h / img.height, 1.0) * 0.55
                img.width = int(img.width * scale)
                img.height = int(img.height * scale)
                # Centrar: anclar en B1 (salta la col A como margen
                # izquierdo) — openpyxl solo acepta celdas como anchor.
                img.anchor = 'A1'
                ws.add_image(img)
            except Exception:
                _logger.warning('No se pudo embeber el logo en el XLSX')

        title_col_start = 5  # A-D reservadas para el logo
        ws.merge_cells(start_row=1, start_column=title_col_start,
                       end_row=2, end_column=n_cols)
        title_cell = ws.cell(row=1, column=title_col_start,
                             value='LISTA DE PRECIOS' if mode == 'list' else 'PEDIDO')
        title_cell.font = title_font
        title_cell.alignment = Alignment(vertical='center', horizontal='left',
                                         indent=1, readingOrder=1)

        ws.merge_cells(start_row=3, start_column=title_col_start,
                       end_row=3, end_column=n_cols)
        subtitle_cell = ws.cell(row=3, column=title_col_start,
                                value='Folio VTA-FO-03 · Versión 01 · Fecha ' +
                                      date.today().strftime('%d/%m/%Y'))
        subtitle_cell.font = subtitle_font
        subtitle_cell.alignment = Alignment(vertical='center', horizontal='right',
                                            readingOrder=1)

        # --- Bloque de contexto (rows 4-6): cliente, RFC, IVA, política -
        r = 4
        # Cliente y RFC se dejan SIEMPRE vacíos en el XLSX por ahora,
        # aunque el usuario haya seleccionado un cliente en el
        # frontend (la selección sigue disponible allí para calcular
        # NC, política y promos — solo no se pinta en el archivo).
        # Cuando se decida mostrar el cliente en el Excel, se cambia
        # '' por partner_name / partner_rfc.
        meta_rows = [
            ('Cliente', '',
             'Precios', 'CON IVA (16%)' if show_iva else 'SIN IVA'),
            ('RFC', '',
             'Política comercial',
             self._cotizador_policy_summary(profile, policy_pct)),
        ]
        for lbl1, val1, lbl2, val2 in meta_rows:
            # Altura explícita del archivo de referencia aprobado.
            ws.row_dimensions[r].height = 15
            ws.cell(row=r, column=1, value=lbl1).font = label_font
            c = ws.cell(row=r, column=2, value=val1); c.font = value_font
            ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=6)
            c = ws.cell(row=r, column=7, value=lbl2); c.font = label_font
            c.alignment = Alignment(horizontal='right', vertical='center',
                                    wrap_text=False, shrink_to_fit=False)
            ws.merge_cells(start_row=r, start_column=7, end_row=r, end_column=8)
            # Estructura del archivo de referencia aprobado por usuario:
            # etiqueta combinada G:H y valor combinado desde I hasta la
            # última columna, ambos alineados a la derecha.
            c = ws.cell(row=r, column=9, value=val2); c.font = strong_font
            c.alignment = Alignment(horizontal='right', vertical='center',
                                    wrap_text=True, shrink_to_fit=False)
            ws.merge_cells(start_row=r, start_column=9, end_row=r, end_column=n_cols)
            r += 1

        # --- Promociones (una por fila, con su color) ----
        # Pedido: solo las que apliquen a al menos 1 producto del carrito.
        # Lista: todas las seleccionadas.
        if mode == 'order' and cart:
            cart_pids = set(cart.keys())
            display_promos = [
                (pr, tier) for pr, tier in active_promos
                if any(pid in cart_pids for pid in pr.get('product_ids', []))
            ]
        else:
            display_promos = active_promos
        promo_label = 'Promociones que aplican a este pedido' if mode == 'order' else 'Promociones seleccionadas'
        ws.cell(row=r, column=1, value=promo_label).font = label_font
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n_cols)
        r += 1
        if display_promos:
            for pr, tier in display_promos:
                detail = self._cotizador_promo_detail(pr, tier)
                color = self._cotizador_promo_color(pr['id'])
                cell = ws.cell(
                    row=r, column=1,
                    value=f"• {pr.get('display_label') or pr['name']} — {detail}")
                cell.font = Font(name='Arial', size=10, bold=True, color=color['text'])
                cell.fill = PatternFill('solid', fgColor=color['fill'])
                cell.alignment = Alignment(indent=1, wrap_text=True, vertical='center')
                ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n_cols)
                ws.row_dimensions[r].height = 30 if len(detail) > 85 else 22
                r += 1
        else:
            msg = ('Ninguna promoción aplica a este pedido' if mode == 'order'
                   else '(Ninguna promoción seleccionada — los precios son de lista)')
            cell = ws.cell(row=r, column=1, value=msg)
            cell.font = promo_font
            cell.alignment = Alignment(indent=1)
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n_cols)
            r += 1

        # --- Leyenda que EVITA ambigüedad --------------------------------
        r += 1
        legend_msg = (
            'La columna "Precio" ya incluye la política Mayoreo (−10%) en '
            'las llantas que aplican; sobre ese precio se calculan la '
            'política comercial y las promociones. La columna "Pr Promo" '
            'es el precio que quedaría SI se cumplen las condiciones de '
            'las promociones seleccionadas (tramo elegido). La "Tarjeta '
            'de regalo" es un valor que el cliente recibe aparte: NO '
            'descuenta el precio de las llantas ni el total del pedido.'
        )
        cell = ws.cell(row=r, column=1, value=legend_msg)
        cell.font = legend_font
        cell.fill = legend_fill
        cell.alignment = Alignment(wrap_text=True, vertical='center', indent=1)
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n_cols)
        ws.row_dimensions[r].height = 48
        r += 2

        # --- Header de la tabla ----------------------------------------
        header_row = r
        for c, name in enumerate(headers, start=1):
            cell = ws.cell(row=header_row, column=c, value=name)
            cell.font = head_font
            cell.fill = head_fill
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        ws.row_dimensions[header_row].height = 28

        # --- Cuerpo ----------------------------------------------------
        if mode == 'list':
            rows_data = catalog
        else:
            rows_data = [p for p in catalog if p['product_id'] in cart]

        nc_per_product = {}
        nc_preview = None
        if mode == 'order' and cart:
            partner_rec = partner if partner else self.env['res.partner']
            promo_lines_all = self._get_promo_lines_from_cart(cart)
            nc_preview = self._ztyres_promo_nc_preview(partner_rec, promo_lines_all)
            if nc_preview:
                nc_per_product = {int(k): v for k, v in (nc_preview.get('per_product') or {}).items()}

        r = header_row + 1
        order_totals_lists = {'lista': [], 'promo': [], 'sub': [], 'nc': [], 'gift': [], 'policy': []}
        for i, p in enumerate(rows_data):
            # Descuento de promo: suma sobre lista de TODAS las promos
            # activas que aportan (misma lógica del simulador del UI).
            promo_disc = 0.0
            gift_card = 0.0
            promos_hit_colors = []
            for pr, tier in active_promos:
                d = self._cotizador_promo_discount(p, pr, tier)
                gift_card += self._cotizador_gift_card_amount(p, pr)
                if d > 0:
                    promo_disc += d
                    promos_hit_colors.append(self._cotizador_promo_color(pr['id']))
            # Mayoreo, política y promos se calculan cada uno SOBRE
            # LISTA (independientes entre sí) y se restan juntos una
            # sola vez. Antes la política se calculaba sobre `base`
            # (lista ya con Mayoreo aplicado), lo que encadenaba los
            # dos descuentos (cascada: lista×0.9×0.98) en vez de
            # sumarlos (directo: lista×(1-0.10-0.02)) — con Mayoreo
            # +2% de política el cliente pagaba más de lo que debía.
            lista = float(p.get('price') or 0.0)
            base = self._cotizador_base_price(p)
            policy_disc = lista * (policy_pct / 100.0)
            final = max(base - policy_disc - promo_disc, 0.0)
            ahorro = max(base - final, 0.0)

            cells = [
                p.get('code') or '',
                p.get('tier') or '',
                p.get('medida') or '',
                p.get('brand') or '',
                p.get('model') or '',
                '-'.join([x for x in (p.get('layer'), p.get('face')) if x]) or '',
                ''.join([x for x in (p.get('speed'), p.get('index_of_load')) if x]) or '',
                p.get('segment') or '',
                p.get('type') or '',
                self._format_dot(p.get('dot_range')),  # DOT compacto (25/26)
                p.get('original_equipment') or '',
            ]
            if mode == 'list':
                row_values = cells + [
                    p.get('free_qty') if p.get('free_qty') is not None else '',
                    base * iva_factor,
                    final * iva_factor if ahorro > 0 else '',
                    gift_card * iva_factor if gift_card > 0 else '',
                ]
            else:
                qty = cart.get(p['product_id']) or 0
                subtotal = final * qty
                nc = nc_per_product.get(p['product_id'], 0.0)
                ahorro_unit = base - final
                pct_desc = (ahorro_unit / base * 100) if base > 0 else 0
                row_values = cells + [
                    qty, base * iva_factor,
                    final * iva_factor if ahorro_unit > 0.005 else '',
                    round(pct_desc, 1) if ahorro_unit > 0.005 else '',
                    subtotal * iva_factor,
                    gift_card * qty * iva_factor if gift_card > 0 else '',
                    nc * iva_factor if nc > 0 else '',
                ]
                order_totals_lists['lista'].append(base * qty)
                order_totals_lists['sub'].append(subtotal)
                order_totals_lists['gift'].append(gift_card * qty)
                order_totals_lists['policy'].append(policy_disc * qty)

            # Reparto de tinte por celda si hay ≥1 promo aplicable en
            # esta fila — mismo criterio que el UI (bloques iguales de
            # columnas, uno por promo).
            cell_fills = []
            if promos_hit_colors:
                n = len(promos_hit_colors)
                sizes = [n_cols // n + (1 if k < n_cols % n else 0) for k in range(n)]
                for k, size in enumerate(sizes):
                    cell_fills.extend([promos_hit_colors[k]['fill']] * size)

            for c, v in enumerate(row_values, start=1):
                cell = ws.cell(row=r, column=c, value=v)
                cell.font = cell_font
                cell.border = border
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    cell.alignment = Alignment(horizontal='right', vertical='center')
                    column_name = headers[c - 1]
                    if column_name in {'Precio', 'Pr Promo', 'Subtotal',
                                       'NC estimada', 'Tarjeta de regalo'}:
                        cell.number_format = currency_fmt
                    elif column_name == '% Desc.':
                        cell.number_format = '0.0"%"'
                    elif column_name == 'Cant.':
                        cell.number_format = '#,##0.##'
                    else:
                        cell.number_format = '#,##0'
                else:
                    cell.alignment = Alignment(horizontal='left', vertical='center')
                if cell_fills:
                    cell.fill = PatternFill('solid', fgColor=cell_fills[c - 1])
                elif i % 2 == 1:
                    cell.fill = row_fill
            r += 1

        # --- Totales (solo pedido) --------------------------------------
        if mode == 'order' and rows_data:
            r += 1
            lista_total = sum(order_totals_lists['lista'])
            sub_total = sum(order_totals_lists['sub'])
            desc_total = lista_total - sub_total

            thick_top = Border(top=Side(style='medium', color=BRAND))
            def total_row(row, label, val, strong=False, fill=False, top_border=False):
                # Cuatro columnas para la etiqueta: evita que textos largos
                # como "TOTAL SI SE CUMPLEN LAS CONDICIONES" se recorten.
                label_start = max(n_cols - 4, 1)
                lbl_cell = ws.cell(row=row, column=label_start, value=label)
                lbl_cell.font = strong_font if strong else label_font
                lbl_cell.alignment = Alignment(horizontal='left', vertical='center',
                                               wrap_text=True, indent=1,
                                               readingOrder=1)
                ws.merge_cells(start_row=row, start_column=label_start,
                               end_row=row, end_column=n_cols - 1)
                v_cell = ws.cell(row=row, column=n_cols, value=val)
                v_cell.font = Font(name='Arial', size=12 if strong else 10,
                                   bold=strong, color=INK)
                v_cell.number_format = currency_fmt
                v_cell.alignment = Alignment(horizontal='right', vertical='center')
                if fill:
                    lbl_cell.fill = head_fill
                    v_cell.fill = head_fill
                if top_border:
                    lbl_cell.border = thick_top
                    v_cell.border = thick_top
                ws.row_dimensions[row].height = 28 if strong else 22

            total_row(r, 'Total a precio base (sin promociones)',
                      lista_total * iva_factor, top_border=True)
            r += 1
            if desc_total > 0.005:
                pct_total = (desc_total / lista_total * 100) if lista_total > 0 else 0
                # Primero se muestra el desglose; "Ahorro potencial" va al
                # final porque es la suma de política + promociones.
                if policy_pct > 0:
                    # Suma real de lo aplicado renglón por renglón
                    # (sobre lista, no sobre lista_total que ya trae
                    # Mayoreo restado) — evita el mismo doble descuento
                    # que se corrigió arriba.
                    policy_saving = sum(order_totals_lists['policy'])
                    detail_start = max(n_cols - 4, 1)
                    detail_cell = ws.cell(
                        row=r, column=detail_start,
                        value=f'   Política comercial (−{policy_pct:g}%)')
                    detail_cell.font = Font(name='Arial', size=9, color=SOFT)
                    detail_cell.alignment = Alignment(horizontal='left', indent=1,
                                                      readingOrder=1)
                    ws.merge_cells(start_row=r, start_column=detail_start,
                                   end_row=r, end_column=n_cols - 1)
                    c = ws.cell(row=r, column=n_cols, value=-policy_saving * iva_factor)
                    c.font = Font(name='Arial', size=9, color=SOFT)
                    c.number_format = currency_fmt
                    r += 1
                for pr, tier in active_promos:
                    promo_saving = sum(
                        self._cotizador_promo_discount(p, pr, tier) * (cart.get(p['product_id']) or 0)
                        for p in rows_data
                    )
                    if promo_saving > 0.005:
                        color = self._cotizador_promo_color(pr['id'])
                        detail_start = max(n_cols - 4, 1)
                        detail_cell = ws.cell(
                            row=r, column=detail_start,
                            value=f'   {pr.get("display_label") or pr["name"]}')
                        detail_cell.font = Font(name='Arial', size=9, bold=True,
                                                color=color['text'])
                        detail_cell.alignment = Alignment(horizontal='left', indent=1,
                                                          readingOrder=1)
                        ws.merge_cells(start_row=r, start_column=detail_start,
                                       end_row=r, end_column=n_cols - 1)
                        c = ws.cell(row=r, column=n_cols, value=-promo_saving * iva_factor)
                        c.font = Font(name='Arial', size=9, color=color['text'])
                        c.number_format = currency_fmt
                        r += 1
                total_row(r, f'Ahorro potencial ({pct_total:.1f}%)',
                          -desc_total * iva_factor, strong=True)
                r += 1
            r += 1
            total_row(r, 'TOTAL SI SE CUMPLEN LAS CONDICIONES',
                      sub_total * iva_factor, strong=True, fill=True)
            r += 2

            # Tarjeta de regalo: valor que el cliente RECIBE, no un
            # descuento. Va después del total y con su propio recuadro
            # para que nadie lo reste del precio de las llantas.
            gift_total = sum(order_totals_lists['gift'])
            if gift_total > 0.005:
                gift_head = ws.cell(
                    row=r, column=1,
                    value=('Tarjeta de regalo — el cliente la recibe aparte; '
                           'NO descuenta el precio de las llantas'))
                gift_head.font = strong_font
                gift_head.fill = PatternFill('solid', fgColor='FCE4C8')
                ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n_cols)
                r += 1
                total_row(r, 'Valor total de tarjeta de regalo',
                          gift_total * iva_factor, strong=True)
                r += 2

            if nc_preview and nc_preview.get('total', 0) > 0:
                # Bloque de NC — aparte del total del pedido, con su
                # propio recuadro; es un beneficio POSTERIOR (nota de
                # crédito), no un descuento de la cotización.
                nc_head = ws.cell(row=r, column=1,
                                  value='Promoción ganada — se emite como Nota de Crédito al facturar')
                nc_head.font = strong_font
                nc_head.fill = PatternFill('solid', fgColor='DDF0E1')
                ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n_cols)
                r += 1
                for it in nc_preview.get('items', []):
                    detail = f"• {it['name']}: ${it['amount']:,.2f}"
                    if it.get('discount_percent'):
                        detail += f" ({it['discount_percent']}%)"
                    ws.cell(row=r, column=1, value=detail).font = promo_font
                    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n_cols)
                    r += 1
                total_row(r, 'NC estimada total', nc_preview['total'] * iva_factor, strong=True)
                r += 1

        # --- Términos y condiciones (solo pedido) ----------------------
        # Resumen de qué políticas y promociones se aplicaron, para que
        # el documento se explique solo sin necesidad de consultar la
        # pantalla del cotizador.
        if mode == 'order':
            r += 2
            terms_font = Font(name='Arial', size=9, color=SOFT)
            terms_bold = Font(name='Arial', size=9, bold=True, color=INK)
            terms_fill = PatternFill('solid', fgColor='F9FAFB')

            cell = ws.cell(row=r, column=1, value='TÉRMINOS Y CONDICIONES APLICADAS')
            cell.font = Font(name='Arial', size=10, bold=True, color=INK)
            cell.fill = PatternFill('solid', fgColor=BAND)
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n_cols)
            r += 1

            # Política comercial
            cell = ws.cell(row=r, column=1,
                           value='Política comercial: ' + self._cotizador_policy_summary(profile, policy_pct))
            cell.font = terms_bold
            cell.fill = terms_fill
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n_cols)
            r += 1

            # Precios
            cell = ws.cell(row=r, column=1,
                           value='Precios: ' + ('CON IVA (16%)' if show_iva else 'SIN IVA'))
            cell.font = terms_bold
            cell.fill = terms_fill
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n_cols)
            r += 1

            # Promociones aplicadas
            applicable = [
                (pr, tier) for pr, tier in active_promos
                if any(pid in set(cart.keys()) for pid in pr.get('product_ids', []))
            ] if cart else active_promos
            if applicable:
                cell = ws.cell(row=r, column=1, value='Promociones que se deben cumplir para que apliquen los precios de la columna "Pr Promo":')
                cell.font = terms_bold
                cell.fill = terms_fill
                ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n_cols)
                r += 1
                for pr, tier in applicable:
                    detail = self._cotizador_promo_detail(pr, tier)
                    color = self._cotizador_promo_color(pr['id'])
                    cell = ws.cell(row=r, column=1, value=f"  • {pr['name']} — {detail}")
                    cell.font = Font(name='Arial', size=9, bold=True, color=color['text'])
                    cell.fill = PatternFill('solid', fgColor=color['fill'])
                    cell.alignment = Alignment(wrap_text=True, vertical='center', indent=1)
                    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n_cols)
                    ws.row_dimensions[r].height = 30 if len(detail) > 85 else 22
                    r += 1
            else:
                cell = ws.cell(row=r, column=1, value='Sin promociones aplicables — los precios son de lista.')
                cell.font = terms_font
                cell.fill = terms_fill
                ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n_cols)
                r += 1

            # Nota legal
            r += 1
            cell = ws.cell(row=r, column=1,
                           value='Los precios y promociones están sujetos a cambios sin previo aviso. '
                                 'Los descuentos de la columna "Pr Promo" aplican únicamente si se cumplen '
                                 'las condiciones de las promociones seleccionadas.')
            cell.font = Font(name='Arial', size=8, italic=True, color=SOFT)
            cell.alignment = Alignment(wrap_text=True, vertical='center')
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=n_cols)
            ws.row_dimensions[r].height = 28

        # --- Anchos de columna -----------------------------------------
        # Anchos de columna del archivo de referencia (VTA-FO-03)
        widths = {
            'Código': 13, 'Tier': 7, 'Medida': 14, 'Marca': 16, 'Modelo': 22,
            'Cap/Cara': 11, 'Vel/Ind': 10, 'Seg': 8, 'Tipo': 10, 'DOT': 8,
            'Eq. Original': 18, 'Inv.': 9, 'Cant.': 9,
            'Precio': 16, 'Pr Promo': 15,
            '% Desc.': 10, 'Subtotal': 16,
            'Tarjeta de regalo': 17, 'NC estimada': 15,
        }
        for c, name in enumerate(headers, start=1):
            ws.column_dimensions[get_column_letter(c)].width = widths.get(name, 12)

        ws.freeze_panes = ws.cell(row=header_row + 1, column=1)
        if rows_data:
            ws.auto_filter.ref = f'A{header_row}:{last_col_letter}{header_row + len(rows_data)}'
        ws.print_title_rows = f'{header_row}:{header_row}'
        ws.print_area = f'A1:{last_col_letter}{r}'
        ws.sheet_view.zoomScale = 85

        buf = BytesIO()
        wb.save(buf)
        return buf.getvalue()

    @api.model
    def _cotizador_filter_catalog(self, catalog, state):
        """Aplica al XLSX de lista exactamente la búsqueda y los cinco
        filtros visibles del catálogo."""
        import re

        allowed_fields = {'brand', 'tier', 'segment', 'type', 'model'}
        filters = state.get('sf_filters') or {}
        search = str(state.get('search') or '').strip().lower()

        def normalize(value):
            value = str(value or '').lower()
            value = re.sub(r'[\s\-/.]+', '', value)
            return re.sub(r'r(?=\d)', '', value)

        search_normalized = normalize(search)
        result = []
        for product in catalog:
            matches_filters = all(
                not values
                or str(product.get(field) or '') in {str(value) for value in values}
                for field, values in filters.items()
                if field in allowed_fields
            )
            if not matches_filters:
                continue

            searchable = '{} {} {} {} R{}'.format(
                product.get('code') or '',
                product.get('brand') or '',
                product.get('name') or '',
                product.get('medida') or '',
                product.get('rim') or '',
            ).lower()
            if search and search not in searchable and search_normalized not in normalize(searchable):
                continue
            result.append(product)
        return result

    def _cotizador_policy_summary(self, profile, policy_pct):
        """Resumen legible de la política comercial: los tres % sumados
        con el total al final. Si no hay ninguno, dice "sin descuentos"."""
        parts = []
        for k, lbl in [('volumen', 'Volumen'), ('logistico', 'Logístico'), ('financiero', 'Financiero')]:
            pct = self._cotizador_policy_value(k, profile.get(k))
            if pct > 0:
                parts.append(f'{lbl} −{pct:g}%')
        if not parts:
            return 'sin descuentos'
        return ' + '.join(parts) + f'  (total −{policy_pct:g}%)'

    def _get_promo_lines_from_cart(self, cart):
        # Adaptador cart→PromoLine, mismo shape que _get_promo_lines
        products = self.env['product.product'].sudo().browse(list(cart.keys())).exists()
        lines = []
        for i, prod in enumerate(products):
            qty = cart.get(prod.id) or 0
            if qty > 0:
                lines.append(PromoLine(i + 1, prod, qty, prod.lst_price))
        return lines

    def _ztyres_promo_nc_preview(self, partner, promo_lines):
        """Evalúa las promociones aprobadas/vigentes de ztyres_promo
        (Notas de Crédito) contra las líneas del cotizador.

        Devuelve None si ztyres_promo no está instalado, si ninguna
        promoción aplica, o si algo falla — el cotizador NUNCA debe
        romperse por este cálculo extra (por eso el try/except ancho
        con log): si el puente falla, la cotización sale igual que
        antes, solo sin el bloque de "Promoción ganada".

        Respeta las mismas reglas del mixin: solo promociones con
        status Aprobada/Confirmada, dentro de su vigencia, con el
        partner no excluido, y con promo_display_mode distinto de
        'no mostrar'. Hereda también sus simplificaciones documentadas:
        no evalúa acumulados por grupo de clientes ni el tope mensual
        de cupones (esos requieren histórico, no un solo documento).
        """
        if 'ztyres_promo.document_promo_mixin' not in self.env:
            return None
        try:
            mixin = self.env['ztyres_promo.document_promo_mixin']
            doc_date = fields.Date.context_today(self)
            fake_lines = _NcEvalLines(
                _NcEvalLine(pl.id, pl.product_id, pl.qty, pl.price_unit)
                for pl in promo_lines
            )
            results = mixin._evaluate_promotions(
                partner, doc_date, fake_lines, 'product_uom_qty'
            )
            # Mismo criterio que compute_promo_ganada: las promociones
            # configuradas como 'no mostrar' no aparecen en ningún lado.
            results = [
                r for r in results
                if (r['promo'].promo_display_mode or 'none') != 'none'
            ]
            if not results:
                return None

            id_to_product = {pl.id: pl.product_id.id for pl in promo_lines}
            items = []
            per_product = {}          # pid → monto TOTAL de NC en esa llanta
            per_product_parts = {}    # pid → [{'promo','amount'}]  desglose por promo
            for r in results:
                promo = r['promo']
                promo_name = promo.nombre or promo.display_name
                is_gift_card = promo._effective_reward_type() == 'gift_card'
                # La tarjeta/cupón no genera NC, pero sí reduce el precio
                # efectivo mostrado por producto. El motor la devuelve CON
                # IVA en gift_card_by_line; este adaptador trabaja SIN IVA.
                effective_amount = (
                    self.env['ztyres_promo.reward_engine'].untaxed(
                        r.get('gift_card_amount', 0.0)
                    )
                    if is_gift_card
                    else r['ganado']
                )
                items.append({
                    'id': promo.id,
                    'name': promo_name,
                    'discount_percent': r['discount_percent'],
                    'amount': effective_amount,
                    # El texto lo redacta quien configuró la promoción
                    # (promo_ganada_message con {promocion}/{monto}/
                    # {porcentaje}) — mismo mensaje que verá después
                    # en la cotización/factura de Odoo.
                    'message': mixin._render_promo_message(
                        promo,
                        r['ganado'],
                        r['discount_percent'],
                        gift_card_amount=r.get('gift_card_amount', 0.0),
                    ),
                })
                amount_by_line = r.get('line_ganado_map') or {}
                if is_gift_card:
                    amount_by_line = {
                        line_id: self.env[
                            'ztyres_promo.reward_engine'
                        ].untaxed(amount)
                        for line_id, amount in (
                            r.get('gift_card_by_line') or {}
                        ).items()
                    }
                for line_id, ganado in amount_by_line.items():
                    pid = id_to_product.get(line_id)
                    if pid and ganado > 0:
                        per_product[pid] = per_product.get(pid, 0.0) + ganado
                        per_product_parts.setdefault(pid, []).append({
                            'promo_id': promo.id,
                            'promo': promo_name,
                            'amount': ganado,
                        })

            return {
                'total': sum(i['amount'] for i in items),
                'items': items,
                'per_product': per_product,
                'per_product_parts': per_product_parts,
            }
        except Exception:
            _logger.exception(
                'Fallo evaluando promociones NC (ztyres_promo) en el '
                'preview del cotizador — se responde sin ese bloque.'
            )
            return None
