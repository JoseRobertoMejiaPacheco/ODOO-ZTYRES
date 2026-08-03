# -*- coding: utf-8 -*-
"""
Evaluación "en vivo" de una promoción sobre un documento de venta
(cotización, orden o factura), en lugar del cálculo masivo histórico.

Responde: "esta cotización/factura, ¿califica para esta promoción
aprobada, y cuánto se ganaría en NC?", mirando solo lo que aporta ESE
documento.

Usa exactamente los mismos dos ejes que el cálculo masivo:

    alcance  -> `_promo_line_matches` (qué líneas participan)
    política -> el motor de beneficios (cuánto se gana)

Antes esto tenía el mismo defecto que `_get_domain`: si la política era
por rin, el alcance se ignoraba y participaba cualquier llanta con ese
rin, de cualquier marca. Ahora el rin solo puede RESTRINGIR lo que el
alcance ya admitió.

Simplificaciones deliberadas frente al cálculo masivo:
- No considera `apply_on_groups` / `apply_volume`: requieren ver todo el
  histórico, no un documento.
- En cupones no se aplica el tope por producto: ese tope es un acumulado
  del periodo, no algo evaluable en un solo documento.
"""
from odoo import models

from .ztyres_promo_config import (
    POLICY_AMOUNT,
    POLICY_MONTHLY_VOLUME,
    POLICY_QUANTITY,
    REWARD_FIXED_AMOUNT,
    SCOPE_ATTRIBUTE_COMBINATION,
    SCOPE_COUPONS,
    SCOPE_RIM_POLICY,
    SCOPE_SPECIFIC_PRODUCTS,
    SCOPE_TIRE_FEATURE,
    TIER_POLICIES,
)

# Estados de promoción que cuentan como vigentes para este cálculo.
EVAL_VALID_STATUSES = ('approve_p', 'done')


