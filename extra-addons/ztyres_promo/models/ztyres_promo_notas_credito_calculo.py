# -*- coding: utf-8 -*-
"""
Cálculo histórico de promociones y notas de crédito.

Orden del proceso (botón "Calcular NC"):

1. valida que alcance y política sean coherentes y estén completos;
2. borra resultados anteriores;
3. crea el detalle auditable (válido / inválido / parcial);
4. aplica el tope de cupones, si la promoción es de cupones;
5. arma un resultado por (cliente, RFC receptor);
6. si aplican grupos, recalcula el beneficio con el acumulado del grupo;
7. recalcula el importe final de cada NC.

Correcciones importantes frente a la versión anterior:

- El universo participante sale del alcance (ver ..._domain.py), no de
  la tabla de políticas.
- El beneficio de grupo por rin ya no mezcla clientes distintos que
  comparten RFC genérico: la reasignación se hace por (cliente, RFC).
- El tope de cupones se aplica por cliente, no por RFC, así que un
  cliente con factura fiscal y de mostrador ya no lo duplica.
- Las líneas de resultado en cero siguen visibles para el motor, así
  que sí reciben el beneficio de grupo cuando les corresponde.
- El detalle se crea en lote y los acumulados se calculan una sola vez.
"""

from collections import defaultdict

from odoo import _, models
from odoo.exceptions import UserError

from .ztyres_promo_config import (
    DEFAULT_COUPON_LIMIT_QTY,
    POLICY_AMOUNT,
    POLICY_MONTHLY_VOLUME,
    POLICY_QUANTITY,
    REWARD_FIXED_AMOUNT,
    REWARD_PERCENTAGE,
    TIER_POLICIES,
)

# Se conserva el nombre público por compatibilidad con integraciones
# existentes; el valor real se toma de `coupon_limit_qty`.
COUPON_LIMIT_PER_PRODUCT = DEFAULT_COUPON_LIMIT_QTY
GENERIC_RFC = 'XAXX010101000'


