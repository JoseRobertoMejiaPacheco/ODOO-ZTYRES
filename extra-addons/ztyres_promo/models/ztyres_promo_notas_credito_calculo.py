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
    BASE_PMS,
    DEFAULT_COUPON_LIMIT_QTY,
    POLICY_AMOUNT,
    POLICY_AMOUNT_RIM,
    POLICY_MONTHLY_VOLUME,
    POLICY_QUANTITY,
    REWARD_FIXED_AMOUNT,
    REWARD_GIFT_CARD,
    REWARD_PERCENTAGE,
    TIER_POLICIES,
)

# Se conserva el nombre público por compatibilidad con integraciones
# existentes; el valor real se toma de `coupon_limit_qty`.
COUPON_LIMIT_PER_PRODUCT = DEFAULT_COUPON_LIMIT_QTY
GENERIC_RFC = 'XAXX010101000'
MISSING_XML_RFC = 'SIN XML ADJUNTO'


def _format_percent(value):
    """7.5 -> '7.5%'; 8.0 -> '8%', sin redondear el beneficio."""
    return ('%.1f' % (value or 0.0)).rstrip('0').rstrip('.') + '%'


class ZtyresPromoCreditNoteCalculation(models.Model):
    _inherit = 'ztyres_promo.notas_credito'

    # ==================================================================
    # Punto de entrada
    # ==================================================================
    def action_calcular_nc(self):
        """Recalcula el detalle y el resultado definitivo de la promoción."""
        self.ensure_one()
        self._validate_configuration()
        self._validate_receiver_rfcs()
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
    def _is_invalid_receiver_rfc(self, value):
        """Un CFDI válido debe traer RFC fiscal o el genérico de mostrador."""
        normalized = (value or '').strip().upper()
        return not normalized or normalized == MISSING_XML_RFC

    def _validate_receiver_rfcs(self):
        """Bloquea el cálculo cuando falta el RFC proveniente del XML.

        ``SIN XML ADJUNTO`` es un estado de error, no un RFC receptor. Se
        valida antes de borrar resultados anteriores para que un documento
        defectuoso no deje el cálculo a medias ni se agrupe como si ese texto
        fuera un RFC fiscal.
        """
        self.ensure_one()
        invalid_domain = self._get_domain() + [
            '|',
            ('edi_vat_receptor', '=', False),
            ('edi_vat_receptor', 'ilike', MISSING_XML_RFC),
        ]
        candidates = self.env['account.move.line'].search(invalid_domain)
        invalid_lines = candidates.filtered(
            lambda line: (
                self._is_invalid_receiver_rfc(line.edi_vat_receptor)
                and not self._is_manually_excluded(line)
            )
        )
        documents = invalid_lines.mapped('move_id')
        if not documents:
            return

        names = documents.mapped('display_name')
        visible = names[:50]
        remaining = len(names) - len(visible)
        detail = ', '.join(visible)
        if remaining:
            detail += _(' y %d documento(s) más') % remaining
        raise UserError(_(
            'No se puede calcular la promoción. %d documento(s) tienen '
            'edi_vat_receptor vacío o con el valor "SIN XML ADJUNTO": %s. '
            'Cada documento debe tener el RFC fiscal obtenido del XML o el '
            'RFC genérico XAXX010101000. Adjunte/corrija el XML y vuelva a '
            'calcular.'
        ) % (len(documents), detail))

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

        if self._is_amount_rim_promotion():
            invalid = policies.filtered(lambda p: not p.rim_discount_ids)
            if invalid:
                raise UserError(_(
                    'En "Monto por Rin / Key Sizes", cada tramo de monto debe '
                    'tener al menos un rango de RIN configurado.'
                ))
            if self.key_size_product_ids:
                invalid_key = policies.filtered(
                    lambda p: not 0 < p.key_size_discount <= 100
                )
                if invalid_key:
                    raise UserError(_(
                        'Hay productos Key Size cargados. Capture su porcentaje '
                        'en todos los tramos de monto.'
                    ))
            return

        if self._is_gift_card_promotion():
            # La tarjeta de regalo no captura porcentaje: sin esta salida
            # el cálculo caía en la validación de porcentajes de abajo y
            # abortaba con "todos los porcentajes deben ser mayores que
            # cero" en una promoción perfectamente bien configurada.
            self._validate_gift_card_configuration(policies)
            return

        invalid = policies.filtered(
            lambda policy: not 0 < policy.discount <= 100
        )
        if invalid:
            raise UserError(_(
                'Todos los porcentajes deben ser mayores que cero y no '
                'superar 100. Se permiten decimales, por ejemplo 2.10.'
            ))

        self._validate_pms_configuration()

    def _validate_pms_configuration(self):
        """Impide calcular sobre una base PMS que no existe.

        Es el único descuido del módulo que NO se nota al calcular: sin
        tabla de precios, `_uses_pms_base()` devuelve False y la
        promoción paga sobre el subtotal facturado tan tranquila. El
        resultado se ve razonable, se aprueba, y la diferencia aparece
        cuando la marca reclama. Por eso aquí se detiene el cálculo en
        vez de dejarlo en un aviso amarillo.
        """
        self.ensure_one()
        if self.key_size_base != BASE_PMS:
            return
        if not self.pms_price_ids:
            raise UserError(_(
                'La base de cálculo es "Precio PMS x piezas" pero no hay '
                'ningún precio cargado. Cargue la plantilla (columnas '
                '"codigo" y "pms") en la pestaña Definición de la '
                'promoción, o cambie la base a "Subtotal facturado".'
            ))
        if not any(record.price > 0 for record in self.pms_price_ids):
            raise UserError(_(
                'Todos los precios PMS cargados están en cero: la '
                'promoción no generaría ninguna nota de crédito.'
            ))

    def _validate_gift_card_configuration(self, policies):
        """Lo que impide calcular una tarjeta de regalo con sentido."""
        self.ensure_one()
        if self._gift_card_uses_product_table():
            if not self.gift_card_ids:
                raise UserError(_(
                    'El valor de la tarjeta sale de la plantilla por código, '
                    'pero no hay ningún código cargado. Cargue la plantilla '
                    'en la pestaña "Tarjeta de regalo".'
                ))
            if not any(card.amount > 0 for card in self.gift_card_ids):
                raise UserError(_(
                    'Todos los códigos de la plantilla tienen monto cero: '
                    'la promoción no entregaría ninguna tarjeta.'
                ))
            return

        if not any(
            getattr(policy, 'gift_card_amount', 0.0) > 0
            for policy in policies
        ):
            raise UserError(_(
                'Ningún nivel tiene valor en la columna "Promo ZT". Capture '
                'el valor de la tarjeta en los niveles, o cambie el origen '
                'del valor a la plantilla por código.'
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
            'missing_partner_vat': self._is_invalid_receiver_rfc(receiver_rfc),
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
        """Resguardo para datos antiguos: vacío y SIN XML son inválidos."""
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
            'tienen líneas sin RFC receptor o con "SIN XML ADJUNTO": %s'
        ) % (len(documents), ', '.join(visible_names))
        message += (
            ' y %d documento(s) más.' % remaining if remaining else '.'
        )
        message += (
            ' Adjunte/corrija el XML para obtener el RFC fiscal, o asigne '
            'el RFC genérico XAXX010101000, y vuelva a calcular.'
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
            accumulated_quantity = (
                global_quantity_by_partner.get(partner.id, 0.0)
                if (
                    self._is_rim_quantity_promotion()
                    and self.apply_volume == 'si'
                )
                else sum(partner_lines.mapped('quantity'))
            )
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
            gift_card_by_receiver = self._allocate_gift_card_amount(
                receivers,
                tier,
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
                    gift_card_amount=gift_card_by_receiver.get(rfc, 0.0),
                ))

        if values_list:
            self.env['ztyres_promo.notas_credito_lines'].create(values_list)
        self.invalidate_recordset(['line_ids'])

    def _effective_percent(self, amount, subtotal):
        """NC ÷ subtotal, el porcentaje que se MUESTRA en el resumen.

        Nunca se usa para reconstruir el importe: se guarda con pocos
        decimales y multiplicar por él perdería pesos. Vive en un método
        propio porque la división por cero estaba escrita tres veces con
        tres criterios (`> 0`, truthy, sin comprobar) y una NC negativa
        —las devoluciones existen— tiene subtotal negativo, no cero.
        """
        self.ensure_one()
        if not subtotal:
            return 0.0
        return (amount or 0.0) * 100.0 / subtotal

    def _result_quantity(self, lines):
        """Piezas del resultado, redondeadas antes de tocar un Integer.

        `quantity` es un campo Integer y la suma de las líneas es un
        float: al escribir 274.99999999 Odoo guarda 274. Un cliente con
        275 llantas aparecía con 274 en el resumen mientras el tramo se
        había elegido, correctamente, con 275.
        """
        return int(round(sum(lines.mapped('quantity'))))

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
        gift_card_amount=0.0,
    ):
        subtotal = sum(lines.mapped('price_subtotal'))
        reward_type = self._effective_reward_type()
        reward_detail = ''
        total = 0.0

        if self._is_gift_card_promotion():
            # El importe de NC de una tarjeta es cero salvo que se haya
            # pedido explícitamente emitirla. Cuando sí se emite, el
            # valor capturado (con IVA) se baja a subtotal: el timbrado
            # vuelve a sumar el IVA y si no, el cliente recibiría 1.16
            # veces la tarjeta prometida.
            total = (
                self._engine.untaxed(gift_card_amount)
                if self._gift_card_generates_nc()
                else 0.0
            )
            return {
                'definitive_nc_id': self.id,
                'partner_id': partner.id,
                'group_id': lines[:1].group_id.id,
                'group_name': lines[:1].group_name or False,
                'price_subtotal': subtotal,
                'quantity': self._result_quantity(lines),
                'rfc': rfc,
                'reward_type': reward_type,
                'reward_percent': 0.0,
                'reward_fixed_amount': 0.0,
                'reward_detail': self._describe_gift_card_result(
                    tier,
                    tier_value,
                    gift_card_amount,
                ),
                'gift_card_amount': gift_card_amount,
                'total_nc_untaxed': total,
            }

        if self._is_coupon_promotion():
            total = coupon_amount
            reward_percent = self._effective_percent(coupon_amount, subtotal)
            reward_detail = 'Cupones: tope %d pza por producto' % (
                self.coupon_limit_qty or DEFAULT_COUPON_LIMIT_QTY
            )
        elif self._is_rim_quantity_promotion():
            total, _by_line, breakdown = self._engine.rim_amounts(
                self.rim_policy_line_ids,
                lines,
                accumulated_quantity,
            )
            reward_percent = self._effective_percent(total, subtotal)
            reward_detail = self._engine.format_rim_breakdown(
                breakdown,
                accumulated_quantity,
            )
        elif self._is_amount_rim_promotion():
            total, _by_line, breakdown = self._engine.amount_rim_amounts(
                self.key_size_product_ids,
                tier,
                lines,
                unit_base_by_line=self._key_size_unit_by_line(lines),
                unit_base_tax_factor=self._pms_tax_factor(),
            )
            reward_percent = self._effective_percent(total, subtotal)
            reward_detail = self._engine.format_key_size_breakdown(
                breakdown,
                tier_value,
                True,
            )
        elif self._uses_key_size_engine():
            # El tramo ya se eligió con el acumulado completo (los Key
            # Sizes incluidos); aquí solo cambia el porcentaje con que
            # cobra cada producto y, si la promoción es de precios PMS,
            # la base sobre la que se aplica.
            total, _by_line, breakdown = self._engine.key_size_amounts(
                self.key_size_product_ids,
                tier,
                lines,
                reward_percent,
                unit_base_by_line=self._key_size_unit_by_line(lines),
                unit_base_tax_factor=self._pms_tax_factor(),
            )
            reward_percent = self._effective_percent(total, subtotal)
            reward_detail = self._engine.format_key_size_breakdown(
                breakdown,
                tier_value,
                self._uses_amount_policy(),
                base_label=self._pms_base_label(),
            )
        elif reward_type == REWARD_FIXED_AMOUNT:
            total = reward_fixed_amount
            reward_detail = 'Monto fijo del nivel alcanzado'
        else:
            total = self._engine.percent_amount(subtotal, reward_percent)
            reward_detail = 'Porcentaje del nivel alcanzado: %s' % (
                _format_percent(reward_percent)
            )

        return {
            'definitive_nc_id': self.id,
            'partner_id': partner.id,
            'group_id': lines[:1].group_id.id,
            'group_name': lines[:1].group_name or False,
            'price_subtotal': subtotal,
            'quantity': self._result_quantity(lines),
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

        if policy in (POLICY_AMOUNT, POLICY_AMOUNT_RIM):
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

        if policy == POLICY_AMOUNT_RIM:
            # El porcentaje se decide por línea después de elegir el tramo.
            return 0.0, 0.0

        if policy == POLICY_MONTHLY_VOLUME:
            total_quantity = (
                global_quantity_by_partner.get(partner.id, 0.0)
                if self.apply_volume == 'si'
                else None
            )
            return (
                self._engine.monthly_volume_discount(
                    self.monthly_volume_line_ids,
                    partner_lines,
                    total_quantity=total_quantity,
                ),
                0.0,
            )

        return 0.0, 0.0

    def _allocate_gift_card_amount(self, lines_by_key, tier):
        """Valor de tarjeta que le toca a cada RFC receptor del cliente.

        Con la plantilla por código no hay nada que repartir: cada
        receptor paga por las piezas que él compró.

        Con valor fijo por nivel sí lo hay, y es la misma trampa del
        monto fijo: un cliente que factura con RFC fiscal y de mostrador
        genera dos renglones de resultado, y entregar el valor completo
        en cada uno duplica la tarjeta. Se reparte proporcional al
        subtotal, igual que el monto fijo.
        """
        self.ensure_one()
        empty = {key: 0.0 for key in lines_by_key}
        if not self._is_gift_card_promotion() or not tier:
            return empty

        if self._gift_card_uses_product_table():
            return {
                key: self._gift_card_amount_for_lines(lines)[0]
                for key, lines in lines_by_key.items()
            }

        tier_amount = getattr(tier, 'gift_card_amount', 0.0) or 0.0
        if not tier_amount:
            return empty
        return self._split_amount_by_subtotal(lines_by_key, tier_amount)

    def _describe_gift_card_result(self, tier, tier_value, gift_card_amount):
        """Texto auditable: por qué salió ese valor de tarjeta."""
        self.ensure_one()
        if not tier:
            return 'No alcanzó ningún nivel: sin tarjeta.'

        acumulado = (
            '$%s' % format(tier_value, ',.2f')
            if self._uses_amount_policy()
            else '%s pza' % self._engine.format_quantity(tier_value)
        )
        if self._gift_card_uses_product_table():
            origen = 'monto por pieza de la plantilla Promo ZT'
        else:
            origen = 'valor fijo del nivel alcanzado'
        entrega = (
            'se emite NC por ese valor'
            if self._gift_card_generates_nc()
            else 'sin NC: la tarjeta se entrega por fuera'
        )
        return 'Acumulado %s | Tarjeta $%s (%s) | %s' % (
            acumulado,
            format(gift_card_amount, ',.2f'),
            origen,
            entrega,
        )

    def _allocate_fixed_amount(self, lines_by_key, fixed_amount):
        """Reparte un premio fijo sin duplicarlo entre RFC receptores."""
        if (
            self._effective_reward_type() != REWARD_FIXED_AMOUNT
            or not fixed_amount
        ):
            return {key: 0.0 for key in lines_by_key}
        return self._split_amount_by_subtotal(lines_by_key, fixed_amount)

    def _split_amount_by_subtotal(self, lines_by_key, amount):
        """Reparte un importe entre receptores, proporcional al subtotal.

        El último receptor se lleva el residuo en vez de su proporción
        redondeada, para que la suma de las partes dé exactamente el
        importe original y no un centavo de más o de menos.
        """
        if len(lines_by_key) == 1:
            return {key: amount for key in lines_by_key}

        subtotals = {
            key: sum(lines.mapped('price_subtotal'))
            for key, lines in lines_by_key.items()
        }
        positive_keys = [key for key, value in subtotals.items() if value > 0]
        total_subtotal = sum(subtotals[key] for key in positive_keys)
        allocations = {key: 0.0 for key in lines_by_key}
        if not positive_keys or not total_subtotal:
            return allocations

        remaining = amount
        for key in positive_keys[:-1]:
            allocated = round(
                amount * subtotals[key] / total_subtotal,
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
            accumulated_quantity = (
                sum(
                    self.detailed_line_ids.filtered(
                        lambda line, grp=group: line.group_id == grp
                    ).mapped('quantity')
                )
                if self.apply_volume == 'si'
                else sum(group_lines.mapped('quantity'))
            )

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
                    'reward_percent': self._effective_percent(
                        amount,
                        result_line.price_subtotal,
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
            total_quantity = None
            if self.apply_volume == 'si':
                # El acumulado global incluye también las líneas que no
                # participan. Las condiciones por medida y la base de la NC
                # siguen saliendo de ``group_lines`` (solo líneas válidas).
                total_quantity = sum(
                    self.detailed_line_ids.filtered(
                        lambda line, grp=group: line.group_id == grp
                    ).mapped('quantity')
                )
            discount = self._engine.monthly_volume_discount(
                self.monthly_volume_line_ids,
                group_lines,
                total_quantity=total_quantity,
            )
            result_lines = self.line_ids.filtered(
                lambda line, grp=group: line.group_id == grp
            )
            result_lines.write({
                'reward_type': REWARD_PERCENTAGE,
                'reward_percent': discount,
                'reward_fixed_amount': 0.0,
                'reward_detail': 'Volumen mensual del grupo %s: %s' % (
                    group.name or group.display_name,
                    _format_percent(discount),
                ),
            })
            for result_line in result_lines:
                result_line.total_nc_untaxed = self._engine.percent_amount(
                    result_line.price_subtotal,
                    discount,
                )

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
            if self._is_amount_rim_promotion():
                tier = self._engine.matching_tier(
                    policies, value, quantity=quantity
                )
                group_lines = self._valid_detailed_lines().filtered(
                    lambda line, grp=group: line.group_id == grp
                )
                for result_line in result_lines:
                    bucket = self._group_lines_for_result(group_lines, result_line)
                    amount, _by_line, breakdown = self._engine.amount_rim_amounts(
                        self.key_size_product_ids,
                        tier,
                        bucket,
                        unit_base_by_line=self._key_size_unit_by_line(bucket),
                        unit_base_tax_factor=self._pms_tax_factor(),
                    )
                    result_line.write({
                        'reward_type': REWARD_PERCENTAGE,
                        'reward_percent': self._effective_percent(
                            amount, result_line.price_subtotal
                        ),
                        'reward_fixed_amount': 0.0,
                        'total_nc_untaxed': amount,
                        'reward_detail': 'Grupo %s | %s' % (
                            group.name or group.display_name,
                            self._engine.format_key_size_breakdown(
                                breakdown, value, True
                            ),
                        ),
                    })
                continue
            reward_percent, reward_fixed = self._engine.tier_reward(
                policies,
                value,
                reward_type,
                quantity=quantity,
            )
            if reward_type == REWARD_GIFT_CARD:
                # El tramo se abre con el acumulado del grupo, pero la
                # tarjeta se paga con las piezas de cada quien: el grupo
                # ayuda a calificar, no a cobrar dos veces.
                self._apply_gift_card_group_rewards(
                    group,
                    result_lines,
                    value,
                    policies,
                )
                continue
            if reward_type == REWARD_FIXED_AMOUNT:
                self._allocate_group_fixed_amount(result_lines, reward_fixed)
                continue
            if self._uses_key_size_engine():
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
                'reward_detail': 'Grupo %s: acumulado %s, %s' % (
                    group.name or group.display_name,
                    round(value, 2),
                    _format_percent(reward_percent),
                ),
            })
            # El importe se escribe AQUÍ, no en un recálculo posterior.
            # Antes esta rama solo dejaba el porcentaje y confiaba en que
            # `_recompute_nc_amounts()` reconstruyera el total; ese
            # recálculo leía `reward_percent` ya redondeado y perdía
            # dinero. Ahora cada rama es responsable de su propio
            # importe y ninguna reconstrucción puede desviarlo.
            for result_line in result_lines:
                result_line.total_nc_untaxed = self._engine.percent_amount(
                    result_line.price_subtotal,
                    reward_percent,
                )

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
                unit_base_by_line=self._key_size_unit_by_line(bucket),
                unit_base_tax_factor=self._pms_tax_factor(),
            )
            result_line.write({
                'reward_type': REWARD_PERCENTAGE,
                'reward_percent': self._effective_percent(
                    amount,
                    result_line.price_subtotal,
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
                        base_label=self._pms_base_label(),
                    ),
                ),
            })

    def _apply_gift_card_group_rewards(
        self,
        group,
        result_lines,
        tier_value,
        policies,
    ):
        """Reescribe la tarjeta de cada resultado con el tramo del grupo."""
        self.ensure_one()
        group_name = group.name or group.display_name
        quantity = sum(result_lines.mapped('quantity'))
        tier = self._engine.matching_tier(policies, tier_value, quantity)

        if not tier:
            result_lines.write({
                'reward_type': REWARD_GIFT_CARD,
                'reward_percent': 0.0,
                'reward_fixed_amount': 0.0,
                'gift_card_amount': 0.0,
                'total_nc_untaxed': 0.0,
                'reward_detail': (
                    'Grupo %s: el acumulado del grupo no alcanza ningún '
                    'nivel, sin tarjeta.' % group_name
                ),
            })
            return

        if self._gift_card_uses_product_table():
            group_lines = self._valid_detailed_lines().filtered(
                lambda line, grp=group: line.group_id == grp
            )
            amounts = {
                result_line.id: self._gift_card_amount_for_lines(
                    self._group_lines_for_result(group_lines, result_line)
                )[0]
                for result_line in result_lines
            }
        else:
            tier_amount = getattr(tier, 'gift_card_amount', 0.0) or 0.0
            lines_by_result = {
                result_line.id: result_line for result_line in result_lines
            }
            amounts = self._split_amount_by_subtotal(
                lines_by_result,
                tier_amount,
            )

        for result_line in result_lines:
            amount = amounts.get(result_line.id, 0.0)
            result_line.write({
                'reward_type': REWARD_GIFT_CARD,
                'reward_percent': 0.0,
                'reward_fixed_amount': 0.0,
                'gift_card_amount': amount,
                'total_nc_untaxed': (
                    self._engine.untaxed(amount)
                    if self._gift_card_generates_nc()
                    else 0.0
                ),
                'reward_detail': 'Grupo %s | %s' % (
                    group_name,
                    self._describe_gift_card_result(tier, tier_value, amount),
                ),
            })

    def _allocate_group_fixed_amount(self, result_lines, fixed_amount):
        """Distribuye una recompensa grupal sin duplicarla por cliente."""
        result_lines.write({
            'reward_type': REWARD_FIXED_AMOUNT,
            'reward_percent': 0.0,
            'reward_fixed_amount': 0.0,
            'total_nc_untaxed': 0.0,
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
                # El monto fijo ES el importe de la NC: se escribe aquí
                # y no se reconstruye después.
                'total_nc_untaxed': allocated,
                'reward_detail': 'Monto fijo del grupo repartido por subtotal',
            })
            remaining -= allocated
        positive_lines[-1].write({
            'reward_fixed_amount': round(remaining, 2),
            'total_nc_untaxed': round(remaining, 2),
            'reward_detail': 'Monto fijo del grupo repartido por subtotal',
        })

    # ==================================================================
    # Cierre
    # ==================================================================
    def _recompute_nc_amounts(self):
        """Ya no reconstruye nada. Se conserva por compatibilidad.

        ESTE MÉTODO ERA EL BUG. Recorría los resultados y rehacía el
        importe con

            total_nc_untaxed = price_subtotal * reward_percent / 100

        leyendo `reward_percent` DEL CAMPO, o sea ya redondeado. Con un
        efectivo real de 4.6540192625%, el campo guardaba 4.65 y sobre
        un subtotal de $1,337,501.34 la nota de crédito salía en
        $62,193.81 en vez de $62,247.57: **$53.76 menos**, por cliente.
        Subir el campo a cuatro decimales lo dejaba en $62,247.31, que
        sigue sin ser el importe correcto.

        No hay número de decimales que arregle esto, porque el importe
        correcto NO es una multiplicación: es la suma de los renglones,
        cada uno con su porcentaje y su base. Cualquier reconstrucción a
        partir de un porcentaje guardado vuelve a perder dinero.

        Había excepciones (`if rim or key_sizes: return`) que protegían
        justo los casos que calculan renglón por renglón, pero eran una
        lista que había que acordarse de ampliar: la base PMS tuvo que
        agregarse a mano, y la promoción por grupo con porcentaje plano
        nunca estuvo protegida porque su rama solo escribía el
        porcentaje y dependía de este recálculo.

        Ahora cada rama escribe su propio importe en el momento de
        calcularlo —`_prepare_result_vals` al crear el resultado, y cada
        `_apply_*_group_rewards` al reasignarlo por grupo— así que no
        queda nada que reconstruir. `reward_percent` pasó a ser lo que
        siempre debió ser: un dato informativo que nadie multiplica.
        """
        return True
