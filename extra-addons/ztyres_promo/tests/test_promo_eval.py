# -*- coding: utf-8 -*-
"""Tests del motor de promociones (`evaluate_document`).

Correr con:
    odoo -d TU_BD -u ztyres_promo --test-enable --stop-after-init \
         --workers=0 --log-level=test

Todo lo que estos tests afirman está calculado A MANO desde la regla de
negocio, no copiado de la salida del motor. Si un test falla, primero
revisa el número esperado: puede que el bug esté en el test, pero
también puede que el motor esté mal y el test lo esté detectando.
"""

from odoo.tests import tagged

from .common import PromoTestCommon
from ..models.ztyres_promo_config import (
    BASE_PMS,
    GIFT_CARD_DELIVERY_NC,
    GIFT_CARD_DELIVERY_NONE,
    GIFT_CARD_SOURCE_PRODUCT,
    GIFT_CARD_SOURCE_TIER,
    POLICY_AMOUNT,
    POLICY_QUANTITY,
    POLICY_RIM_QUANTITY,
    PRICE_TAXED,
    PRICE_UNTAXED,
    REWARD_FIXED_AMOUNT,
    REWARD_GIFT_CARD,
    SCOPE_ATTRIBUTE_COMBINATION,
    SCOPE_RIM_POLICY,
    SCOPE_TIRE_FEATURE,
    UNLIMITED,
)


@tagged('post_install', '-at_install')
class TestPromoEval(PromoTestCommon):

    # ------------------------------------------------------------------
    # Caso 1 — Alcance OR + política por Cantidad
    # ------------------------------------------------------------------
    def test_scope_or_cuenta_solo_las_marcas_del_alcance(self):
        """Goodyear O Pirelli participan; Dunlop no debe sumar nada.

        Carrito: 30 GY + 20 PI + 10 DU, todas a $1,000.
        Participan 50 piezas -> tramo 50..199 -> 5%.
        Base = 50 x 1,000 = 50,000  ->  ganado = 2,500.
        Las 10 Dunlop no entran ni al tramo ni a la base.
        """
        promo = self._promo(
            promo_conditions=SCOPE_TIRE_FEATURE,
            promo_type=POLICY_QUANTITY,
            brand_ids=[(6, 0, [self.goodyear.id, self.pirelli.id])],
            policy_line_qty_ids=[
                (0, 0, {'lower_limit': 1, 'upper_limit': 49, 'discount': 3.0}),
                (0, 0, {'lower_limit': 50, 'upper_limit': 199, 'discount': 5.0}),
                (0, 0, {'lower_limit': 200, 'upper_limit': UNLIMITED, 'discount': 8.0}),
            ],
        )
        order = self._order([
            (self.p_goodyear_16, 30, 1000.0),
            (self.p_pirelli_17, 20, 1000.0),
            (self.p_dunlop_18, 10, 1000.0),
        ])

        result = self._evaluate(promo, order)

        self.assertIsNotNone(result, 'La promoción debería aplicar')
        self.assertEqual(result['qty'], 50)
        self.assertEqual(result['amount'], 50000.0)
        self.assertEqual(result['discount_percent'], 5.0)
        self.assertAlmostEqual(result['ganado'], 2500.0, places=2)
        self.assertEqual(
            len(result['lines']), 2,
            'Dunlop no debe aparecer en el desglose por producto',
        )

    # ------------------------------------------------------------------
    # Caso 2 — Alcance AND exige al menos DOS criterios
    # ------------------------------------------------------------------
    def test_scope_and_con_un_solo_criterio_no_aplica(self):
        """`_matches_scope` devuelve False si hay menos de 2 criterios.

        Es una salvaguarda deliberada: un AND con un solo eje sería un
        OR disfrazado. Vale la pena tenerlo fijado por un test, porque
        desde la interfaz se ve como una promoción bien configurada.
        """
        promo = self._promo(
            promo_conditions=SCOPE_ATTRIBUTE_COMBINATION,
            promo_type=POLICY_QUANTITY,
            brand_ids=[(6, 0, [self.dunlop.id])],
            policy_line_qty_ids=[
                (0, 0, {'lower_limit': 1, 'upper_limit': UNLIMITED, 'discount': 5.0}),
            ],
        )
        order = self._order([(self.p_dunlop_18, 40, 1000.0)])

        self.assertIsNone(self._evaluate(promo, order))

    def test_scope_and_con_dos_criterios_si_aplica(self):
        """Dunlop Y Premium: el producto cumple ambos -> 5% de 40,000."""
        promo = self._promo(
            promo_conditions=SCOPE_ATTRIBUTE_COMBINATION,
            promo_type=POLICY_QUANTITY,
            brand_ids=[(6, 0, [self.dunlop.id])],
            tier_ids=[(6, 0, [self.tier_premium.id])],
            policy_line_qty_ids=[
                (0, 0, {'lower_limit': 1, 'upper_limit': UNLIMITED, 'discount': 5.0}),
            ],
        )
        order = self._order([(self.p_dunlop_18, 40, 1000.0)])

        result = self._evaluate(promo, order)

        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['ganado'], 2000.0, places=2)

    def test_scope_and_no_matchea_si_falla_un_solo_eje(self):
        """Dunlop Y Value: la Dunlop del fixture es Premium -> no aplica."""
        promo = self._promo(
            promo_conditions=SCOPE_ATTRIBUTE_COMBINATION,
            promo_type=POLICY_QUANTITY,
            brand_ids=[(6, 0, [self.dunlop.id])],
            tier_ids=[(6, 0, [self.tier_value.id])],
            policy_line_qty_ids=[
                (0, 0, {'lower_limit': 1, 'upper_limit': UNLIMITED, 'discount': 5.0}),
            ],
        )
        order = self._order([(self.p_dunlop_18, 40, 1000.0)])

        self.assertIsNone(self._evaluate(promo, order))

    # ------------------------------------------------------------------
    # Caso 3 — Cantidad Acumulada por Rin
    # ------------------------------------------------------------------
    def test_rim_policy_acumulado_global_y_porcentaje_por_rin(self):
        """El tramo se elige con el acumulado TOTAL; cada rin cobra el suyo.

        Carrito: 60 piezas R16 + 40 piezas R18, todas a $1,000.
        Acumulado = 100 -> cae en el tramo 100..inf para ambos rines.
            R16 -> 6%  sobre 60,000 = 3,600
            R18 -> 8%  sobre 40,000 = 3,200
        Total esperado = 6,800.

        Esta es la mecánica que el refactor vino a arreglar: el universo
        sale del alcance y el acumulado es común, no por rin.
        """
        promo = self._promo(
            promo_conditions=SCOPE_RIM_POLICY,
            promo_type=POLICY_RIM_QUANTITY,
            rim_policy_line_ids=[
                (0, 0, {
                    'lower_limit': 50, 'upper_limit': 99,
                    'rim_ids': [(6, 0, [self.rim16.id, self.rim17.id])],
                    'discount': 4.0,
                }),
                (0, 0, {
                    'lower_limit': 100, 'upper_limit': UNLIMITED,
                    'rim_ids': [(6, 0, [self.rim16.id, self.rim17.id])],
                    'discount': 6.0,
                }),
                (0, 0, {
                    'lower_limit': 100, 'upper_limit': UNLIMITED,
                    'rim_ids': [(6, 0, [self.rim18.id])],
                    'discount': 8.0,
                }),
            ],
        )
        order = self._order([
            (self.p_goodyear_16, 60, 1000.0),
            (self.p_dunlop_18, 40, 1000.0),
        ])

        result = self._evaluate(promo, order)

        self.assertIsNotNone(result)
        self.assertEqual(result['qty'], 100)
        self.assertAlmostEqual(result['ganado'], 6800.0, places=2)
        self.assertIsNone(
            result['discount_percent'],
            'En promos por rin no hay un porcentaje único: debe ser None',
        )

    # ------------------------------------------------------------------
    # Caso 4 — Monto fijo repartido entre líneas
    # ------------------------------------------------------------------
    def test_monto_fijo_se_reparte_sin_perder_centavos(self):
        """El fijo se prorratea por subtotal y la última línea absorbe el resto.

        Carrito: 10 GY a $1,000 (10,000) + 5 PI a $1,000 (5,000).
        El monto fijo se captura CON IVA, así que 1,160 capturados son
        1,000 de NC (el timbrado le vuelve a sumar el IVA y el cliente
        recibe los 1,160 prometidos). Sobre esos 1,000:
            GY: round(1000 * 10000/15000, 2) = 666.67
            PI: 1000 - 666.67                = 333.33
        El total debe dar exactamente 1,000.00, sin centavo perdido.

        El test capturaba 1,000 y esperaba 1,000 de ganado: se escribió
        antes de la regla "todo monto capturado lleva IVA" y desde
        entonces fallaba pidiendo 1,000 donde el motor daba 862.07. Lo
        que se estaba probando —el prorrateo sin perder centavos— sigue
        intacto; solo se captura el número que corresponde.
        """
        promo = self._promo(
            promo_conditions=SCOPE_TIRE_FEATURE,
            promo_type=POLICY_AMOUNT,
            reward_type=REWARD_FIXED_AMOUNT,
            brand_ids=[(6, 0, [self.goodyear.id, self.pirelli.id])],
            policy_line_amount_ids=[
                (0, 0, {
                    'lower_limit': 1, 'upper_limit': UNLIMITED,
                    'fixed_amount': 1160.0,
                }),
            ],
        )
        order = self._order([
            (self.p_goodyear_16, 10, 1000.0),
            (self.p_pirelli_17, 5, 1000.0),
        ])

        result = self._evaluate(promo, order)

        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['ganado'], 1000.0, places=2)