class ZtyresPromoCreditNoteCalculation(models.Model):
    _inherit = 'ztyres_promo.notas_credito'

    # ==================================================================
    # Punto de entrada
    # ==================================================================
    def action_calcular_nc(self):
        """Recalcula el detalle y el resultado definitivo de la promoción."""
        self.ensure_one()
        self._validate_configuration()
        self._clear_previous_lines()
        self._create_detailed_lines()
        self._update_missing_partner_vat_warning()
        self._create_result_lines()
        self._apply_group_rewards()
        self._recompute_nc_amounts()
        if self.missing_partner_vat_warning:
            return self._missing_partner_vat_notification()
        return True

    @property
    def _engine(self):
        return self.env['ztyres_promo.reward_engine']

    # ==================================================================
    # Validación previa
    # ==================================================================
    def _validate_configuration(self):
        """Un solo lugar valida alcance + política antes de calcular."""
        self.ensure_one()
        if not self._get_scope():
            raise UserError(_(
                'Seleccione el alcance de productos de la promoción.'
            ))
        if not self._get_policy():
            raise UserError(_('Seleccione el tipo de política.'))

        if self._is_coupon_promotion():
            if not self.coupon_ids:
                raise UserError(_(
                    'Cargue al menos un producto con monto en la sección '
                    'Cupones.'
                ))
            return

        if self._is_rim_quantity_promotion():
            if not self.rim_policy_line_ids:
                raise UserError(_(
                    'Configure al menos un nivel de beneficio por rin.'
                ))
            return

        if self._get_policy() == POLICY_MONTHLY_VOLUME:
            if not self.monthly_volume_line_ids:
                raise UserError(_(
                    'Configure al menos un nivel de volumen mensual.'
                ))
            return

        if self._get_policy() not in TIER_POLICIES:
            return

        policies = self._active_policy_lines()
        if not policies:
            raise UserError(_('Configure al menos un nivel de beneficio.'))

        if self._effective_reward_type() == REWARD_FIXED_AMOUNT:
            invalid = policies.filtered(lambda policy: policy.fixed_amount <= 0)
            if invalid:
                raise UserError(_(
                    'Todos los niveles deben tener un monto fijo mayor que '
                    'cero.'
                ))
            return

        invalid = policies.filtered(
            lambda policy: not 0 < policy.discount <= 100
        )
        if invalid:
            raise UserError(_(
                'Todos los porcentajes deben ser mayores que cero y no '
                'superar 100. Se permiten decimales, por ejemplo 2.10.'
            ))

    # ==================================================================
    # Detalle auditable
    # ==================================================================
    def _clear_previous_lines(self):
        self.ensure_one()
        self.missing_partner_vat_warning = False
        self.env['ztyres_promo.notas_credito_lines'].search([
            ('definitive_nc_id', '=', self.id),
        ]).unlink()
        self.env['ztyres_promo.lines'].search([
            ('definitive_nc_id', '=', self.id),
        ]).unlink()
        self.invalidate_recordset(['line_ids', 'detailed_line_ids'])

    def _create_detailed_lines(self):
        """Crea en lote las líneas participantes y las descartadas."""
        self.ensure_one()
        move_lines = self.env['account.move.line']
        all_lines = move_lines.search(self._base_invoice_line_domain())
        valid_lines = move_lines.search(self._get_domain())
        invalid_lines = all_lines - valid_lines

        # El grupo ya viene resuelto en la propia línea de factura
        # (account.move.line.group_id, snapshot histórico que se fija al
        # timbrar). Antes había que reconstruir la relación
        # buscando grupos por nombre a partir de un Char: eso obligaba a
        # que los nombres fueran únicos —dos grupos homónimos abortaban
        # el cálculo con un error— y dejaba huérfano el histórico en
        # cuanto alguien renombraba un grupo.
        values_list = [
            self._prepare_detailed_line_vals(
                line,
                'invalid' if self._is_manually_excluded(line) else 'valid',
            )
            for line in valid_lines
        ]
        values_list += [
            self._prepare_detailed_line_vals(line, 'invalid')
            for line in invalid_lines
        ]

        if values_list:
            self.env['ztyres_promo.lines'].create(values_list)
        self.invalidate_recordset(['detailed_line_ids'])

    def _is_manually_excluded(self, line):
        return (
            line.partner_id in self.excluded_partner_ids
            or line.move_id in self.excluded_invoice_ids
            or (
                self.generic_edi == 'no'
                and line.edi_vat_receptor == GENERIC_RFC
            )
        )

    def _prepare_detailed_line_vals(self, line, state):
        """Convierte account.move.line al modelo de auditoría."""
        sign = 1 if line.move_id.move_type == 'out_invoice' else -1
        sale_lines = line.sale_line_ids
        receiver_rfc = line.edi_vat_receptor
        group = line.group_id
        return {
            'definitive_nc_id': self.id,
            'rfc': receiver_rfc,
            'missing_partner_vat': not bool(receiver_rfc),
            'group_id': group.id,
            # group_name se guarda como texto plano y NO como related:
            # es el nombre que tenía el grupo cuando se calculó esta NC.
            # Si mañana lo renombran, el detalle auditable debe seguir
            # diciendo con qué nombre se pagó.
            'group_name': group.name or False,
            'move_type': line.move_id.move_type,
            'move_id': line.move_id.id,
            'product_id': line.product_id.product_tmpl_id.id,
            'product_name': line.product_id.name,
            'name': line.name,
            'product_code': line.product_id.default_code,
            'product_brand': line.product_id.brand_id.name or '',
            'date': line.move_id.invoice_date,
            'quantity': sign * line.quantity,
            'price_subtotal': sign * line.price_subtotal,
            'partner_id': line.partner_id.id,
            'sale_origin': ', '.join(sale_lines.mapped('order_id.name')),
            'list_origin': sale_lines[:1].list_origin if sale_lines else '',
            'state': state,
        }

    def _update_missing_partner_vat_warning(self):
        """Guarda una alerta persistente sin revertir el cálculo."""
        self.ensure_one()
        missing_lines = self.detailed_line_ids.filtered('missing_partner_vat')
        documents = missing_lines.mapped('move_id')
        if not documents:
            self.missing_partner_vat_warning = False
            return

        document_names = documents.mapped('display_name')
        visible_names = document_names[:50]
        remaining = len(document_names) - len(visible_names)
        message = (
            'No se puede confirmar la promoción porque %d documento(s) '
            'tienen líneas sin RFC receptor: %s'
        ) % (len(documents), ', '.join(visible_names))
        message += (
            ' y %d documento(s) más.' % remaining if remaining else '.'
        )
        message += (
            ' Corrija el RFC fiscal del cliente o la configuración genérica '
            'del documento y vuelva a calcular.'
        )
        self.missing_partner_vat_warning = message

    def _missing_partner_vat_notification(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Cálculo finalizado con alerta',
                'message': self.missing_partner_vat_warning,
                'type': 'danger',
                'sticky': True,
            },
        }

    # ==================================================================
    # Agrupaciones reutilizables
    # ==================================================================
    def _valid_detailed_lines(self):
        self.ensure_one()
        return self.detailed_line_ids.filtered(
            lambda line: line.state in ('valid', 'partial')
        )

    def _lines_by_partner(self, lines):
        """dict {partner: recordset} en una sola pasada."""
        ids_by_partner = defaultdict(list)
        for line in lines:
            ids_by_partner[line.partner_id.id].append(line.id)
        model = self.env['ztyres_promo.lines']
        return {
            self.env['res.partner'].browse(partner_id): model.browse(line_ids)
            for partner_id, line_ids in ids_by_partner.items()
        }

    def _lines_by_receiver(self, lines):
        """dict {rfc: recordset} dentro de un mismo cliente."""
        ids_by_rfc = defaultdict(list)
        for line in lines:
            ids_by_rfc[line.rfc or ''].append(line.id)
        model = self.env['ztyres_promo.lines']
        return {
            rfc: model.browse(line_ids)
            for rfc, line_ids in sorted(ids_by_rfc.items())
        }

    # ==================================================================
    # Resultados por cliente y RFC
    # ==================================================================
    def _create_result_lines(self):
        self.ensure_one()
        coupon_amount_by_line = self._apply_coupon_limits()
        global_quantity_by_partner = self._global_quantity_by_partner()
        values_list = []

        for partner, partner_lines in self._lines_by_partner(
            self._valid_detailed_lines()
        ).items():
            reward_percent, reward_fixed = self._get_partner_tier_reward(
                partner,
                partner_lines,
                global_quantity_by_partner,
            )
            accumulated_quantity = sum(partner_lines.mapped('quantity'))
            tier_value = self._tier_value(
                partner,
                partner_lines,
                global_quantity_by_partner,
            )
            tier = self._matching_tier(
                partner,
                partner_lines,
                global_quantity_by_partner,
            )
            receivers = self._lines_by_receiver(partner_lines)
            fixed_by_receiver = self._allocate_fixed_amount(
                receivers,
                reward_fixed,
            )
            for rfc, receiver_lines in receivers.items():
                values_list.append(self._prepare_result_vals(
                    partner=partner,
                    # Nunca sustituir un RFC faltante por el VAT fiscal
                    # del partner: cada resultado representa exactamente
                    # el receptor que traían sus CFDI.
                    rfc=rfc,
                    lines=receiver_lines,
                    accumulated_quantity=accumulated_quantity,
                    reward_percent=reward_percent,
                    reward_fixed_amount=fixed_by_receiver.get(rfc, 0.0),
                    tier_value=tier_value,
                    tier=tier,
                    coupon_amount=sum(
                        coupon_amount_by_line.get(line.id, 0.0)
                        for line in receiver_lines
                    ),
                ))

        if values_list:
            self.env['ztyres_promo.notas_credito_lines'].create(values_list)
        self.invalidate_recordset(['line_ids'])

    def _prepare_result_vals(
        self,
        partner,
        rfc,
        lines,
        accumulated_quantity,
        reward_percent,
        reward_fixed_amount,
        tier_value=0.0,
        tier=None,
        coupon_amount=0.0,
    ):
        subtotal = sum(lines.mapped('price_subtotal'))
        reward_type = self._effective_reward_type()
        reward_detail = ''
        total = 0.0

        if self._is_coupon_promotion():
            total = coupon_amount
            reward_percent = (
                coupon_amount * 100 / subtotal if subtotal > 0 else 0.0
            )
            reward_detail = 'Cupones: tope %d pza por producto' % (
                self.coupon_limit_qty or DEFAULT_COUPON_LIMIT_QTY
            )
        elif self._is_rim_quantity_promotion():
            total, _by_line, breakdown = self._engine.rim_amounts(
                self.rim_policy_line_ids,
                lines,
                accumulated_quantity,
            )
            reward_percent = total * 100 / subtotal if subtotal > 0 else 0.0
            reward_detail = self._engine.format_rim_breakdown(
                breakdown,
                accumulated_quantity,
            )
        elif self._has_key_sizes():
            # El tramo ya se eligió con el acumulado completo (los Key
            # Sizes incluidos); aquí solo cambia el porcentaje con que
            # cobra cada producto.
            total, _by_line, breakdown = self._engine.key_size_amounts(
                self.key_size_product_ids,
                tier,
                lines,
                reward_percent,
            )
            reward_percent = total * 100 / subtotal if subtotal > 0 else 0.0
            reward_detail = self._engine.format_key_size_breakdown(
                breakdown,
                tier_value,
                self._uses_amount_policy(),
            )
        elif reward_type == REWARD_FIXED_AMOUNT:
            total = reward_fixed_amount
            reward_detail = 'Monto fijo del nivel alcanzado'
        else:
            total = subtotal * reward_percent / 100
            reward_detail = 'Porcentaje del nivel alcanzado: %.2f%%' % (
                reward_percent
            )

        return {
            'definitive_nc_id': self.id,
            'partner_id': partner.id,
            'group_id': lines[:1].group_id.id,
            'group_name': lines[:1].group_name or False,
            'price_subtotal': subtotal,
            'quantity': sum(lines.mapped('quantity')),
            'rfc': rfc,
            'reward_type': reward_type,
            'reward_percent': reward_percent,
            'reward_fixed_amount': (
                reward_fixed_amount if reward_type == REWARD_FIXED_AMOUNT else 0.0
            ),
            'reward_detail': reward_detail,
            'total_nc_untaxed': total,
        }

    def _global_quantity_by_partner(self):
        """Cantidad facturada por cliente, participe o no en la promoción.

        Se calcula una sola vez: antes se recorría todo el detalle dentro
        del ciclo por cliente.
        """
        self.ensure_one()
        if self.apply_volume != 'si':
            return {}
        quantity_by_partner = defaultdict(float)
        for line in self.detailed_line_ids:
            quantity_by_partner[line.partner_id.id] += line.quantity
        return quantity_by_partner

    def _tier_value(self, partner, partner_lines, global_quantity_by_partner=None):
        """Acumulado con el que se elige el tramo, según la política.

        Vive en un solo lugar porque ahora lo leen dos consumidores: la
        selección del tramo y la tabla de Key Sizes. Si cada uno lo
        calculara por su cuenta, un cliente podría caer en un tramo con
        la tabla general y en otro con la de Key Sizes.
        """
        self.ensure_one()
        policy = self._get_policy()
        global_quantity_by_partner = global_quantity_by_partner or {}

        if policy == POLICY_QUANTITY:
            # 'Aplicar por cantidad global': el tramo se elige con todo lo
            # facturado al cliente, participe o no en la promoción.
            if self.apply_volume == 'si':
                return global_quantity_by_partner.get(partner.id, 0.0)
            return sum(partner_lines.mapped('quantity'))

        if policy == POLICY_AMOUNT:
            return sum(partner_lines.mapped('price_subtotal'))

        return 0.0

    def _matching_tier(self, partner, partner_lines, global_quantity_by_partner=None):
        """Nivel alcanzado, como registro.

        `_get_partner_tier_reward` devuelve solo el porcentaje, y los Key
        Sizes necesitan además la columna "% Key Sizes" de ese mismo
        nivel. Se resuelve aquí con el mismo acumulado para que no haya
        forma de que uno lea un nivel y el otro lea otro.
        """
        self.ensure_one()
        policy = self._get_policy()
        if policy not in TIER_POLICIES:
            return self._active_policy_lines().browse()
        value = self._tier_value(
            partner,
            partner_lines,
            global_quantity_by_partner,
        )
        # En política por Cantidad el acumulado ES la cantidad, igual que
        # en `_get_partner_tier_reward`: si aquí se pasara otra, el
        # requisito `min_qty` podría descartar un nivel que allá sí
        # aplicó.
        quantity = (
            value
            if policy == POLICY_QUANTITY
            else sum(partner_lines.mapped('quantity'))
        )
        return self._engine.matching_tier(
            self._active_policy_lines(),
            value,
            quantity=quantity,
        )

    def _get_partner_tier_reward(
        self,
        partner,
        partner_lines,
        global_quantity_by_partner=None,
    ):
        """Beneficio por tramos para un cliente. Rin y cupones no usan esto."""
        self.ensure_one()
        policy = self._get_policy()

        if policy == POLICY_QUANTITY:
            quantity = self._tier_value(
                partner,
                partner_lines,
                global_quantity_by_partner,
            )
            return self._engine.tier_reward(
                self.policy_line_qty_ids,
                quantity,
                self._effective_reward_type(),
                quantity=quantity,
            )

        if policy == POLICY_AMOUNT:
            return self._engine.tier_reward(
                self.policy_line_amount_ids,
                self._tier_value(partner, partner_lines),
                self._effective_reward_type(),
                quantity=sum(partner_lines.mapped('quantity')),
            )

        if policy == POLICY_MONTHLY_VOLUME:
            return (
                self._engine.monthly_volume_discount(
                    self.monthly_volume_line_ids,
                    partner_lines,
                ),
                0.0,
            )

        return 0.0, 0.0

    def _allocate_fixed_amount(self, lines_by_key, fixed_amount):
        """Reparte un premio fijo sin duplicarlo entre RFC receptores."""
        if (
            self._effective_reward_type() != REWARD_FIXED_AMOUNT
            or not fixed_amount
        ):
            return {key: 0.0 for key in lines_by_key}
        if len(lines_by_key) == 1:
            return {key: fixed_amount for key in lines_by_key}

        subtotals = {
            key: sum(lines.mapped('price_subtotal'))
            for key, lines in lines_by_key.items()
        }
        positive_keys = [key for key, value in subtotals.items() if value > 0]
        total_subtotal = sum(subtotals[key] for key in positive_keys)
        allocations = {key: 0.0 for key in lines_by_key}
        if not positive_keys or not total_subtotal:
            return allocations

        remaining = fixed_amount
        for key in positive_keys[:-1]:
            allocated = round(
                fixed_amount * subtotals[key] / total_subtotal,
                2,
            )
            allocations[key] = allocated
            remaining -= allocated
        allocations[positive_keys[-1]] = round(remaining, 2)
        return allocations

    # ==================================================================
    # Cupones
    # ==================================================================
    def _apply_coupon_limits(self):
        """Aplica el tope por producto UNA vez por cliente.

        Antes el tope se evaluaba dentro del armado de cada resultado, o
        sea una vez por RFC receptor: un cliente con ventas fiscales y de
        mostrador recibía el doble de piezas bonificadas.
        """
        self.ensure_one()
        if not self._is_coupon_promotion():
            return {}

        limit = self.coupon_limit_qty or DEFAULT_COUPON_LIMIT_QTY
        amount_by_line = {}
        states_by_value = defaultdict(list)

        for _partner, partner_lines in self._lines_by_partner(
            self._valid_detailed_lines()
        ).items():
            _total, amounts, states = self._engine.coupon_amounts(
                self.coupon_ids,
                partner_lines,
                limit,
            )
            amount_by_line.update(amounts)
            for line_id, state in states.items():
                states_by_value[state].append(line_id)

        model = self.env['ztyres_promo.lines']
        for state, line_ids in states_by_value.items():
            model.browse(line_ids).write({'state': state})
        self.invalidate_recordset(['detailed_line_ids'])
        return amount_by_line

    # ==================================================================
    # Beneficio por grupo de clientes
    # ==================================================================
    def _apply_group_rewards(self):
        self.ensure_one()
        if self.apply_on_groups != 'si' or self._is_coupon_promotion():
            return

        if self._is_rim_quantity_promotion():
            self._apply_rim_group_rewards()
            return

        if self._get_policy() == POLICY_MONTHLY_VOLUME:
            self._apply_monthly_volume_group_rewards()
            return

        if self._get_policy() in TIER_POLICIES:
            self._apply_tier_group_rewards()

    def _group_records(self):
        """Grupos presentes en el resultado, como registros.

        La clave de agrupación pasó de ser el NOMBRE del grupo a ser el
        propio registro. Con nombres, dos grupos homónimos se fundían en
        uno solo y repartían mal la nota de crédito; era tan peligroso
        que el código anterior prefería abortar el cálculo con un error
        antes que arriesgarse. Con registros el problema desaparece: los
        nombres pueden repetirse sin consecuencias.
        """
        return self.line_ids.mapped('group_id')

    def _group_lines_for_result(self, group_lines, result_line):
        """Compras del mismo partner y del mismo receptor fiscal.

        El grupo comparte únicamente el acumulado usado para alcanzar el
        tramo. La base sobre la que se paga cada NC nunca se comparte:
        permanece separada por ``partner_id + rfc``. Esto impide usar las
        ventas XAXX010101000 para aumentar una NC fiscal, o viceversa.
        """
        return group_lines.filtered(
            lambda line: (
                line.partner_id == result_line.partner_id
                and line.rfc == result_line.rfc
            )
        )

    def _apply_rim_group_rewards(self):
        """El grupo comparte el acumulado; cada rin conserva su porcentaje."""
        for group in self._group_records():
            group_lines = self._valid_detailed_lines().filtered(
                lambda line, grp=group: line.group_id == grp
            )
            accumulated_quantity = sum(group_lines.mapped('quantity'))

            for result_line in self.line_ids.filtered(
                lambda line, grp=group: line.group_id == grp
            ):
                # Por (cliente, RFC): filtrar solo por RFC mezclaba a dos
                # clientes distintos del mismo grupo que comparten el RFC
                # genérico de mostrador y duplicaba su NC.
                bucket = self._group_lines_for_result(
                    group_lines,
                    result_line,
                )
                amount, _by_line, breakdown = self._engine.rim_amounts(
                    self.rim_policy_line_ids,
                    bucket,
                    accumulated_quantity,
                )
                result_line.write({
                    'reward_type': REWARD_PERCENTAGE,
                    'reward_percent': (
                        amount * 100 / result_line.price_subtotal
                        if result_line.price_subtotal > 0
                        else 0.0
                    ),
                    # El monto manda: `reward_percent` solo se muestra.
                    'total_nc_untaxed': amount,
                    'reward_fixed_amount': 0.0,
                    'reward_detail': 'Grupo %s | %s' % (
                        group.name or group.display_name,
                        self._engine.format_rim_breakdown(
                            breakdown,
                            accumulated_quantity,
                        ),
                    ),
                })

    def _apply_monthly_volume_group_rewards(self):
        for group in self._group_records():
            group_lines = self._valid_detailed_lines().filtered(
                lambda line, grp=group: line.group_id == grp
            )
            discount = self._engine.monthly_volume_discount(
                self.monthly_volume_line_ids,
                group_lines,
            )
            self.line_ids.filtered(
                lambda line, grp=group: line.group_id == grp
            ).write({
                'reward_type': REWARD_PERCENTAGE,
                'reward_percent': discount,
                'reward_fixed_amount': 0.0,
                'reward_detail': 'Volumen mensual del grupo %s: %.2f%%' % (
                    group.name or group.display_name,
                    discount,
                ),
            })

    def _apply_tier_group_rewards(self):
        """Tramo elegido con el acumulado del grupo, no del cliente."""
        grouped_data = (
            self.get_grouped_data_volume()
            if self.apply_volume == 'si'
            else self.get_grouped_data(self._get_policy())
        )
        policies = self._active_policy_lines()
        reward_type = self._effective_reward_type()

        for group, value in grouped_data:
            result_lines = self.line_ids.filtered(
                lambda line, grp=group: line.group_id == grp
            )
            if not result_lines:
                continue
            quantity = sum(result_lines.mapped('quantity'))
            reward_percent, reward_fixed = self._engine.tier_reward(
                policies,
                value,
                reward_type,
                quantity=quantity,
            )
            if reward_type == REWARD_FIXED_AMOUNT:
                self._allocate_group_fixed_amount(result_lines, reward_fixed)
                continue
            if self._has_key_sizes():
                self._apply_key_size_group_rewards(
                    group,
                    result_lines,
                    value,
                    reward_percent,
                    self._engine.matching_tier(policies, value, quantity),
                )
                continue
            result_lines.write({
                'reward_type': REWARD_PERCENTAGE,
                'reward_percent': reward_percent,
                'reward_fixed_amount': 0.0,
                'reward_detail': 'Grupo %s: acumulado %s, %.2f%%' % (
                    group.name or group.display_name,
                    round(value, 2),
                    reward_percent,
                ),
            })

    def _apply_key_size_group_rewards(
        self,
        group,
        result_lines,
        tier_value,
        base_discount,
        tier,
    ):
        """El grupo comparte el tramo; cada Key Size conserva su porcentaje."""
        group_lines = self._valid_detailed_lines().filtered(
            lambda line, grp=group: line.group_id == grp
        )
        for result_line in result_lines:
            # Por (cliente, RFC), igual que en la política por rin: filtrar
            # solo por RFC mezcla a dos clientes del mismo grupo que
            # comparten el RFC genérico de mostrador.
            bucket = self._group_lines_for_result(
                group_lines,
                result_line,
            )
            amount, _by_line, breakdown = self._engine.key_size_amounts(
                self.key_size_product_ids,
                tier,
                bucket,
                base_discount,
            )
            result_line.write({
                'reward_type': REWARD_PERCENTAGE,
                'reward_percent': (
                    amount * 100 / result_line.price_subtotal
                    if result_line.price_subtotal > 0
                    else 0.0
                ),
                # El monto manda: `reward_percent` solo se muestra.
                'total_nc_untaxed': amount,
                'reward_fixed_amount': 0.0,
                'reward_detail': 'Grupo %s | %s' % (
                    group.name or group.display_name,
                    self._engine.format_key_size_breakdown(
                        breakdown,
                        tier_value,
                        self._uses_amount_policy(),
                    ),
                ),
            })

    def _allocate_group_fixed_amount(self, result_lines, fixed_amount):
        """Distribuye una recompensa grupal sin duplicarla por cliente."""
        result_lines.write({
            'reward_type': REWARD_FIXED_AMOUNT,
            'reward_percent': 0.0,
            'reward_fixed_amount': 0.0,
        })
        positive_lines = result_lines.filtered(
            lambda line: line.price_subtotal > 0
        ).sorted('id')
        total_subtotal = sum(positive_lines.mapped('price_subtotal'))
        if not positive_lines or not fixed_amount or not total_subtotal:
            return

        remaining = fixed_amount
        for line in positive_lines[:-1]:
            allocated = round(
                fixed_amount * line.price_subtotal / total_subtotal,
                2,
            )
            line.write({
                'reward_fixed_amount': allocated,
                'reward_detail': 'Monto fijo del grupo repartido por subtotal',
            })
            remaining -= allocated
        positive_lines[-1].write({
            'reward_fixed_amount': round(remaining, 2),
            'reward_detail': 'Monto fijo del grupo repartido por subtotal',
        })

    # ==================================================================
    # Cierre
    # ==================================================================
    def _recompute_nc_amounts(self):
        """Recalcula el total después de los ajustes por grupo."""
        self.ensure_one()
        if self._is_coupon_promotion():
            return
        if self._is_rim_quantity_promotion() or self._has_key_sizes():
            # El importe por rin / por Key Size ya es la suma exacta de
            # cada renglón. Reconstruirlo desde `reward_percent` lo
            # desviaba: ese campo es informativo y se guarda con 2
            # decimales, así que un efectivo de 3.003797% se leía como
            # 3.00% y la NC salía baja.
            return
        for line in self.line_ids:
            line.total_nc_untaxed = (
                line.reward_fixed_amount
                if line.reward_type == REWARD_FIXED_AMOUNT
                else line.price_subtotal * line.reward_percent / 100
            )