class ZtyresVolumenEval(models.Model):
    _inherit = 'ztyres_promo.notas_credito'

    _EVAL_VALID_STATUSES = EVAL_VALID_STATUSES

    # ------------------------------------------------------------------
    # Filtros de elegibilidad
    # ------------------------------------------------------------------
    def _promo_is_in_date_range(self, doc_date):
        self.ensure_one()
        if not doc_date:
            return False
        if self.start_date and doc_date < self.start_date:
            return False
        if self.end_date and doc_date > self.end_date:
            return False
        return True

    def _promo_partner_excluded(self, partner, edi_vat_receptor=False):
        self.ensure_one()
        if partner and partner.id in self.excluded_partner_ids.ids:
            return True
        if self.generic_edi == 'no' and edi_vat_receptor == 'XAXX010101000':
            return True
        return False

    # ------------------------------------------------------------------
    # EJE 1: ¿la línea participa?
    # ------------------------------------------------------------------
    def _promo_line_matches(self, line):
        """Alcance AND restricción de la política, en ese orden."""
        self.ensure_one()
        if not line.product_id:
            return False
        if not self._matches_scope(line):
            return False
        return self._matches_policy_restriction(line)

    def _matches_scope(self, line):
        self.ensure_one()
        product = line.product_id
        scope = self._get_scope()

        if scope == SCOPE_COUPONS:
            return product.product_tmpl_id in self.coupon_ids.mapped('product_id')

        if scope == SCOPE_SPECIFIC_PRODUCTS:
            return product.product_tmpl_id in self.product_ids

        if scope == SCOPE_RIM_POLICY:
            return self._matches_policy_rims(product)

        if scope == SCOPE_TIRE_FEATURE:
            checks = self._get_line_feature_checks(line)
            if self.price_list_ids:
                checks.append(
                    self._get_line_price_list_origin(line)
                    in self.price_list_ids.mapped('name')
                )
            return any(checks)

        if scope == SCOPE_ATTRIBUTE_COMBINATION:
            active_criteria = self._get_active_product_criteria(product)
            if len(active_criteria) < 2:
                return False
            return all(
                value and value.id in allowed_records.ids
                for allowed_records, value in active_criteria
            )

        return False

    def _matches_policy_restriction(self, line):
        """La política por rin solo restringe; ninguna otra restringe."""
        self.ensure_one()
        if not self._is_rim_quantity_promotion():
            return True
        if self._get_scope() == SCOPE_RIM_POLICY:
            return True
        return self._matches_policy_rims(line.product_id)

    def _matches_policy_rims(self, product):
        self.ensure_one()
        rim = product.tire_measure_id.rim_id
        return bool(rim) and rim in self.rim_policy_line_ids.mapped('rim_ids')

    def _get_active_product_criteria(self, product):
        criteria = (
            (self.brand_ids, product.brand_id),
            (self.tier_ids, product.tier_id),
            (self.measure_ids, product.tire_measure_id),
            (self.segment_ids, product.segment_id),
            (self.rin_ids, product.tire_measure_id.rim_id),
            (self.face_ids, product.face_id),
            (self.layer_ids, product.layer_id),
            (self.model_ids, product.model_id),
        )
        return [
            (allowed_records, value)
            for allowed_records, value in criteria
            if allowed_records
        ]

    def _get_line_feature_checks(self, line):
        product = line.product_id
        checks = [
            bool(value) and value.id in allowed_records.ids
            for allowed_records, value in self._get_active_product_criteria(product)
        ]
        if self.product_ids:
            checks.append(product.product_tmpl_id in self.product_ids)
        return checks

    def _get_line_price_list_origin(self, line):
        origin = getattr(line, 'list_origin', False)
        if origin:
            return origin
        sale_lines = getattr(line, 'sale_line_ids', self.env['sale.order.line'])
        return sale_lines[:1].list_origin if sale_lines else False

    # ------------------------------------------------------------------
    # EJE 2: ¿cuánto se gana?
    # ------------------------------------------------------------------
    def _build_line_ganado_map(
        self,
        matched_lines,
        quantity_field,
        discount_percent,
        fixed_amount=0.0,
    ):
        """Monto ganado atribuible a CADA línea.

        Es la base de todo lo demás (total de la promoción, desglose por
        producto y el campo expuesto en las líneas del documento), para
        que nunca queden desincronizados.
        """
        self.ensure_one()
        engine = self.env['ztyres_promo.reward_engine']

        if self._is_rim_quantity_promotion():
            accumulated_quantity = sum(matched_lines.mapped(quantity_field))
            _total, amount_by_line, _breakdown = engine.rim_amounts(
                self.rim_policy_line_ids,
                matched_lines,
                accumulated_quantity,
            )
            return amount_by_line

        if self._is_coupon_promotion():
            amount_by_product = {
                coupon.product_id.id: coupon.amount
                for coupon in self.coupon_ids
            }
            return {
                line.id: line[quantity_field] * amount_by_product.get(
                    line.product_id.product_tmpl_id.id,
                    0.0,
                )
                for line in matched_lines
            }

        if self._get_policy() not in TIER_POLICIES:
            return {}

        if self._effective_reward_type() == REWARD_FIXED_AMOUNT:
            return self._allocate_fixed_amount_by_line(
                matched_lines,
                fixed_amount,
            )

        if self._has_key_sizes():
            policies = self._active_policy_lines()
            tier_value = (
                sum(matched_lines.mapped('price_subtotal'))
                if self._uses_amount_policy()
                else sum(matched_lines.mapped(quantity_field))
            )
            _total, amount_by_line, _breakdown = engine.key_size_amounts(
                self.key_size_product_ids,
                engine.matching_tier(
                    policies,
                    tier_value,
                    quantity=sum(matched_lines.mapped(quantity_field)),
                ),
                matched_lines,
                discount_percent or 0.0,
                quantity_field=quantity_field,
            )
            return amount_by_line

        return {
            line.id: line.price_subtotal * (discount_percent or 0) / 100
            for line in matched_lines
        }

    def _allocate_fixed_amount_by_line(self, matched_lines, fixed_amount):
        total_subtotal = sum(matched_lines.mapped('price_subtotal'))
        if total_subtotal <= 0 or fixed_amount <= 0:
            return {}
        result = {}
        remaining = fixed_amount
        ordered_lines = matched_lines.sorted('id')
        for line in ordered_lines[:-1]:
            allocated = round(
                fixed_amount * line.price_subtotal / total_subtotal,
                2,
            )
            result[line.id] = allocated
            remaining -= allocated
        result[ordered_lines[-1].id] = round(remaining, 2)
        return result

    def _build_product_breakdown(self, matched_lines, quantity_field, line_ganado_map):
        """Agrupa el mapa por producto para el texto 'Por Producto'."""
        groups = {}
        order = []
        for line in matched_lines:
            product = line.product_id.product_tmpl_id
            key = product.id
            if key not in groups:
                groups[key] = {
                    'product_name': product.name,
                    'qty': 0.0,
                    'amount': 0.0,
                    'ganado': 0.0,
                }
                order.append(key)
            groups[key]['qty'] += line[quantity_field]
            groups[key]['amount'] += line.price_subtotal
            groups[key]['ganado'] += line_ganado_map.get(line.id, 0.0)
        return [groups[key] for key in order]

    # ------------------------------------------------------------------
    # Entrada pública
    # ------------------------------------------------------------------
    def evaluate_document(
        self,
        partner,
        doc_date,
        lines,
        quantity_field,
        edi_vat_receptor=False,
    ):
        """Evalúa esta promoción contra las líneas de un documento.

        :param partner: res.partner del documento
        :param doc_date: fecha del documento, para validar vigencia
        :param lines: recordset de líneas (sale.order.line o account.move.line)
        :param quantity_field: 'product_uom_qty' en órdenes, 'quantity' en facturas
        :param edi_vat_receptor: RFC receptor de la factura, si aplica
        :return: dict con el resultado, o None si la promoción no aplica.
        """
        self.ensure_one()

        if self.status not in EVAL_VALID_STATUSES:
            return None
        if not self._promo_is_in_date_range(doc_date):
            return None
        if self._promo_partner_excluded(partner, edi_vat_receptor):
            return None

        matched_lines = lines.filtered(
            lambda line: (
                line.product_id
                and line.display_type not in ('line_section', 'line_note')
                and self._promo_line_matches(line)
            )
        )
        if not matched_lines:
            return None

        quantity = sum(matched_lines.mapped(quantity_field))
        amount = sum(matched_lines.mapped('price_subtotal'))

        discount_percent, fixed_amount = self._evaluate_document_reward(
            quantity,
            amount,
        )
        if discount_percent is None:
            return None

        line_ganado_map = self._build_line_ganado_map(
            matched_lines,
            quantity_field,
            discount_percent,
            fixed_amount,
        )
        ganado = sum(line_ganado_map.values())
        if ganado <= 0:
            return None

        return {
            'promo': self,
            'qty': quantity,
            'amount': amount,
            'discount_percent': (
                None
                if (
                    self._is_rim_quantity_promotion()
                    or self._has_key_sizes()
                    or self._effective_reward_type() == REWARD_FIXED_AMOUNT
                )
                else discount_percent
            ),
            'ganado': ganado,
            'lines': self._build_product_breakdown(
                matched_lines,
                quantity_field,
                line_ganado_map,
            ),
            'line_ganado_map': line_ganado_map,
        }

    def _evaluate_document_reward(self, quantity, amount):
        """(porcentaje, monto fijo) o (None, None) si no es evaluable aquí."""
        self.ensure_one()
        engine = self.env['ztyres_promo.reward_engine']
        policy = self._get_policy()

        if self._is_rim_quantity_promotion() or self._is_coupon_promotion():
            return 0.0, 0.0

        if policy == POLICY_QUANTITY:
            return engine.tier_reward(
                self.policy_line_qty_ids,
                quantity,
                self._effective_reward_type(),
                quantity=quantity,
            )

        if policy == POLICY_AMOUNT:
            return engine.tier_reward(
                self.policy_line_amount_ids,
                amount,
                self._effective_reward_type(),
                quantity=quantity,
            )

        if policy == POLICY_MONTHLY_VOLUME:
            # Depende del acumulado del periodo completo del cliente.
            return None, None

        return None, None