# ----------------------------------------------------------------------
# PENDIENTE, y a propósito sin escribir:
#
#  - Volumen Mensual: `_evaluate_document_reward` devuelve (None, None)
#    para POLICY_MONTHLY_VOLUME, así que `evaluate_document` SIEMPRE
#    regresa None. Esa política solo vive en el cálculo histórico por
#    periodo, no en la evaluación en vivo. Si esperabas verla en el
#    cotizador, eso es un hallazgo, no un test que falte.
#
#  - Cupones: necesito tus datos reales (importe por producto y el
#    comportamiento esperado del tope `coupon_limit_qty` cuando un mismo
#    cliente aparece con RFC fiscal y genérico).
#
#  - Key Sizes, apply_on_groups y apply_volume: son los tres que según
#    el docstring de `ztyres_promo_config.py` inflaban las NC. Escribir
#    el número esperado A OJO aquí sería congelar el bug. Pásame un caso
#    real con el monto que la promoción DEBÍA pagar y los escribo.
# ----------------------------------------------------------------------


@tagged('post_install', '-at_install')
class TestTramosConIva(PromoTestCommon):
    """Los límites de la tabla de montos se capturan CON IVA.

    El acumulado con el que se comparan es el subtotal, y la NC se
    calcula sobre ese mismo subtotal. Con IVA al 16%:

        límite 35,000 con IVA  ->  se alcanza con 30,172.41 de subtotal
    """

    def _promo_35k(self):
        return self._promo(
            promo_conditions=SCOPE_TIRE_FEATURE,
            promo_type=POLICY_AMOUNT,
            brand_ids=[(6, 0, [self.goodyear.id])],
            policy_line_amount_ids=[
                (0, 0, {
                    'lower_limit': 35000, 'upper_limit': UNLIMITED,
                    'discount': 5.0,
                }),
            ],
        )

    def test_subtotal_justo_debajo_del_umbral_no_alcanza(self):
        """30,172.00 de subtotal son 34,999.52 con IVA: no llega."""
        order = self._order([(self.p_goodyear_16, 1, 30172.00)])
        self.assertIsNone(self._evaluate(self._promo_35k(), order))

    def test_subtotal_equivalente_a_35k_con_iva_si_alcanza(self):
        """30,172.42 de subtotal son 35,000.01 con IVA: entra al tramo.

        Y la NC sale del SUBTOTAL, no del monto con IVA:
            30,172.42 x 5% = 1,508.62
        Si alguien calculara sobre los 35,000 saldrían 1,750.00, que es
        exactamente el 16% de más que este test existe para atrapar.
        """
        order = self._order([(self.p_goodyear_16, 1, 30172.42)])
        result = self._evaluate(self._promo_35k(), order)

        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['amount'], 30172.42, places=2)
        self.assertAlmostEqual(result['ganado'], 1508.62, places=2)

    def test_tramos_por_cantidad_no_se_tocan(self):
        """Las piezas no llevan IVA: 50 llantas son 50, no 43.

        Si la conversión se aplicara a toda tabla de tramos y no solo a
        la de montos, este caso caería en el tramo equivocado.
        """
        promo = self._promo(
            promo_conditions=SCOPE_TIRE_FEATURE,
            promo_type=POLICY_QUANTITY,
            brand_ids=[(6, 0, [self.goodyear.id])],
            policy_line_qty_ids=[
                (0, 0, {'lower_limit': 1, 'upper_limit': 49, 'discount': 3.0}),
                (0, 0, {'lower_limit': 50, 'upper_limit': UNLIMITED, 'discount': 5.0}),
            ],
        )
        order = self._order([(self.p_goodyear_16, 50, 1000.0)])
        result = self._evaluate(promo, order)

        self.assertIsNotNone(result)
        self.assertEqual(result['discount_percent'], 5.0)

    def test_tasa_configurable(self):
        """Cambiar la tasa mueve el umbral, sin tocar código.

        Este test tiene DOS aserciones a propósito. Con solo la negativa
        pasaba en verde aunque la conversión no estuviera ocurriendo:
        si el factor se queda en 1.0, el umbral es 35,000 y 30,172.42
        tampoco alcanza — el mismo None por la razón equivocada. La
        aserción positiva es la que obliga a que la tasa del 8% se esté
        aplicando de verdad.
        """
        self.env['ir.config_parameter'].sudo().set_param(
            'ztyres_promo.tier_amount_tax_rate', '8'
        )
        # Con IVA al 8%, 35,000 se alcanzan con 32,407.41 de subtotal.
        promo = self._promo_35k()

        justo_abajo = self._order([(self.p_goodyear_16, 1, 32407.00)])
        self.assertIsNone(self._evaluate(promo, justo_abajo))

        justo_arriba = self._order([(self.p_goodyear_16, 1, 32407.41)])
        result = self._evaluate(promo, justo_arriba)
        self.assertIsNotNone(
            result,
            'Con la tasa al 8% el umbral debe bajar a 32,407.41',
        )
        self.assertAlmostEqual(result['ganado'], 1620.37, places=2)

    def test_sin_parametro_configurado_usa_16(self):
        """El caso por defecto: sin el parámetro en BD, la tasa es 16%.

        `get_param` devuelve False cuando la clave no existe, y
        `float(False)` es 0.0 sin lanzar excepción. Si eso se cuela, el
        factor queda en 1.0 y los límites nunca se convierten.
        """
        self.env['ir.config_parameter'].sudo().set_param(
            'ztyres_promo.tier_amount_tax_rate', False
        )
        engine = self.env['ztyres_promo.reward_engine']
        self.assertAlmostEqual(engine._tier_tax_factor(), 1.16, places=6)

    def test_tasa_cero_escrita_a_mano_se_respeta(self):
        """Un 0 explícito no es lo mismo que 'sin configurar'.

        Sirve para promociones sobre productos exentos: el límite se
        compara tal cual, sin bajarlo.
        """
        self.env['ir.config_parameter'].sudo().set_param(
            'ztyres_promo.tier_amount_tax_rate', '0'
        )
        engine = self.env['ztyres_promo.reward_engine']
        self.assertAlmostEqual(engine._tier_tax_factor(), 1.0, places=6)


