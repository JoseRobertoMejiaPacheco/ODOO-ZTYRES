# -*- coding: utf-8 -*-
"""
Del alcance al dominio de búsqueda.

Regla única de este archivo:

    universo = condiciones obligatorias
             AND alcance (promo_conditions)
             AND restricción de la política (si la política restringe)

La política NUNCA sustituye al alcance. Antes sí lo hacía: si la
política era "Cantidad Acumulada por Rin", `_get_domain` regresaba de
inmediato con los rines de la tabla de políticas y descartaba marca,
tier, medida, segmento y los rines del propio alcance. Una promoción de
DUNLOP/FALKEN terminaba pagando NC sobre llantas de cualquier marca que
tuviera esos rines.
"""

from odoo import _, models
from odoo.exceptions import UserError
from odoo.osv import expression

from .ztyres_promo_config import (
    POLICY_RIM_QUANTITY,
    SCOPE_ATTRIBUTE_COMBINATION,
    SCOPE_COUPONS,
    SCOPE_RIM_POLICY,
    SCOPE_SPECIFIC_PRODUCTS,
    SCOPE_TIRE_FEATURE,
)


class ZtyresPromoCreditNoteDomain(models.Model):
    _inherit = 'ztyres_promo.notas_credito'

    # ------------------------------------------------------------------
    # Condiciones obligatorias
    # ------------------------------------------------------------------
    def _base_invoice_line_domain(self):
        """Lo que siempre se cumple, sin importar alcance ni política."""
        self.ensure_one()
        return [
            ('move_id.move_type', 'in', ('out_invoice', 'out_refund')),
            ('move_id.state', '=', 'posted'),
            ('product_id.detailed_type', '=', 'product'),
            ('display_type', '=', 'product'),
            ('move_id.invoice_date', '>=', self.start_date),
            ('move_id.invoice_date', '<=', self.end_date),
            ('partner_id', '!=', False),
        ]

    # ------------------------------------------------------------------
    # Dominio completo
    # ------------------------------------------------------------------
    def _get_domain(self):
        """Universo participante = base AND alcance AND política."""
        self.ensure_one()
        parts = [self._base_invoice_line_domain(), self._get_scope_domain()]
        policy_domain = self._get_policy_domain()
        if policy_domain:
            parts.append(policy_domain)
        return expression.AND(parts)

    def _get_scope_domain(self):
        """EJE 1: qué productos participan."""
        self.ensure_one()
        scope = self._get_scope()

        if not scope:
            raise UserError(_(
                'Seleccione el alcance de productos de la promoción.'
            ))

        if scope == SCOPE_COUPONS:
            return self._get_coupon_products_domain()

        if scope == SCOPE_SPECIFIC_PRODUCTS:
            return self._get_specific_products_domain()

        if scope == SCOPE_RIM_POLICY:
            return self._get_rim_policy_domain(required=True)

        criteria = self._get_product_domains(
            include_extended=(scope == SCOPE_TIRE_FEATURE)
        )

        if scope == SCOPE_TIRE_FEATURE:
            if not criteria:
                raise UserError(_(
                    'Configure al menos un criterio de producto para la '
                    'promoción.'
                ))
            return expression.OR(criteria)

        if scope == SCOPE_ATTRIBUTE_COMBINATION:
            if len(criteria) < 2:
                raise UserError(_(
                    'Seleccione al menos dos características para una '
                    'promoción de tipo "Combinación de Características".'
                ))
            return expression.AND(criteria)

        raise UserError(_('Seleccione un alcance de productos válido.'))

    def _get_policy_domain(self):
        """EJE 2: la política solo puede restringir el universo.

        Únicamente "Cantidad Acumulada por Rin" restringe: solo las
        líneas cuyo rin aparece en algún tramo pueden generar NC. Si el
        alcance ya es "Rines de las Políticas" la restricción es la
        misma y no se duplica.
        """
        self.ensure_one()
        if self._get_policy() != POLICY_RIM_QUANTITY:
            return []
        if self._get_scope() == SCOPE_RIM_POLICY:
            return []
        return self._get_rim_policy_domain(required=True)

    # ------------------------------------------------------------------
    # Piezas del alcance
    # ------------------------------------------------------------------
    def _get_rim_policy_domain(self, required=False):
        self.ensure_one()
        rines = self.rim_policy_line_ids.mapped('rim_ids')
        if not rines:
            if required:
                raise UserError(_(
                    'Configure al menos una política con rines participantes.'
                ))
            return []
        return [('product_id.tire_measure_id.rim_id', 'in', rines.ids)]

    def _get_coupon_products_domain(self):
        """En cupones, cada línea cargada define producto y recompensa."""
        self.ensure_one()
        products = self.coupon_ids.mapped('product_id')
        if not products:
            raise UserError(_(
                'Cargue al menos un producto con monto en la sección Cupones.'
            ))
        return [(
            'product_id',
            'in',
            products.mapped('product_variant_ids').ids,
        )]

    def _get_specific_products_domain(self):
        self.ensure_one()
        if not self.product_ids:
            raise UserError(_(
                'Cargue al menos un producto para la promoción de '
                'Productos / Códigos Específicos.'
            ))
        return [(
            'product_id',
            'in',
            self.product_ids.mapped('product_variant_ids').ids,
        )]

    def _get_product_domains(self, include_extended=False):
        """Cada criterio es un dominio independiente, listo para AND/OR."""
        self.ensure_one()
        configured_fields = (
            (self.brand_ids, 'product_id.brand_id'),
            (self.tier_ids, 'product_id.tier_id'),
            (self.measure_ids, 'product_id.tire_measure_id'),
            (self.segment_ids, 'product_id.segment_id'),
            (self.rin_ids, 'product_id.tire_measure_id.rim_id'),
            (self.face_ids, 'product_id.face_id'),
            (self.layer_ids, 'product_id.layer_id'),
            (self.model_ids, 'product_id.model_id'),
        )
        domains = [
            [(field_name, 'in', records.ids)]
            for records, field_name in configured_fields
            if records
        ]

        # Solo el modo OR admite estos dos criterios adicionales: en el
        # modo AND obligarían a que el producto esté además en la lista
        # manual, que casi nunca es lo que se quiere.
        if include_extended and self.product_ids:
            domains.append([(
                'product_id',
                'in',
                self.product_ids.mapped('product_variant_ids').ids,
            )])
        if include_extended and self.price_list_ids:
            domains.append([(
                'sol_id.list_origin',
                'in',
                self.price_list_ids.mapped('name'),
            )])
        return domains

    # ------------------------------------------------------------------
    # Agrupaciones para el beneficio por grupo de clientes
    # ------------------------------------------------------------------
    def get_grouped_data(self, promo_type=None):
        """Acumulado por grupo de clientes, según la política."""
        self.ensure_one()
        aggregate_by_type = {
            'quantity': ('quantity:sum', 'quantity'),
            'amount': ('price_subtotal:sum', 'price_subtotal'),
        }
        aggregate = aggregate_by_type.get(promo_type or self._get_policy())
        if not aggregate:
            return []

        return self._read_group_values(
            model_name='ztyres_promo.notas_credito_lines',
            record_ids=self.line_ids.ids,
            field_spec=aggregate[0],
            result_key=aggregate[1],
        )

    def get_grouped_data_volume(self):
        """Cantidad global por grupo: incluye lo que no participa.

        Solo se usa cuando 'Aplicar por cantidad global' está en Sí.
        """
        self.ensure_one()
        return self._read_group_values(
            model_name='ztyres_promo.lines',
            record_ids=self.detailed_line_ids.ids,
            field_spec='quantity:sum',
            result_key='quantity',
        )

    def _read_group_values(self, model_name, record_ids, field_spec, result_key):
        """Acumulado por grupo, agrupando por el Many2one real.

        Antes se agrupaba por `group_name` (Char). Dos grupos con el
        mismo nombre caían en el mismo cubo y compartían acumulado, así
        que el módulo se protegía prohibiendo nombres duplicados: si
        existían, el cálculo entero se detenía con un UserError. Al
        agrupar por `group_id` ese conflicto deja de existir y la
        restricción sobra — los nombres vuelven a ser solo etiquetas.

        Devuelve una lista de tuplas (registro de grupo, valor).
        """
        if not record_ids:
            return []

        rows = self.env[model_name].read_group(
            domain=[
                ('id', 'in', record_ids),
                ('group_id', '!=', False),
            ],
            fields=['group_id', field_spec],
            groupby=['group_id'],
            orderby='group_id',
        )

        group_model = self.env['ztyres_volumen.group']
        result = []
        for row in rows:
            raw = row.get('group_id')
            # read_group regresa el Many2one como (id, display_name).
            group_id = raw[0] if isinstance(raw, (list, tuple)) and raw else raw
            if not group_id:
                continue
            result.append((group_model.browse(group_id), row[result_key]))
        return result
