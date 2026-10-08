# -*- coding: utf-8 -*-
"""
Motor de beneficios.

Un solo lugar decide "dado un acumulado, ¿qué tramo aplica y cuánto se
otorga?". Antes esa decisión estaba duplicada y con criterios distintos
en tres archivos:

- `_get_policy_reward`  -> ignoraba por completo el límite superior;
- el descuento por rin  -> sí lo respetaba;
- `_get_monthly_volume_discount` -> lo respetaba con otra convención.

Resultado: la misma tabla de tramos daba números distintos según la
política elegida. Aquí queda una sola regla:

    un tramo aplica si  lower_limit <= valor <= upper_limit
    y (si se configuró) la cantidad de piezas alcanza `min_qty`.

Si varios tramos aplican, gana el de mayor `lower_limit` (el más alto
alcanzado). Es un AbstractModel para que sea llamable desde cualquier
modelo con `self.env['ztyres_promo.reward_engine']`, pero no guarda
estado ni toca la base de datos.

Nota sobre el campo de cantidad: este motor recibe líneas de modelos
distintos. Los documentos vivos usan `sale.order.line` /
`account.move.line` (`product_uom_qty`, `quantity`), y el detalle de la
promoción usa su propio modelo (`quantity`). Por eso los métodos que
suman piezas reciben `quantity_field` y quien llama decide el nombre; el
motor nunca lo adivina.
"""
from collections import defaultdict
from datetime import date as date_type

from odoo import models
from odoo.tools.float_utils import float_is_zero, float_round

from .ztyres_promo_config import (
    REWARD_FIXED_AMOUNT,
    REWARD_GIFT_CARD,
    UNLIMITED,
    normalize_upper_limit,
)