@tagged('post_install', '-at_install')
class TestTarjetaDeRegalo(PromoTestCommon):
    """Promo ZT: compra mínima y tarjeta de regalo, sin nota de crédito.

    50,000 con IVA se alcanzan con 43,103.45 de subtotal. Al llegar, el
    cliente se lleva una tarjeta por el valor de la columna Promo ZT —
    que se entrega tal cual se capturó, porque no pasa por ninguna NC.
    """

    def _promo_tarjeta(self):
        """Tarjeta cuyo valor es el fijo del NIVEL, no el de la plantilla.

        `gift_card_source` se escribe explícito: el campo tiene default
        'product' (la Promo ZT vigente), así que un fixture que no lo
        diga prueba el origen equivocado — el motor busca la plantilla
        por código, no encuentra ninguna, y devuelve None. Era la causa
        de que esta clase entera fallara.
        """
        return self._promo(
            promo_conditions=SCOPE_TIRE_FEATURE,
            promo_type=POLICY_AMOUNT,
            reward_type='gift_card',
            gift_card_source=GIFT_CARD_SOURCE_TIER,
            brand_ids=[(6, 0, [self.goodyear.id])],
            policy_line_amount_ids=[
                (0, 0, {
                    'lower_limit': 50000, 'upper_limit': UNLIMITED,
                    'gift_card_amount': 2000.0,
                }),
            ],
        )

    def test_no_llega_al_minimo(self):
        order = self._order([(self.p_goodyear_16, 1, 43103.00)])
        self.assertIsNone(self._evaluate(self._promo_tarjeta(), order))

    def test_llega_y_avisa_sin_generar_nc(self):
        """Alcanza el nivel: avisa, con ganado en CERO.

        El cero no es un descuido: `_create_nc` solo emite nota de
        crédito para las líneas con `total_nc_untaxed > 0`, así que un
        ganado de 0 es justo lo que impide que se genere. La promoción
        sigue apareciendo como alcanzada.
        """
        order = self._order([(self.p_goodyear_16, 1, 43103.45)])
        result = self._evaluate(self._promo_tarjeta(), order)

        self.assertIsNotNone(result, 'Debe avisar aunque no genere NC')
        self.assertEqual(result['ganado'], 0.0)
        self.assertAlmostEqual(result['gift_card_amount'], 2000.0, places=2)

    def test_valor_de_la_tarjeta_no_se_le_baja_el_iva(self):
        """2,000 capturados son 2,000 entregados.

        A diferencia del monto fijo y de los cupones, aquí no hay
        timbrado que vuelva a sumar el IVA, así que bajarlo dejaría al
        cliente con 1,724.14 de tarjeta.
        """
        order = self._order([(self.p_goodyear_16, 1, 50000.00)])
        result = self._evaluate(self._promo_tarjeta(), order)
        self.assertAlmostEqual(result['gift_card_amount'], 2000.0, places=2)

    def test_monto_fijo_si_se_le_baja_el_iva(self):
        """El contraste: 1,160 capturados dan 1,000 de NC.

        La NC se emite sobre 1,000 y el timbrado le suma el IVA, así que
        el cliente recibe los 1,160 prometidos.
        """
        promo = self._promo(
            promo_conditions=SCOPE_TIRE_FEATURE,
            promo_type=POLICY_AMOUNT,
            reward_type=REWARD_FIXED_AMOUNT,
            brand_ids=[(6, 0, [self.goodyear.id])],
            policy_line_amount_ids=[
                (0, 0, {
                    'lower_limit': 1, 'upper_limit': UNLIMITED,
                    'fixed_amount': 1160.0,
                }),
            ],
        )
        order = self._order([(self.p_goodyear_16, 1, 10000.0)])
        result = self._evaluate(promo, order)

        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['ganado'], 1000.0, places=2)


