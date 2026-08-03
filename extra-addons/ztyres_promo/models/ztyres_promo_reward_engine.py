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

from .ztyres_promo_config import (
    REWARD_FIXED_AMOUNT,
    normalize_upper_limit,
)


class ZtyresPromoRewardEngine(models.AbstractModel):
    _name = 'ztyres_promo.reward_engine'
    _description = 'Motor de cálculo de beneficios de promociones'

    # ------------------------------------------------------------------
    # Tramos genéricos (Cantidad / Monto)
    # ------------------------------------------------------------------
    def tier_matches(self, policy, value, quantity=None):
        """¿El acumulado cae dentro de este tramo?"""
        upper_limit = normalize_upper_limit(policy.upper_limit)
        if value < policy.lower_limit or value > upper_limit:
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

    def tier_reward(self, policies, value, reward_type, quantity=None):
        """Devuelve ``(porcentaje, monto_fijo)`` del tramo alcanzado."""
        policy = self.matching_tier(policies, value, quantity)
        if not policy:
            return 0.0, 0.0
        if reward_type == REWARD_FIXED_AMOUNT:
            return 0.0, policy.fixed_amount
        return policy.discount, 0.0

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
        by_rim = defaultdict(lambda: {'discount': 0.0, 'qty': 0.0, 'amount': 0.0})
        total = 0.0

        for line in lines:
            rim = line.product_id.tire_measure_id.rim_id
            discount = self.rim_discount(
                rim_policies,
                rim,
                accumulated_quantity,
            )
            amount = line.price_subtotal * discount / 100
            amount_by_line[line.id] = amount
            total += amount

            bucket = by_rim[rim.display_name if rim else 'Sin rin']
            bucket['discount'] = discount
            bucket['qty'] += self._quantity_of(line, quantity_field)
            bucket['amount'] += amount

        breakdown = [
            (name, values['discount'], values['qty'], values['amount'])
            for name, values in sorted(by_rim.items())
        ]
        return total, amount_by_line, breakdown

    def format_rim_breakdown(self, breakdown, accumulated_quantity):
        """Texto auditable: por qué salió ese porcentaje efectivo."""
        parts = [
            '%s: %s pza x %.2f%%' % (name, int(quantity), discount)
            for name, discount, quantity, _amount in breakdown
            if quantity
        ]
        if not parts:
            return ''
        return 'Acumulado %s pza | %s' % (
            int(accumulated_quantity),
            ' + '.join(parts),
        )

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
    ):
        """NC por línea cuando el tramo alcanzado trae porcentaje de Key Size.

        El tramo ya se eligió con el acumulado completo, los Key Sizes
        incluidos: por eso ayudan a alcanzar el objetivo igual que
        cualquier otra llanta. Aquí solo cambia el porcentaje con el que
        se les paga.

        Si el nivel alcanzado tiene `key_size_discount` en cero, los Key
        Sizes cobran el porcentaje general: no hay que capturar nada.

        :return: ``(total, {line_id: monto}, [(etiqueta, %, cantidad, monto)])``
        """
        override = tier.key_size_discount if tier else 0.0
        product_ids = set(key_products.ids)
        amount_by_line = {}
        buckets = defaultdict(
            lambda: {'discount': 0.0, 'qty': 0.0, 'amount': 0.0, 'key': False}
        )
        total = 0.0

        for line in lines:
            is_key_size = (
                override > 0
                and self._template_of(line.product_id).id in product_ids
            )
            discount = override if is_key_size else base_discount
            amount = line.price_subtotal * discount / 100
            amount_by_line[line.id] = amount
            total += amount

            bucket = buckets['Key Sizes' if is_key_size else 'Base']
            bucket['discount'] = discount
            bucket['qty'] += self._quantity_of(line, quantity_field)
            bucket['amount'] += amount
            bucket['key'] = is_key_size

        # 'Base' primero, 'Key Sizes' después.
        breakdown = [
            (name, values['discount'], values['qty'], values['amount'])
            for name, values in sorted(
                buckets.items(),
                key=lambda item: item[1]['key'],
            )
        ]
        return total, amount_by_line, breakdown

    def _template_of(self, product):
        """Acepta product.product (documentos) o product.template (detalle)."""
        return getattr(product, 'product_tmpl_id', product) or product

    def _quantity_of(self, line, quantity_field=None):
        """Cantidad de la línea sin importar el modelo que la provea.

        Se consulta `_fields` y no `getattr(..., 0)`: en un recordset el
        acceso a un campo inexistente lanza AttributeError antes de poder
        devolver el default.
        """
        candidates = [quantity_field] if quantity_field else []
        candidates += ['quantity', 'product_uom_qty', 'qty']
        for name in candidates:
            if name and name in line._fields:
                return line[name]
        return 0.0

    def format_key_size_breakdown(
        self,
        breakdown,
        tier_value,
        is_amount_policy=False,
    ):
        """Texto auditable: qué cobró el % general y qué los Key Sizes."""
        parts = [
            '%s: %s pza x %.2f%%' % (name, int(quantity), discount)
            for name, discount, quantity, _amount in breakdown
            if quantity
        ]
        if not parts:
            return ''
        accumulated = (
            '$%s' % format(tier_value, ',.2f')
            if is_amount_policy
            else '%s pza' % int(tier_value)
        )
        return 'Acumulado %s | %s' % (accumulated, ' + '.join(parts))

    # ------------------------------------------------------------------
    # Volumen mensual
    # ------------------------------------------------------------------
    def monthly_volume_discount(self, policies, detailed_lines):
        """Evalúa volumen total, medidas distintas y mínimo por medida."""
        eligible_lines = detailed_lines.filtered(
            lambda line: (
                line.state == 'valid'
                and line.product_id
                and line.product_id.tire_measure_id
            )
        )
        total_quantity = sum(eligible_lines.mapped('quantity'))
        quantity_by_measure = defaultdict(float)
        for line in eligible_lines:
            measure = line.product_id.tire_measure_id
            quantity_by_measure[measure.id] += line.quantity

        discounts = []
        for policy in policies:
            measures_reached = sum(
                quantity >= policy.minimum_qty_per_measure
                for quantity in quantity_by_measure.values()
            )
            if not self.tier_matches(policy, total_quantity):
                continue
            if measures_reached >= policy.minimum_products:
                discounts.append(policy.discount)

        return max(discounts, default=0.0)

    # ------------------------------------------------------------------
    # Cupones
    # ------------------------------------------------------------------
    def coupon_amounts(self, coupons, lines, limit_per_product):
        """Aplica el tope de piezas por producto sobre un conjunto de líneas.

        Devuelve ``(total, {line_id: monto}, {line_id: estado})``. El tope
        se aplica sobre TODAS las líneas recibidas, así que quien llame
        debe pasar el universo correcto (por cliente, no por RFC) para no
        duplicar el beneficio.
        """
        amount_by_product = {
            coupon.product_id.id: coupon.amount
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
                amount = applied_quantity * coupon_amount
                amount_by_line[line.id] = amount
                total += amount
                remaining -= applied_quantity
                state_by_line[line.id] = (
                    'valid'
                    if applied_quantity == line.quantity
                    else 'partial'
                )

        return total, amount_by_line, state_by_line