class ZtyresPromoRewardEngine(models.AbstractModel):
    _name = 'ztyres_promo.reward_engine'
    _description = 'Motor de cálculo de beneficios de promociones'

    # ------------------------------------------------------------------
    # Tramos genéricos (Cantidad / Monto)
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Tramos por monto: límites CON IVA, acumulado SIN IVA
    # ------------------------------------------------------------------
    # Los límites de la tabla de montos se capturan como los ve el
    # negocio: con IVA. "Llegar a 35,000" significa 35,000 facturados.
    # Pero la NC se calcula SIEMPRE sobre el subtotal, porque es lo que
    # se acredita.
    #
    # Para que ambas cosas convivan hay que llevarlas al mismo terreno, y
    # se hace convirtiendo el LÍMITE, no el acumulado:
    #
    #     35,000 / 1.16 = 30,172.41
    #
    # o sea, un cliente entra al tramo al llegar a 30,172.41 de subtotal,
    # y sobre ese subtotal se genera la NC.
    #
    # Se convierte el límite y no el acumulado a propósito: el acumulado
    # viaja por todo el motor (base de la NC, desglose por línea, reparto
    # de monto fijo, tabla de Key Sizes). Tocarlo obligaría a acordarse de
    # volverlo a bajar en cada uno de esos puntos, y el primero que se
    # olvide infla la NC un 16%. El límite, en cambio, solo se usa aquí.
    #
    # OJO: esto asume UNA tasa para toda la promoción. Si en la misma
    # promoción entran productos con IVA frontera (8%) o exentos, el
    # tramo se elige con una tasa que no es la de esas líneas. Ver la
    # nota al final del archivo.
    AMOUNT_TIER_MODEL = 'ztyres_promo.current_policy_amount'
    TIER_TAX_RATE_PARAM = 'ztyres_promo.tier_amount_tax_rate'
    DEFAULT_TIER_TAX_RATE = 16.0

    # ------------------------------------------------------------------
    # Redondeo: una sola regla para todo el módulo
    # ------------------------------------------------------------------
    # Un importe de NC se paga en centavos. Antes cada método devolvía
    # el float crudo de la multiplicación y el redondeo ocurría, sin que
    # nadie lo decidiera, al escribir en un campo `digits=(16, 2)`. Eso
    # tenía dos consecuencias feas:
    #
    # 1. El total de un cliente era la suma de importes SIN redondear,
    #    mientras que el detalle que se le enseña muestra cada renglón
    #    redondeado. La suma de la columna no daba el total, por uno o
    #    dos centavos, justo en las promociones con Key Sizes y por rin
    #    (las únicas que suman renglón por renglón).
    # 2. Un `0.1 + 0.2` mal redondeado se arrastraba a comparaciones
    #    (`> 0`) que decidían si una línea cobraba o no.
    #
    # Ahora TODO importe sale de aquí redondeado a la moneda, y el total
    # es la suma exacta de los renglones ya redondeados.
    def _money_rounding(self):
        currency = self.env.company.currency_id
        return currency.rounding or 0.01

    def _money_digits(self):
        currency = self.env.company.currency_id
        return currency.decimal_places if currency else 2

    def round_money(self, amount):
        """Redondea un importe a la precisión de la moneda.

        Dos pasos, y el segundo no es adorno. `float_round` decide bien
        el centavo (redondea medio hacia arriba, que es lo que se espera
        de dinero) pero devuelve el resultado como
        `numero_de_centavos * 0.01`, y esa multiplicación reintroduce
        ruido binario:

            float_round(84.07, 0.01)  ->  84.07000000000001

        El valor es correcto al centavo, pero deja de ser IGUAL al float
        que cualquiera escribe como 84.07, y eso rompe toda comparación
        exacta aguas abajo — incluidos los consumidores de este módulo,
        como el cotizador de ztyres_promotions, que serializa el importe
        y lo compara contra el número capturado.

        `round()` sobre un valor que ya está al centavo no puede cambiar
        el centavo: solo elige el float más cercano a ese número
        decimal, que es el mismo que produce escribirlo a mano.
        """
        return round(
            float_round(
                amount or 0.0,
                precision_rounding=self._money_rounding(),
            ),
            self._money_digits(),
        )

    def percent_amount(self, base, percent):
        """`base x percent%`, ya redondeado a centavos.

        Único lugar donde se multiplica una base por un porcentaje. Si
        mañana la regla de redondeo cambia (por moneda, por país), se
        cambia aquí y no en seis archivos.
        """
        return self.round_money((base or 0.0) * (percent or 0.0) / 100.0)

    def is_zero_percent(self, percent):
        """¿Un porcentaje es cero? Comparado como número, no como float.

        `discount > 0` con un 0.0000000001 heredado de una importación
        dice que sí hay descuento y hace cobrar un porcentaje que en
        pantalla se ve como cero.
        """
        return float_is_zero(percent or 0.0, precision_digits=4)

    def format_money(self, amount):
        """Importe para los textos auditables: '$1,234.56'."""
        return '$%s' % format(self.round_money(amount), ',.2f')

    def format_quantity(self, quantity):
        """Piezas para los textos auditables: redondea, no trunca.

        `int(274.99999)` da 274, y ese 274 se imprimía en la columna
        "Detalle del beneficio" de un cliente que compró 275 piezas. Las
        cantidades llegan de sumas de floats (y de notas de crédito, que
        restan), así que el .99999 es lo normal, no la excepción.
        """
        value = float_round(quantity or 0.0, precision_digits=2)
        if float_is_zero(value - round(value), precision_digits=2):
            return '{:,.0f}'.format(round(value))
        return '{:,.2f}'.format(value)

    def _tier_tax_factor(self):
        """Factor para bajar un límite con IVA a subtotal (1.16 por defecto).

        La tasa se lee de ir.config_parameter
        (`ztyres_promo.tier_amount_tax_rate`, en porcentaje) para que
        cambiarla no requiera tocar código.

        OJO con el valor no configurado: `get_param` devuelve False, y
        `float(False)` NO lanza excepción — devuelve 0.0. Un try/except
        solo, entonces, deja pasar una tasa del 0% y los límites nunca se
        convierten: la promoción exige 35,000 de subtotal en vez de
        30,172.41. Por eso el caso "sin configurar" se detecta ANTES de
        intentar convertir.

        Una tasa de 0 escrita a mano sí se respeta: hay quien la quiera
        para promociones sobre productos exentos.
        """
        raw = self.env['ir.config_parameter'].sudo().get_param(
            self.TIER_TAX_RATE_PARAM
        )
        if raw is False or raw is None or str(raw).strip() == '':
            rate = self.DEFAULT_TIER_TAX_RATE
        else:
            try:
                rate = float(raw)
            except (TypeError, ValueError):
                rate = self.DEFAULT_TIER_TAX_RATE
        if rate < 0:
            rate = self.DEFAULT_TIER_TAX_RATE
        return 1.0 + (rate / 100.0)

    def _tier_bounds(self, policy):
        """Límites del tramo en la misma unidad que el acumulado.

        En tramos por cantidad se devuelven tal cual: las piezas no
        llevan IVA. En tramos por monto se bajan a subtotal.
        """
        lower = policy.lower_limit
        upper = normalize_upper_limit(policy.upper_limit)

        if getattr(policy, '_name', '') != self.AMOUNT_TIER_MODEL:
            return lower, upper

        factor = self._tier_tax_factor()
        lower = lower / factor
        # UNLIMITED es un centinela, no un monto: dividirlo solo lo
        # ensucia sin cambiar nada.
        if upper < UNLIMITED:
            upper = upper / factor
        return lower, upper

    def tier_matches(self, policy, value, quantity=None):
        """¿El acumulado cae dentro de este tramo?

        `value` viene SIN IVA en las políticas por monto (es la suma de
        price_subtotal). Los límites se bajan a esa misma base en
        `_tier_bounds`.
        """
        lower_limit, upper_limit = self._tier_bounds(policy)
        if value < lower_limit or value > upper_limit:
            return False
        minimum_quantity = getattr(policy, 'min_qty', 0) or 0
        if minimum_quantity and quantity is not None:
            return quantity >= minimum_quantity
        return True

    def matching_tier(self, policies, value, quantity=None):
        """Tramo alcanzado, o vacío si el acumulado no cae en ninguno."""
        eligible = policies.filtered(
            lambda policy: self.tier_matches(policy, value, quantity)
        )
        if not eligible:
            return policies.browse()
        return max(
            eligible,
            key=lambda policy: (policy.lower_limit, policy.id),
        )

    def untaxed(self, amount):
        """Baja el IVA a un monto capturado en la configuración.

        Regla del módulo: TODO monto que se captura en una promoción se
        escribe con IVA, porque así lo ve el negocio (una tarjeta "de
        $2,000" son $2,000 en la mano; un cupón "de $150" son $150).

        Pero la nota de crédito se emite sobre el subtotal y Odoo le
        vuelve a sumar el IVA al timbrarla. Si el monto capturado se
        pasara tal cual, el cliente recibiría 1.16 veces lo prometido.
        De ahí este helper: se aplica en el último momento, justo donde
        un monto configurado se convierte en importe de NC.

        No se aplica a la tarjeta de regalo: ese valor no pasa por
        ninguna NC, se entrega tal cual se capturó.

        El resultado sale redondeado a centavos: es un importe de dinero,
        no un valor intermedio. Bajarle el IVA a $150.00 da
        $129.310344827..., y arrastrar esa cola por el cálculo hace que
        el total del cliente no cuadre con la suma de sus renglones.
        """
        return self.round_money((amount or 0.0) / self._tier_tax_factor())

    def gift_card_qualifies(self, policies, value, quantity=None):
        """¿El acumulado alcanza algún nivel?

        Es la pregunta que hace la tarjeta de regalo cuyo valor sale de
        la plantilla por código: ahí el nivel no aporta un monto, solo
        dice si el cliente califica ("compra mínima de 50 mil netos al
        mes"). Sin niveles configurados no califica nadie — un tramo
        vacío no es un tramo que siempre se cumple.
        """
        return bool(self.matching_tier(policies, value, quantity))

    def gift_card_value(self, policies, value, quantity=None):
        """Valor fijo de la tarjeta del nivel alcanzado, o 0 si no alcanza.

        Se devuelve tal cual está capturado (con IVA): es lo que se le
        entrega al cliente. Si la promoción entrega el valor como nota
        de crédito, quien llama le baja el IVA con `untaxed`, porque el
        timbrado vuelve a sumarlo.
        """
        policy = self.matching_tier(policies, value, quantity)
        if not policy:
            return 0.0
        return getattr(policy, 'gift_card_amount', 0.0) or 0.0

    def gift_card_product_amounts(
        self,
        gift_cards,
        lines,
        quantity_field='quantity',
    ):
        """Valor de tarjeta por piezas, según la plantilla por código.

        Regla: ``piezas × monto del código``. Un código que no está en
        la plantilla vale 0 — participa del acumulado que abre el nivel
        (eso lo decide el alcance, no esta tabla), pero no aporta
        tarjeta.

        Los montos van CON IVA, tal como se capturaron: es lo que se le
        entrega al cliente. Convertirlos es responsabilidad de quien
        emita una NC con ellos.

        :return: ``(total, {line_id: monto})``
        """
        amount_by_product = {
            self._template_of(card.product_id).id: card.amount or 0.0
            for card in gift_cards
        }
        amount_by_line = {}
        total = 0.0

        for line in lines:
            unit_amount = amount_by_product.get(
                self._template_of(line.product_id).id,
                0.0,
            )
            amount = self.round_money(
                unit_amount * self._quantity_of(line, quantity_field)
            )
            amount_by_line[line.id] = amount
            total += amount

        return self.round_money(total), amount_by_line

    def tier_reward(self, policies, value, reward_type, quantity=None):
        """Devuelve ``(porcentaje, monto_fijo)`` del tramo alcanzado.

        El monto fijo sale ya SIN IVA: se captura con IVA y aquí se baja,
        porque de aquí se va directo a la NC.

        La tarjeta de regalo devuelve (0, 0) a propósito — no hay NC que
        calcular. Su valor se consulta aparte con `gift_card_value`.
        """
        policy = self.matching_tier(policies, value, quantity)
        if not policy:
            return 0.0, 0.0
        if reward_type == REWARD_GIFT_CARD:
            return 0.0, 0.0
        if reward_type == REWARD_FIXED_AMOUNT:
            return 0.0, self.untaxed(policy.fixed_amount)
        return policy.discount or 0.0, 0.0

    # ------------------------------------------------------------------
    # Cantidad acumulada por rin
    # ------------------------------------------------------------------
    def rim_discount(self, rim_policies, rim, accumulated_quantity):
        """Porcentaje del rin para el tramo global alcanzado.

        El acumulado es común a toda la promoción (o al grupo): primero
        se suman todas las llantas participantes y con ese total se elige
        el tramo; después cada rin cobra su propio porcentaje.
        """
        if not rim:
            return 0.0
        eligible = rim_policies.filtered(
            lambda policy: (
                rim in policy.rim_ids
                and self.tier_matches(policy, accumulated_quantity)
            )
        )
        if not eligible:
            return 0.0
        policy = max(
            eligible,
            key=lambda item: (item.lower_limit, item.discount, item.id),
        )
        return policy.discount

    def rim_amounts(
        self,
        rim_policies,
        lines,
        accumulated_quantity,
        quantity_field='quantity',
    ):
        """NC por línea y desglose por rin.

        `quantity_field` es el campo de cantidad del modelo de `lines`:
        'product_uom_qty' para sale.order.line, 'quantity' para el
        detalle y para account.move.line.

        :return: ``(total, {line_id: monto}, [(rin, %, cantidad, monto)])``
        """
        amount_by_line = {}
        by_rim = defaultdict(lambda: {
            'discount': 0.0,
            'qty': 0.0,
            'base': 0.0,
            'amount': 0.0,
        })
        total = 0.0

        for line in lines:
            rim = line.product_id.tire_measure_id.rim_id
            discount = self.rim_discount(
                rim_policies,
                rim,
                accumulated_quantity,
            )
            amount = self.percent_amount(line.price_subtotal, discount)
            amount_by_line[line.id] = amount
            total += amount

            bucket = by_rim[rim.display_name if rim else 'Sin rin']
            bucket['discount'] = discount
            bucket['qty'] += self._quantity_of(line, quantity_field)
            bucket['base'] += line.price_subtotal
            bucket['amount'] += amount

        breakdown = [
            (
                name,
                values['discount'],
                values['qty'],
                values['base'],
                values['amount'],
            )
            for name, values in sorted(by_rim.items())
        ]
        return self.round_money(total), amount_by_line, breakdown

    def format_rim_breakdown(self, breakdown, accumulated_quantity):
        """Texto auditable que CUADRA: cada rin con su base y su importe.

        Antes decía solo piezas y porcentaje ("R16: 120 pza x 5.00%"),
        y con eso el importe no se puede verificar: falta la base sobre
        la que se aplicó cada porcentaje. Quien quisiera comprobar la NC
        tenía que multiplicar el subtotal total por el % efectivo, que
        es justo la cuenta que NO da (ver `format_key_size_breakdown`).
        """
        parts = [
            '%s: %s pza x %.2f%% sobre %s = %s' % (
                name,
                self.format_quantity(quantity),
                discount,
                self.format_money(base),
                self.format_money(amount),
            )
            for name, discount, quantity, base, amount in breakdown
            if quantity
        ]
        if not parts:
            return ''
        total = sum(item[4] for item in breakdown)
        return 'Acumulado %s pza | %s | Total %s' % (
            self.format_quantity(accumulated_quantity),
            ' + '.join(parts),
            self.format_money(total),
        )

    # ------------------------------------------------------------------
    # Monto por rin + Key Sizes
    # ------------------------------------------------------------------
    def _rim_number(self, rim):
        """Extrae el número del rin de nombres como R16, 16 o R17+."""
        if not rim:
            return 0
        import re
        match = re.search(r"(\d{2})", rim.display_name or '')
        return int(match.group(1)) if match else 0

    def amount_rim_amounts(
        self,
        key_products,
        tier,
        lines,
        quantity_field='quantity',
        unit_base_by_line=None,
        unit_base_tax_factor=1.0,
    ):
        """Tramo por monto real; porcentaje por RIN/Key Size sobre PMS.

        El tramo se selecciona fuera de este método usando el subtotal
        realmente facturado de los códigos participantes. Una vez elegido,
        cada línea cobra su porcentaje según Key Size o rango de RIN.

        Si ``unit_base_by_line`` contiene la línea, la NC se calcula como el
        resto del motor PMS: primero se redondea el descuento POR PIEZA sobre
        el PMS capturado, luego se multiplica por piezas y finalmente se baja
        IVA cuando corresponda. Esto evita diferencias de centavos contra la
        liquidación de la marca.
        """
        if not tier:
            return 0.0, {}, []
        key_ids = set(key_products.ids)
        ranges = tier.rim_discount_ids.sorted(
            lambda r: (r.rim_from, r.rim_to, r.id)
        )
        unit_base_by_line = unit_base_by_line or {}
        tax_factor = unit_base_tax_factor or 1.0
        amount_by_line = {}
        buckets = defaultdict(
            lambda: {
                'discount': 0.0, 'qty': 0.0, 'base': 0.0,
                'amount': 0.0, 'origen': set(),
            }
        )
        total = 0.0

        for line in lines:
            tmpl = self._template_of(line.product_id)
            is_key = tmpl.id in key_ids
            rim = getattr(
                getattr(line.product_id, 'tire_measure_id', False),
                'rim_id', False,
            )
            rim_number = self._rim_number(rim)
            if is_key:
                label = 'Key Sizes'
                discount = tier.key_size_discount or 0.0
            else:
                rule = ranges.filtered(
                    lambda r: r.rim_from <= rim_number <= r.rim_to
                )[:1]
                if rule:
                    end = '+' if rule.rim_to >= 99 else str(rule.rim_to)
                    label = 'R%s-%s' % (rule.rim_from, end)
                    discount = rule.discount or 0.0
                else:
                    label = 'Sin beneficio por rin'
                    discount = 0.0

            qty = self._quantity_of(line, quantity_field)
            unit_base = unit_base_by_line.get(line.id)
            if unit_base is not None:
                unit_reward = self.percent_amount(unit_base, discount)
                amount = self.round_money(qty * unit_reward / tax_factor)
                # Base equivalente SIN IVA, solo para el desglose/auditoría.
                base = self.round_money(qty * unit_base / tax_factor)
                origen = 'PMS'
            else:
                # Fallback defensivo para registros viejos. En amount_rim las
                # líneas sin PMS se filtran antes de llegar aquí.
                base = line.price_subtotal
                amount = self.percent_amount(base, discount)
                origen = 'facturado'

            amount_by_line[line.id] = amount
            total += amount
            bucket = buckets[label]
            bucket['discount'] = discount
            bucket['qty'] += qty
            bucket['base'] += base
            bucket['amount'] += amount
            bucket['origen'].add(origen)

        breakdown = [
            (name, vals['discount'], vals['qty'], vals['base'], vals['amount'])
            for name, vals in buckets.items() if vals['qty']
        ]
        return self.round_money(total), amount_by_line, breakdown

    # ------------------------------------------------------------------
    # Key Sizes: productos que cobran otro porcentaje en el mismo tramo
    # ------------------------------------------------------------------
    def key_size_amounts(
        self,
        key_products,
        tier,
        lines,
        base_discount,
        quantity_field='quantity',
        unit_base_by_line=None,
        unit_base_tax_factor=1.0,
    ):
        """NC por línea cuando el tramo alcanzado trae porcentaje de Key Size.

        El tramo ya se eligió con el acumulado completo, los Key Sizes
        incluidos: por eso ayudan a alcanzar el objetivo igual que
        cualquier otra llanta. Aquí solo cambia el porcentaje con el que
        se les paga.

        Si el nivel alcanzado tiene `key_size_discount` en cero, los Key
        Sizes cobran el porcentaje general: no hay que capturar nada.

        `unit_base_by_line` es el precio de UNA pieza sobre el que se
        cobra la línea (precios PMS), **tal como se capturó**.
        `unit_base_tax_factor` es el divisor de IVA que hay que aplicarle
        (1.16 si ese precio trae IVA, 1.0 si no).

        El orden de estas tres operaciones no es intercambiable:

            descuento por pieza = redondear(precio capturado x %)
            NC de la línea      = redondear(piezas x descuento / factor)

        El convenio fija el descuento POR PIEZA sobre su propio precio de
        lista —"$120.95 por llanta, tomado del PMS con IVA"— y esa cifra
        con centavos es la que la marca multiplica. Bajarle el IVA al
        precio ANTES de sacar el porcentaje redondea un número que el
        convenio nunca menciona, y el resultado se desvía: en la
        liquidación real de julio, 2 centavos en el subtotal que al
        timbrar se vuelven 2 centavos sobre una cifra que el proveedor
        tiene en su papel al centavo exacto.

        Una línea que no esté en el diccionario cobra sobre su subtotal
        facturado, nunca sobre cero, para que un código sin precio
        capturado no desaparezca en silencio de la NC.

        :return: ``(total, {line_id: monto}, [(etiqueta, %, cantidad, base, monto)])``
        """
        override = tier.key_size_discount if tier else 0.0
        has_override = not self.is_zero_percent(override)
        product_ids = set(key_products.ids)
        factor = unit_base_tax_factor or 1.0
        amount_by_line = {}
        buckets = defaultdict(lambda: {
            'discount': 0.0,
            'qty': 0.0,
            'base': 0.0,
            'amount': 0.0,
            'key': False,
            'pending': [],
        })
        total = 0.0

        for line in lines:
            is_key_size = (
                has_override
                and self._template_of(line.product_id).id in product_ids
            )
            discount = override if is_key_size else base_discount
            quantity = self._quantity_of(line, quantity_field)

            unit_base = None
            if unit_base_by_line is not None:
                unit_base = unit_base_by_line.get(line.id)

            if unit_base is None:
                base = line.price_subtotal
                # El importe NO se calcula aquí. Con base facturada, el
                # convenio define UN importe por grupo —"NC 13-16" y
                # "NC Key Sizes"— y luego los suma. Redondear renglón
                # por renglón y sumar da un resultado distinto por
                # centavos, y el que manda es el del proveedor.
                amount = None
            else:
                unit_reward = self.percent_amount(unit_base, discount)
                amount = self.round_money(unit_reward * quantity / factor)
                base = self.round_money(unit_base * quantity / factor)

            if amount is not None:
                amount_by_line[line.id] = amount
                total += amount

            # La etiqueta distingue de dónde salió la base, no solo qué
            # porcentaje se cobró. En una promoción mixta —los códigos
            # con precio PMS cobran sobre PMS, los de las listas de
            # mayoreo y outlet sobre su subtotal facturado— el detalle
            # tiene que separar las dos poblaciones: son dos cuentas
            # distintas conviviendo en la misma nota de crédito, y
            # mezclarlas en un solo renglón hace imposible cuadrar
            # ninguna de las dos contra el papel del proveedor.
            #
            # Cuando la promoción no usa PMS en absoluto, las etiquetas
            # se quedan cortas ('Base', 'Key Sizes'): no hay ambigüedad
            # que aclarar y el sufijo solo estorbaría.
            if unit_base_by_line is None:
                label = 'Key Sizes' if is_key_size else 'Base'
            else:
                origen = 'PMS' if unit_base is not None else 'facturado'
                label = '%s (%s)' % (
                    'Key Sizes' if is_key_size else 'Base',
                    origen,
                )

            bucket = buckets[label]
            bucket['discount'] = discount
            bucket['qty'] += quantity
            bucket['base'] += base
            bucket['key'] = is_key_size
            if amount is None:
                bucket['pending'].append((line, base))
            else:
                bucket['amount'] += amount

        # Los grupos con base facturada se cierran ahora. El convenio
        # calcula un importe por grupo —"NC 13-16", "NC Key Sizes"— y
        # suma; NO redondea los grupos, redondea el total. Por eso el
        # importe crudo de cada grupo se acumula sin tocar y el
        # redondeo ocurre una sola vez, sobre la suma.
        #
        # Después hay que repartir ese total redondeado: el último
        # grupo absorbe el residuo, y dentro de cada grupo el último
        # renglón absorbe el suyo. Así el detalle suma exactamente lo
        # que se paga, sin centavos huérfanos. El costo es que un grupo
        # puede mostrar un centavo más que el mismo grupo calculado
        # aislado; es el precio de que la columna cuadre.
        pending_labels = [
            label
            for label, values in sorted(
                buckets.items(),
                key=lambda item: (item[1]['key'], item[0]),
            )
            if values['pending']
        ]
        raw_by_label = {
            label: (buckets[label]['base'] or 0.0)
            * (buckets[label]['discount'] or 0.0)
            / 100.0
            for label in pending_labels
        }
        if pending_labels:
            total = self.round_money(total + sum(raw_by_label.values()))
            remaining_total = total - sum(
                values['amount']
                for label, values in buckets.items()
                if label not in pending_labels
            )
            for label in pending_labels[:-1]:
                amount = self.round_money(raw_by_label[label])
                buckets[label]['amount'] = amount
                remaining_total = self.round_money(remaining_total - amount)
            buckets[pending_labels[-1]]['amount'] = self.round_money(
                remaining_total
            )

        for values in buckets.values():
            if not values['pending']:
                continue
            group_amount = values['amount']
            remaining = group_amount
            group_base = values['base']
            for line, line_base in values['pending'][:-1]:
                share = (
                    self.round_money(group_amount * line_base / group_base)
                    if group_base
                    else 0.0
                )
                amount_by_line[line.id] = share
                remaining = self.round_money(remaining - share)
            last_line, _last_base = values['pending'][-1]
            amount_by_line[last_line.id] = remaining

        # 'Base' antes que 'Key Sizes', y dentro de cada uno el orden
        # alfabético deja 'facturado' antes que 'PMS' de forma estable.
        breakdown = [
            (
                name,
                values['discount'],
                values['qty'],
                values['base'],
                values['amount'],
            )
            for name, values in sorted(
                buckets.items(),
                key=lambda item: (item[1]['key'], item[0]),
            )
        ]
        return self.round_money(total), amount_by_line, breakdown

    def _template_of(self, product):
        """Acepta product.product (documentos) o product.template (detalle)."""
        return getattr(product, 'product_tmpl_id', product) or product

    def _quantity_of(self, line, quantity_field=None):
        """Cantidad de la línea sin importar el modelo que la provea.

        En un recordset se consulta `_fields` y no `getattr(..., 0)`:
        el acceso a un campo inexistente lanza AttributeError antes de
        poder devolver el default.

        Pero no todas las líneas son recordsets. El cotizador arma
        `_NcEvalLine` (objetos Python sueltos, sin `_fields`), así que
        ahí la comprobación se hace con `hasattr`. Sin esto, cualquier
        promoción por rin o con Key Sizes reventaba en el preview.
        """
        candidates = [quantity_field] if quantity_field else []
        candidates += ['quantity', 'product_uom_qty', 'qty']
        model_fields = getattr(line, '_fields', None)
        for name in candidates:
            if not name:
                continue
            if model_fields is not None:
                if name in model_fields:
                    return line[name]
            elif hasattr(line, name):
                return line[name]
        return 0.0

    def format_key_size_breakdown(
        self,
        breakdown,
        tier_value,
        is_amount_policy=False,
        base_label='',
    ):
        """Texto auditable que CUADRA: cada grupo con su base y su importe.

        El formato es deliberado. La columna `% efectivo` NO puede
        reconstruir el total y no hay número de decimales que lo
        arregle: el total es la suma de importes redondeados a centavos,
        no el producto de una multiplicación. Con la mezcla del ejemplo
        —275 pza al 4.20% y 60 al 6.00%— el efectivo real es
        4.4337935569%; guardado con 4 decimales reconstruye 30,347.14
        contra 30,347.10 reales. Con 6 decimales acierta ese caso y
        falla otros.

        Lo que sí cuadra es esto: cada grupo con las piezas, el
        porcentaje, LA BASE sobre la que se aplicó y el importe que
        salió; al final, la suma. Cada renglón se puede verificar con
        una calculadora y los renglones suman el total.

        `base_label` dice de dónde salieron esas bases cuando no son el
        subtotal facturado (precios PMS).
        """
        parts = [
            '%s: %s pza x %.2f%% sobre %s = %s' % (
                name,
                self.format_quantity(quantity),
                discount,
                self.format_money(base),
                self.format_money(amount),
            )
            for name, discount, quantity, base, amount in breakdown
            if quantity
        ]
        if not parts:
            return ''
        accumulated = (
            '$%s' % format(tier_value, ',.2f')
            if is_amount_policy
            else '%s pza' % self.format_quantity(tier_value)
        )
        total = sum(item[4] for item in breakdown)
        text = 'Acumulado %s | %s | Total %s' % (
            accumulated,
            ' + '.join(parts),
            self.format_money(total),
        )
        if base_label:
            text += ' (%s)' % base_label
        return text

    # ------------------------------------------------------------------
    # Volumen mensual
    # ------------------------------------------------------------------
    def monthly_volume_discount(
        self,
        policies,
        detailed_lines,
        total_quantity=None,
    ):
        """Evalúa volumen total, medidas distintas y mínimo por medida.

        ``total_quantity`` permite abrir el tramo con la cantidad global
        facturada (incluyendo productos que no participan). Las medidas y su
        mínimo siempre se validan con ``detailed_lines`` para que los productos
        ajenos a la promoción no satisfagan esas dos condiciones.
        """
        eligible_lines = detailed_lines.filtered(
            lambda line: (
                line.state == 'valid'
                and line.product_id
                and line.product_id.tire_measure_id
            )
        )
        if total_quantity is None:
            total_quantity = sum(eligible_lines.mapped('quantity'))
        quantity_by_measure = defaultdict(float)
        for line in eligible_lines:
            measure = line.product_id.tire_measure_id
            quantity_by_measure[measure.id] += line.quantity

        reached_policies = []
        for policy in policies:
            measures_reached = sum(
                quantity >= policy.minimum_qty_per_measure
                for quantity in quantity_by_measure.values()
            )
            # Volumen mensual es una escalera de objetivos acumulativos, no
            # una colección de cubos excluyentes. Si el cliente rebasa el
            # límite superior de un nivel, pero todavía no cumple las medidas
            # del siguiente, conserva el nivel anterior que sí alcanzó.
            #
            # Ejemplo: 202 piezas globales + 8 medidas sí cumplen el nivel
            # 100/8 (1%), aunque todavía no cumplan el nivel 200/12 (3%).
            if total_quantity < policy.lower_limit:
                continue
            if measures_reached >= policy.minimum_products:
                reached_policies.append(policy)

        if not reached_policies:
            return 0.0
        highest_policy = max(
            reached_policies,
            key=lambda policy: policy.lower_limit,
        )
        return highest_policy.discount

    # ------------------------------------------------------------------
    # Cupones
    # ------------------------------------------------------------------
    def coupon_amounts(self, coupons, lines, limit_per_product):
        """Aplica el tope de piezas por producto sobre un conjunto de líneas.

        Devuelve ``(total, {line_id: monto}, {line_id: estado})``. El tope
        se aplica sobre TODAS las líneas recibidas, así que quien llame
        debe pasar el universo correcto (por cliente, no por RFC) para no
        duplicar el beneficio.

        El importe de cada cupón se captura CON IVA y aquí se baja, igual
        que el monto fijo: de aquí sale directo a la nota de crédito, que
        volverá a sumarle el IVA al timbrarse.
        """
        amount_by_product = {
            coupon.product_id.id: self.untaxed(coupon.amount)
            for coupon in coupons
        }
        lines_by_product = defaultdict(list)
        # Orden cronológico estable: las líneas sin fecha van primero y
        # nunca se comparan contra un objeto date.
        for line in lines.sorted(
            lambda item: (item.date or date_type.min, item.id)
        ):
            lines_by_product[line.product_id.id].append(line)

        total = 0.0
        amount_by_line = {}
        state_by_line = {}

        for product_id, product_lines in lines_by_product.items():
            coupon_amount = amount_by_product.get(product_id)
            if coupon_amount is None:
                for line in product_lines:
                    amount_by_line[line.id] = 0.0
                    state_by_line[line.id] = 'invalid'
                continue

            remaining = limit_per_product
            for line in product_lines:
                if remaining <= 0:
                    amount_by_line[line.id] = 0.0
                    state_by_line[line.id] = 'invalid'
                    continue

                applied_quantity = min(line.quantity, remaining)
                amount = self.round_money(applied_quantity * coupon_amount)
                amount_by_line[line.id] = amount
                total += amount
                remaining -= applied_quantity
                state_by_line[line.id] = (
                    'valid'
                    if applied_quantity == line.quantity
                    else 'partial'
                )

        return self.round_money(total), amount_by_line, state_by_line