@tagged('post_install', '-at_install')
class TestGiftCardFromProductTemplate(PromoTestCommon):
    """Tarjeta de regalo cuyo valor sale de la plantilla por código.

    Es la mecánica de B/F-0801PZT: el nivel solo dice si el cliente
    califica ("compra mínima de 50 mil netos al mes") y el valor sale de
    la columna Promo ZT de cada código, multiplicado por las piezas.

    Los 50 mil del convenio YA INCLUYEN IVA — "netos" ahí significa neto
    de descuentos y devoluciones, no sin IVA. Por eso se capturan tal
    cual, 50000, en una columna que de por sí se llama "Desde (con
    IVA)". El motor los baja a subtotal para comparar:

        50,000 / 1.16 = 43,103.45 de subtotal

    o sea que el cliente califica al llegar a 43,103.45 de subtotal, que
    es exactamente lo mismo que 50,000 facturados.
    """

    MINIMO_CON_IVA = 50000
    MINIMO_SUBTOTAL = 43103.45

    def _promo_plantilla(self, valores=None, delivery=GIFT_CARD_DELIVERY_NONE):
        """Promo por Monto, con valor por código.

        `valores` = [(producto, monto_por_pieza), ...]
        """
        if valores is None:
            valores = [(self.p_goodyear_16, 5.0)]
        promo = self._promo(
            promo_conditions=SCOPE_TIRE_FEATURE,
            promo_type=POLICY_AMOUNT,
            reward_type=REWARD_GIFT_CARD,
            gift_card_source=GIFT_CARD_SOURCE_PRODUCT,
            gift_card_delivery=delivery,
            brand_ids=[(6, 0, [self.goodyear.id, self.pirelli.id])],
            policy_line_amount_ids=[
                (0, 0, {
                    'lower_limit': self.MINIMO_CON_IVA,
                    'upper_limit': UNLIMITED,
                }),
            ],
        )
        promo.write({
            'gift_card_ids': [
                (0, 0, {
                    'product_id': product.product_tmpl_id.id,
                    'amount': amount,
                })
                for product, amount in valores
            ],
        })
        return promo

    # ------------------------------------------------------------------
    # El caso que pidió el negocio
    # ------------------------------------------------------------------
    def test_columna_de_5_por_10_llantas_da_50(self):
        """El ejemplo textual: si la columna dice 5 y compra 10, son 50.

        Carrito: 10 GY a 5,000 = 50,000 de subtotal (58,000 facturados),
        muy por encima del mínimo. Califica, y la tarjeta son 10 x 5 = 50.
        """
        order = self._order([(self.p_goodyear_16, 10, 5000.0)])

        result = self._evaluate(self._promo_plantilla(), order)

        self.assertIsNotNone(result, 'Con 50,000 netos debe calificar')
        self.assertAlmostEqual(result['gift_card_amount'], 50.0, places=2)

    def test_codigo_17756300_con_valor_84_07(self):
        """Caso real: al llegar a $50,000 con IVA paga $84.07 por pieza."""
        order = self._order([
            (self.p_goodyear_16, 1, self.MINIMO_SUBTOTAL),
        ])
        promo = self._promo_plantilla(valores=[
            (self.p_goodyear_16, 84.07),
        ])

        result = self._evaluate(promo, order)

        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['gift_card_amount'], 84.07, places=2)

    def test_el_valor_escala_con_las_piezas(self):
        """20 llantas del mismo código dan el doble: no es un valor fijo."""
        order = self._order([(self.p_goodyear_16, 20, 5000.0)])
        result = self._evaluate(self._promo_plantilla(), order)
        self.assertAlmostEqual(result['gift_card_amount'], 100.0, places=2)

    def test_no_llega_al_minimo_no_hay_tarjeta(self):
        """40,000 de subtotal son 46,400 facturados: no llega a los 50 mil."""
        order = self._order([(self.p_goodyear_16, 8, 5000.0)])
        self.assertIsNone(self._evaluate(self._promo_plantilla(), order))

    def test_el_minimo_se_mide_sobre_lo_facturado(self):
        """Los 50 mil del convenio son facturados, IVA incluido.

        Un centavo por debajo del umbral no califica, y justo en el
        umbral sí. Sirve de candado contra el error de captura opuesto:
        si alguien "corrigiera" el nivel a 58,000 pensando que 50 mil
        eran sin IVA, este caso empezaría a fallar y avisaría que la
        promoción se volvió más difícil de alcanzar de lo pactado.
        """
        # 49,999.48 facturados: se queda a 52 centavos del mínimo.
        justo_abajo = self._order([(self.p_goodyear_16, 1, 43103.00)])
        self.assertIsNone(self._evaluate(self._promo_plantilla(), justo_abajo))

        # 50,000.00 facturados exactos.
        justo_arriba = self._order([
            (self.p_goodyear_16, 1, self.MINIMO_SUBTOTAL),
        ])
        self.assertIsNotNone(
            self._evaluate(self._promo_plantilla(), justo_arriba)
        )

    # ------------------------------------------------------------------
    # Alcance vs. plantilla
    # ------------------------------------------------------------------
    def test_codigo_sin_valor_suma_al_minimo_pero_no_paga(self):
        """Pirelli participa del acumulado; sin valor en la plantilla, no paga.

        Carrito: 5 GY + 5 PI a 5,000 = 50,000 de subtotal. Las dos marcas
        entran por el alcance y juntas abren el nivel, pero solo Goodyear
        tiene columna Promo ZT: 5 x 5 = 25.
        """
        order = self._order([
            (self.p_goodyear_16, 5, 5000.0),
            (self.p_pirelli_17, 5, 5000.0),
        ])

        result = self._evaluate(self._promo_plantilla(), order)

        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['amount'], 50000.0, places=2)
        self.assertAlmostEqual(result['gift_card_amount'], 25.0, places=2)

    def test_solo_las_piezas_de_la_plantilla_cuentan_para_el_valor(self):
        """Pirelli sola califica por monto, pero no hay nada que pagar.

        10 PI a 5,000 abren el nivel de sobra, pero ningún código del
        carrito tiene columna Promo ZT: la tarjeta sería de cero y la
        promoción se descarta en vez de avisar $0.00.
        """
        order = self._order([(self.p_pirelli_17, 10, 5000.0)])
        self.assertIsNone(self._evaluate(self._promo_plantilla(), order))

    def test_cada_codigo_cobra_su_propio_valor(self):
        """La plantilla es por código, no un valor único para la promo."""
        order = self._order([
            (self.p_goodyear_16, 5, 5000.0),
            (self.p_pirelli_17, 5, 5000.0),
        ])
        promo = self._promo_plantilla(valores=[
            (self.p_goodyear_16, 5.0),
            (self.p_pirelli_17, 12.0),
        ])

        result = self._evaluate(promo, order)

        # 5 x 5 + 5 x 12 = 85
        self.assertAlmostEqual(result['gift_card_amount'], 85.0, places=2)

    def test_desglose_por_producto_trae_el_valor_de_tarjeta(self):
        order = self._order([
            (self.p_goodyear_16, 10, 5000.0),
            (self.p_pirelli_17, 1, 1000.0),
        ])
        promo = self._promo_plantilla(valores=[(self.p_goodyear_16, 5.0)])

        result = self._evaluate(promo, order)

        goodyear_lines = [
            line for line in result['lines'] if line['ganado'] > 0
        ]
        self.assertEqual(len(goodyear_lines), 1)
        self.assertAlmostEqual(goodyear_lines[0]['ganado'], 50.0, places=2)

    # ------------------------------------------------------------------
    # Entrega
    # ------------------------------------------------------------------
    def test_solo_aviso_no_genera_nc(self):
        """`ganado` en cero es lo que impide que se emita la NC."""
        order = self._order([(self.p_goodyear_16, 10, 5000.0)])
        result = self._evaluate(self._promo_plantilla(), order)

        self.assertEqual(result['ganado'], 0.0)
        self.assertFalse(result['line_ganado_map'])

    def test_entrega_como_nc_nunca_emite_nc(self):
        """Hoy la tarjeta NUNCA genera nota de crédito, ni con delivery='nc'.

        OJO: este test documenta una contradicción abierta del módulo, no
        un comportamiento que dé por bueno.

        `_gift_card_generates_nc()` devuelve False sin mirar nada, y la
        vista lo dice ("No genera ni timbra nota de crédito"), pero el
        campo `gift_card_delivery` sigue ofreciendo la opción "Nota de
        crédito por el valor de la tarjeta" y hasta emite un aviso en
        rojo advirtiendo que se va a timbrar. Elegir esa opción no hace
        nada.

        El test se escribió cuando la opción sí funcionaba (esperaba
        43.10 = 50/1.16) y desde entonces fallaba. Se actualiza a lo que
        el motor hace HOY —y no al revés— porque la dirección contraria
        pondría CFDI en el SAT: si algún día se decide honrar el campo,
        que sea una decisión tomada, no un test que la fuerce.

        Hay que resolverlo en una de las dos direcciones: quitar la
        opción del selector, o hacer que `_gift_card_generates_nc()` lea
        el campo.
        """
        order = self._order([(self.p_goodyear_16, 10, 5000.0)])
        promo = self._promo_plantilla(delivery=GIFT_CARD_DELIVERY_NC)

        result = self._evaluate(promo, order)

        self.assertAlmostEqual(result['gift_card_amount'], 50.0, places=2)
        self.assertEqual(
            result['ganado'],
            0.0,
            'La tarjeta no emite NC aunque la entrega diga que sí',
        )

    # ------------------------------------------------------------------
    # Política por cantidad
    # ------------------------------------------------------------------
    def test_tambien_funciona_con_politica_por_cantidad(self):
        """El nivel puede medir piezas en vez de pesos.

        Antes el motor leía siempre la tabla de montos, así que una
        tarjeta con política por Cantidad no se entregaba nunca.
        """
        promo = self._promo(
            promo_conditions=SCOPE_TIRE_FEATURE,
            promo_type=POLICY_QUANTITY,
            reward_type=REWARD_GIFT_CARD,
            gift_card_source=GIFT_CARD_SOURCE_PRODUCT,
            brand_ids=[(6, 0, [self.goodyear.id])],
            policy_line_qty_ids=[
                (0, 0, {'lower_limit': 10, 'upper_limit': UNLIMITED}),
            ],
        )
        promo.write({
            'gift_card_ids': [
                (0, 0, {
                    'product_id': self.p_goodyear_16.product_tmpl_id.id,
                    'amount': 5.0,
                }),
            ],
        })

        insuficiente = self._order([(self.p_goodyear_16, 9, 100.0)])
        self.assertIsNone(self._evaluate(promo, insuficiente))

        suficiente = self._order([(self.p_goodyear_16, 10, 100.0)])
        result = self._evaluate(promo, suficiente)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result['gift_card_amount'], 50.0, places=2)


@tagged('post_install', '-at_install')
class TestVisibleRewardResults(PromoTestCommon):
    """Resultados (NC) oculta ceros; Detalle conserva toda la auditoría."""

    def test_solo_recompensas_positivas_entran_en_resultados(self):
        promo = self._promo()
        Result = self.env['ztyres_promo.notas_credito_lines']
        zero = Result.create({
            'definitive_nc_id': promo.id,
            'reward_type': 'percentage',
            'total_nc_untaxed': 0.0,
        })
        residual = Result.create({
            'definitive_nc_id': promo.id,
            'reward_type': 'percentage',
            'total_nc_untaxed': 0.004,
        })
        positive = Result.create({
            'definitive_nc_id': promo.id,
            'reward_type': 'percentage',
            'total_nc_untaxed': 0.01,
        })
        gift_zero = Result.create({
            'definitive_nc_id': promo.id,
            'reward_type': 'gift_card',
            'gift_card_amount': 0.0,
            'total_nc_untaxed': 100.0,
        })
        gift_positive = Result.create({
            'definitive_nc_id': promo.id,
            'reward_type': 'gift_card',
            'gift_card_amount': 0.01,
        })

        self.assertFalse(zero.has_reward)
        self.assertFalse(residual.has_reward)
        self.assertTrue(positive.has_reward)
        self.assertFalse(gift_zero.has_reward)
        self.assertTrue(gift_positive.has_reward)
        self.assertEqual(
            set(promo.winning_line_ids.ids),
            {positive.id, gift_positive.id},
        )
        self.assertEqual(len(promo.line_ids), 5)

    def test_descarga_facturas_solo_de_resultados_ganadores(self):
        """Una línea válida sin recompensa no autoriza su factura."""
        promo = self._promo()
        Move = self.env['account.move']
        winner_invoice = Move.create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_date': self.DOC_DATE,
        })
        participant_only_invoice = Move.create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'invoice_date': self.DOC_DATE,
        })

        self.env['ztyres_promo.lines'].create([
            {
                'definitive_nc_id': promo.id,
                'partner_id': self.partner.id,
                'rfc': 'RFC-GANADOR',
                'state': 'valid',
                'move_type': 'out_invoice',
                'move_id': winner_invoice.id,
                'product_id': self.p_goodyear_16.product_tmpl_id.id,
                'quantity': 1,
                'price_subtotal': 100.0,
            },
            {
                'definitive_nc_id': promo.id,
                'partner_id': self.partner.id,
                'rfc': 'RFC-SIN-PREMIO',
                'state': 'valid',
                'move_type': 'out_invoice',
                'move_id': participant_only_invoice.id,
                'product_id': self.p_pirelli_17.product_tmpl_id.id,
                'quantity': 1,
                'price_subtotal': 100.0,
            },
        ])
        self.env['ztyres_promo.notas_credito_lines'].create([
            {
                'definitive_nc_id': promo.id,
                'partner_id': self.partner.id,
                'rfc': 'RFC-GANADOR',
                'reward_type': 'percentage',
                'total_nc_untaxed': 10.0,
            },
            {
                'definitive_nc_id': promo.id,
                'partner_id': self.partner.id,
                'rfc': 'RFC-SIN-PREMIO',
                'reward_type': 'percentage',
                'total_nc_untaxed': 0.0,
            },
        ])

        invoices = promo._get_valid_invoices('out_invoice')
        self.assertEqual(invoices, winner_invoice)


@tagged('post_install', '-at_install')
class TestKeySizesYBasePms(PromoTestCommon):
    """Key Sizes (qué porcentaje) y base PMS (sobre qué se aplica).

    Son dos ejes distintos y se combinan. Todos los números de aquí
    están calculados a mano desde la regla de negocio.
    """

    def _promo_key_sizes(self, **extra):
        """4.20% general, 6.00% para el Key Size, un solo tramo.

        La Goodyear es el Key Size; la Pirelli cobra el general.
        """
        values = dict(
            promo_conditions=SCOPE_TIRE_FEATURE,
            promo_type=POLICY_QUANTITY,
            brand_ids=[(6, 0, [self.goodyear.id, self.pirelli.id])],
            key_size_product_ids=[
                (6, 0, [self.p_goodyear_16.product_tmpl_id.id]),
            ],
            policy_line_qty_ids=[
                (0, 0, {
                    'lower_limit': 1,
                    'upper_limit': UNLIMITED,
                    'discount': 4.20,
                    'key_size_discount': 6.00,
                }),
            ],
        )
        values.update(extra)
        return self._promo(**values)

    def _pms(self, *pairs):
        """[(producto, precio), ...] -> comandos para pms_price_ids."""
        return [
            (0, 0, {
                'product_id': product.product_tmpl_id.id,
                'price': price,
            })
            for product, price in pairs
        ]

    # ------------------------------------------------------------------
    # Base de siempre: el subtotal facturado
    # ------------------------------------------------------------------
    def test_key_sizes_cobran_su_columna_sobre_lo_facturado(self):
        """10 GY x 6% + 10 PI x 4.20% sobre $1,000 = 600 + 420."""
        promo = self._promo_key_sizes()
        order = self._order([
            (self.p_goodyear_16, 10, 1000.0),
            (self.p_pirelli_17, 10, 1000.0),
        ])

        result = self._evaluate(promo, order)

        self.assertAlmostEqual(result['ganado'], 1020.0, places=2)
        self.assertIsNone(
            result['discount_percent'],
            'Con Key Sizes no hay un porcentaje único que explique el '
            'importe: mostrarlo invita a multiplicar y no cuadrar',
        )

    # ------------------------------------------------------------------
    # Base PMS
    # ------------------------------------------------------------------
    def test_base_pms_ignora_el_precio_de_venta(self):
        """El importe sale del PMS, no de lo facturado.

        GY: 10 pza x 500 (PMS) x 6.00%  =   300.00
        PI: 10 pza x 2,000 (PMS) x 4.20% = 840.00
                                          --------
                                          1,140.00

        Lo facturado (10 x 1,000 cada uno) habría dado 1,020: si el test
        ve 1,020, el PMS no se está aplicando.
        """
        promo = self._promo_key_sizes(
            key_size_base=BASE_PMS,
            pms_price_taxed=PRICE_UNTAXED,
            pms_price_ids=self._pms(
                (self.p_goodyear_16, 500.0),
                (self.p_pirelli_17, 2000.0),
            ),
        )
        order = self._order([
            (self.p_goodyear_16, 10, 1000.0),
            (self.p_pirelli_17, 10, 1000.0),
        ])

        result = self._evaluate(promo, order)

        self.assertAlmostEqual(result['ganado'], 1140.0, places=2)

    def test_el_descuento_por_pieza_se_redondea_antes_de_multiplicar(self):
        """Caso real de la liquidación Bridgestone/Firestone de julio.

        El convenio fija el descuento POR PIEZA, y así lo liquida la
        marca:

            10871003 (Key Size)  PMS 2,519.83 x 4.80% = 120.95 / pza
                                 x 20 pza             = 2,419.00
            17160003 (general)   PMS 1,902.85 x 4.20% =  79.92 / pza
                                 x 20 pza             = 1,598.40
                                                        ---------
                                                         4,017.40

        Redondeando al final —`round(piezas x PMS x %)`— darían 2,419.04
        y 1,598.39: 3 centavos de más en dos renglones, $1.21 en la
        liquidación completa de 22. La liquidación no cuadraría contra
        la del proveedor, que es la que manda.
        """
        promo = self._promo_key_sizes(
            key_size_base=BASE_PMS,
            pms_price_taxed=PRICE_UNTAXED,
            pms_price_ids=self._pms(
                (self.p_goodyear_16, 2519.83),
                (self.p_pirelli_17, 1902.85),
            ),
            policy_line_qty_ids=[
                (0, 0, {
                    'lower_limit': 1,
                    'upper_limit': UNLIMITED,
                    'discount': 4.20,
                    'key_size_discount': 4.80,
                }),
            ],
        )
        order = self._order([
            (self.p_goodyear_16, 20, 2431.85),
            (self.p_pirelli_17, 20, 1860.79),
        ])

        result = self._evaluate(promo, order)

        self.assertAlmostEqual(result['ganado'], 4017.40, places=2)
        self.assertNotAlmostEqual(
            result['ganado'],
            4017.43,
            places=2,
            msg='4,017.43 significa que se redondeó al final, no por pieza',
        )

    def test_dos_clientes_con_distinto_precio_reciben_lo_mismo(self):
        """Es la razón de ser de la promoción.

        El mismo código, vendido a 1,000 y a 1,500: con base PMS la NC
        por pieza es idéntica.
        """
        promo = self._promo_key_sizes(
            key_size_base=BASE_PMS,
            pms_price_ids=self._pms((self.p_goodyear_16, 500.0)),
        )
        barato = self._order([(self.p_goodyear_16, 10, 1000.0)])
        caro = self._order([(self.p_goodyear_16, 10, 1500.0)])

        self.assertAlmostEqual(
            self._evaluate(promo, barato)['ganado'],
            self._evaluate(promo, caro)['ganado'],
            places=2,
        )

    def test_precio_pms_capturado_con_iva_se_convierte_al_final(self):
        """El % se aplica al precio del convenio; el IVA se baja después.

        1,160 con IVA al 6% son $69.60 de descuento por pieza —la cifra
        que trae el convenio— y 10 piezas dan $696.00 con IVA, o sea
        $600.00 de subtotal, que es lo que se factura en la NC.

        El orden importa: bajarle el IVA al precio ANTES de sacar el
        porcentaje redondea un número intermedio que el convenio nunca
        menciona, y la liquidación se desvía por centavos del papel del
        proveedor.

        Capturado como "sin IVA", el mismo archivo daría 696: ese 16% de
        diferencia es exactamente lo que se juega en el selector.
        """
        con_iva = self._promo_key_sizes(
            key_size_base=BASE_PMS,
            pms_price_taxed=PRICE_TAXED,
            pms_price_ids=self._pms((self.p_goodyear_16, 1160.0)),
        )
        sin_iva = self._promo_key_sizes(
            key_size_base=BASE_PMS,
            pms_price_taxed=PRICE_UNTAXED,
            pms_price_ids=self._pms((self.p_goodyear_16, 1160.0)),
        )
        order = self._order([(self.p_goodyear_16, 10, 1000.0)])

        self.assertAlmostEqual(
            self._evaluate(con_iva, order)['ganado'], 600.0, places=2,
        )
        self.assertAlmostEqual(
            self._evaluate(sin_iva, order)['ganado'], 696.0, places=2,
        )

    def test_participante_sin_precio_pms_cobra_sobre_lo_facturado(self):
        """El fallback es deliberado: base cero lo dejaría sin NC callado.

        GY tiene PMS: 10 x 500 x 6.00%           = 300.00
        PI no tiene:  10 x 1,000 facturado x 4.20% = 420.00
        """
        promo = self._promo_key_sizes(
            key_size_base=BASE_PMS,
            pms_price_ids=self._pms((self.p_goodyear_16, 500.0)),
        )
        order = self._order([
            (self.p_goodyear_16, 10, 1000.0),
            (self.p_pirelli_17, 10, 1000.0),
        ])

        result = self._evaluate(promo, order)

        self.assertAlmostEqual(result['ganado'], 720.0, places=2)

    def test_el_nivel_se_sigue_eligiendo_con_lo_facturado(self):
        """El PMS cambia la base, nunca el tramo.

        Tramo por monto que abre en 50,000 CON IVA (43,103.45 de
        subtotal). El cliente factura 50,000 de subtotal, así que
        califica; el PMS de sus llantas es ridículo a propósito. Si el
        acumulado se midiera con PMS (10 x 500 = 5,000) no alcanzaría
        ningún nivel y el resultado sería None.
        """
        promo = self._promo(
            promo_conditions=SCOPE_TIRE_FEATURE,
            promo_type=POLICY_AMOUNT,
            brand_ids=[(6, 0, [self.goodyear.id])],
            key_size_base=BASE_PMS,
            pms_price_ids=self._pms((self.p_goodyear_16, 500.0)),
            policy_line_amount_ids=[
                (0, 0, {
                    'lower_limit': 50000,
                    'upper_limit': UNLIMITED,
                    'discount': 4.00,
                }),
            ],
        )
        order = self._order([(self.p_goodyear_16, 10, 5000.0)])

        result = self._evaluate(promo, order)

        self.assertIsNotNone(
            result,
            'El nivel se alcanza con los 50,000 facturados',
        )
        # 10 pza x 500 x 4% = 200, no 50,000 x 4% = 2,000.
        self.assertAlmostEqual(result['ganado'], 200.0, places=2)

    def test_base_pms_sin_tabla_cargada_no_se_activa(self):
        """Sin precios no hay base PMS: se paga sobre lo facturado.

        En el cálculo masivo este caso se detiene con un UserError,
        porque es el único descuido que de otro modo pasa
        desapercibido. Aquí, en el cotizador, solo se comprueba que no
        invente una base de cero y deje al cliente sin nada.
        """
        promo = self._promo_key_sizes(key_size_base=BASE_PMS)
        order = self._order([(self.p_goodyear_16, 10, 1000.0)])

        result = self._evaluate(promo, order)

        self.assertAlmostEqual(result['ganado'], 600.0, places=2)


@tagged('post_install', '-at_install')
class TestDecimales(PromoTestCommon):
    """Redondeo a centavos y cantidades que no se truncan."""

    @property
    def _engine(self):
        return self.env['ztyres_promo.reward_engine']

    def test_piezas_se_redondean_no_se_truncan(self):
        """`int(274.99999)` daba 274 en el detalle de un cliente con 275.

        Las cantidades vienen de sumas de floats y las notas de crédito
        restan, así que el .99999 es lo normal, no la excepción.
        """
        self.assertEqual(self._engine.format_quantity(274.99999), '275')
        self.assertEqual(self._engine.format_quantity(275.00001), '275')
        self.assertEqual(self._engine.format_quantity(1275.0), '1,275')

    def test_media_pieza_no_se_esconde(self):
        """Redondear no es truncar, pero tampoco es mentir."""
        self.assertEqual(self._engine.format_quantity(2.5), '2.50')

    def test_importe_por_porcentaje_sale_en_centavos(self):
        """El resultado es un valor de centavos, no una cola binaria.

        Se compara con `assertAlmostEqual` y no con `assertEqual` porque
        `16186.80` no es representable en binario: lo que devuelve el
        motor es el float más cercano a ese número de centavos, y eso es
        exactamente lo que se le pide.
        """
        self.assertAlmostEqual(
            self._engine.percent_amount(385400.0, 4.20),
            16186.80,
            places=6,
        )
        # 33.33 x 3.33% = 1.109889 -> un centavo redondo.
        self.assertAlmostEqual(
            self._engine.percent_amount(33.33, 3.33),
            1.11,
            places=6,
        )

    def test_porcentaje_de_basura_flotante_es_cero(self):
        """`discount > 0` decía que sí a un 0.0000000001 heredado."""
        self.assertTrue(self._engine.is_zero_percent(0.0000000001))
        self.assertFalse(self._engine.is_zero_percent(0.01))

    def test_el_total_es_la_suma_exacta_de_los_renglones(self):
        """Lo que se le enseña al cliente suma lo que se le paga.

        Antes el total venía de sumar importes SIN redondear mientras el
        detalle mostraba renglones YA redondeados: no cuadraban por
        centavos, y no había forma de explicarlo.

        El caso está elegido para que las dos formas de calcular den
        números distintos, que es la única manera de que el test sirva:

            tres renglones de $1.00 al 0.50%
            cada renglón:  0.005 -> 0.01     ->  total  0.03
            sin redondear: 0.015 -> 0.02     ->  total  0.02

        Un 0.02 aquí significa que el total volvió a salir de la suma
        cruda y el detalle no cuadra.
        """
        promo = self._promo(
            promo_conditions=SCOPE_TIRE_FEATURE,
            promo_type=POLICY_QUANTITY,
            brand_ids=[
                (6, 0, [self.goodyear.id, self.pirelli.id, self.dunlop.id]),
            ],
            key_size_product_ids=[
                (6, 0, [self.p_goodyear_16.product_tmpl_id.id]),
            ],
            policy_line_qty_ids=[
                (0, 0, {
                    'lower_limit': 1,
                    'upper_limit': UNLIMITED,
                    'discount': 0.50,
                    'key_size_discount': 0.50,
                }),
            ],
        )
        order = self._order([
            (self.p_goodyear_16, 1, 1.0),
            (self.p_pirelli_17, 1, 1.0),
            (self.p_dunlop_18, 1, 1.0),
        ])

        result = self._evaluate(promo, order)

        self.assertAlmostEqual(result['ganado'], 0.03, places=2)
        self.assertAlmostEqual(
            result['ganado'],
            sum(result['line_ganado_map'].values()),
            places=2,
        )
        for amount in result['line_ganado_map'].values():
            self.assertAlmostEqual(
                amount,
                round(amount, 2),
                places=6,
                msg='Cada renglón debe venir ya redondeado a centavos',
            )

    def test_cantidad_del_resultado_se_redondea_antes_del_integer(self):
        """`quantity` es Integer y la suma de líneas es float.

        Escribir 274.99999 guardaba 274. El tramo, mientras tanto, se
        había elegido correctamente con 275.
        """
        promo = self._promo()
        lines = self.env['ztyres_promo.lines'].create([
            {
                'definitive_nc_id': promo.id,
                'partner_id': self.partner.id,
                'state': 'valid',
                'product_id': self.p_goodyear_16.product_tmpl_id.id,
                'quantity': 274.99999,
                'price_subtotal': 100.0,
            },
        ])
        self.assertEqual(promo._result_quantity(lines), 275)

    def test_el_detalle_del_beneficio_cuadra(self):
        """El texto auditable trae base e importe por grupo, y suman.

        Es la respuesta al "no me da": el `% efectivo` no reconstruye el
        total —ningún porcentaje único puede, porque el total es la suma
        de renglones redondeados— así que el detalle tiene que traer las
        piezas, el porcentaje, LA BASE y el importe de cada grupo. Cada
        renglón se comprueba con una calculadora y los renglones suman.
        """
        engine = self._engine
        breakdown = [
            ('Base', 4.20, 275.0, 595550.0, 25013.10),
            ('Key Sizes', 6.00, 60.0, 88900.0, 5334.00),
        ]

        texto = engine.format_key_size_breakdown(
            breakdown,
            684450.0,
            is_amount_policy=True,
        )

        self.assertIn('Base: 275 pza x 4.20% sobre $595,550.00', texto)
        self.assertIn('Key Sizes: 60 pza x 6.00% sobre $88,900.00', texto)
        self.assertIn('Total $30,347.10', texto)
        # Lo que importa: los importes del texto suman el total del texto.
        self.assertAlmostEqual(
            sum(item[4] for item in breakdown),
            30347.10,
            places=2,
        )

    def test_el_importe_no_se_reconstruye_desde_el_porcentaje(self):
        """Regresión del caso real: se perdían $53.76 por cliente.

        Subtotal $1,337,501.34 con un efectivo real de 4.6540192625%:
        la NC correcta es $62,247.57. `_recompute_nc_amounts()` la
        rehacía multiplicando por el `reward_percent` GUARDADO —4.65 al
        leerlo del campo— y la dejaba en $62,193.81.

        Con cuatro decimales habría dado $62,247.31: tampoco es el
        importe correcto. El importe correcto no es una multiplicación,
        es la suma de los renglones; por eso ahora cada rama escribe su
        propio total y este método ya no reconstruye nada.
        """
        promo = self._promo()
        result_line = self.env['ztyres_promo.notas_credito_lines'].create({
            'definitive_nc_id': promo.id,
            'partner_id': self.partner.id,
            'reward_type': 'percentage',
            'price_subtotal': 1337501.34,
            'reward_percent': 4.6540,
            'total_nc_untaxed': 62247.57,
        })

        promo._recompute_nc_amounts()

        self.assertAlmostEqual(
            result_line.total_nc_untaxed,
            62247.57,
            places=2,
            msg='El importe calculado renglón por renglón no se toca',
        )

    def test_el_porcentaje_efectivo_reproduce_el_total_en_excel(self):
        """Tecleado en Excel, el % mostrado devuelve el Total NC.

        Es el caso real reportado: subtotal $1,337,501.34 y NC
        $62,247.57. El porcentaje se guarda con 8 decimales
        (4.65401926), y multiplicarlo por el subtotal da los $62,247.57
        al centavo. Con 2 decimales daba 62,193.81 y con 4, 62,247.31:
        de ahí venía el "no me sale igual que en Excel".
        """
        subtotal = 1337501.34
        total_nc = 62247.57

        result_line = self.env['ztyres_promo.notas_credito_lines'].create({
            'definitive_nc_id': self._promo().id,
            'partner_id': self.partner.id,
            'reward_type': 'percentage',
            'price_subtotal': subtotal,
            'reward_percent': total_nc * 100 / subtotal,
            'total_nc_untaxed': total_nc,
        })

        # Lo que haría cualquiera con la calculadora, leyendo la columna.
        en_excel = round(subtotal * result_line.reward_percent / 100, 2)

        self.assertAlmostEqual(en_excel, total_nc, places=2)

    def test_base_facturada_redondea_por_grupo_no_por_renglon(self):
        """Caso real de la promoción de solo Key Sizes (sin PMS).

        El convenio lo dice con todas sus letras: "Primero hace la NC
        con base de TOTAL 13-16 con el porcentaje de la columna
        Porcentaje; luego hace la NC con base a TOTAL KEY SIZE con el
        porcentaje de la columna Key Size; después suma las dos".

        O sea: la base de cada porcentaje es el subtotal DEL GRUPO, y el
        redondeo ocurre una sola vez sobre la suma. Redondeando renglón
        por renglón el resultado se desvía centavos.

            Base 4.20% sobre 30,000.00 (3 renglones) = 1,260.00
            Key  4.80% sobre 20,000.00 (2 renglones) =   960.00
                                                       --------
                                                       2,220.00
        """
        promo = self._promo_key_sizes(
            policy_line_qty_ids=[
                (0, 0, {
                    'lower_limit': 1,
                    'upper_limit': UNLIMITED,
                    'discount': 4.20,
                    'key_size_discount': 4.80,
                }),
            ],
        )
        order = self._order([
            (self.p_goodyear_16, 10, 2000.0),
            (self.p_pirelli_17, 10, 1000.0),
            (self.p_dunlop_18, 10, 2000.0),
        ])

        result = self._evaluate(promo, order)

        # GY es el Key Size: 20,000 x 4.80% = 960.00
        # PI + DU son la base: 30,000 x 4.20% = 1,260.00
        self.assertAlmostEqual(result['ganado'], 2220.0, places=2)
        self.assertAlmostEqual(
            result['ganado'],
            sum(result['line_ganado_map'].values()),
            places=2,
            msg='El reparto por renglón debe sumar el importe del grupo',
        )
