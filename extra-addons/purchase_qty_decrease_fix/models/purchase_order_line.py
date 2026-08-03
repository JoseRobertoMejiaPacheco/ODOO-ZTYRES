# -*- coding: utf-8 -*-
import logging

from odoo import models
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # ------------------------------------------------------------------
    # Utilidades de lectura de movimientos
    # ------------------------------------------------------------------
    def _get_pending_move_chain(self):
        """Devuelve TODOS los stock.move ligados a esta línea de compra que
        aún no están 'done' ni 'cancel', siguiendo la cadena de movimientos
        encadenados (push/pull) hasta el final (move_dest_ids).

        Solo se consideran los movimientos de ESTA línea/producto, nunca los
        de otros productos que compartan el mismo picking.

        IMPORTANTE: se excluyen los movimientos que ya tengan cantidad
        avanzada/hecha (quantity_done > 0), aunque su estado todavía no sea
        'done'. Cancelarlos automáticamente haría perder la cantidad que el
        usuario ya introdujo manualmente en el picking (p.ej. una recepción
        parcial aún sin validar). Esos casos se dejan para revisión manual.
        """
        self.ensure_one()
        chain = self._get_full_move_chain()
        pending = chain.filtered(lambda m: m.state not in ('done', 'cancel'))

        # No tocar movimientos que ya tengan cantidad avanzada: cancelarlos
        # perdería ese progreso y obligaría a re-introducirlo.
        already_advanced = pending.filtered(lambda m: m.quantity_done)
        if already_advanced:
            _logger.info(
                "purchase_qty_decrease_fix: se excluyen %s movimiento(s) "
                "con cantidad ya avanzada (no se cancelan): %s",
                len(already_advanced), already_advanced.ids,
            )

        return pending - already_advanced

    def _get_advanced_move_chain(self):
        """Movimientos no-done/cancel de esta línea que YA tienen cantidad
        avanzada (quantity_done > 0) y que, por tanto, el fix no cancela
        automáticamente. Se usan solo para informar en el chatter.
        """
        self.ensure_one()
        chain = self._get_full_move_chain()
        pending = chain.filtered(lambda m: m.state not in ('done', 'cancel'))
        return pending.filtered(lambda m: m.quantity_done)

    def _get_full_move_chain(self):
        """Todos los stock.move de esta línea (cualquier estado), siguiendo
        la cadena encadenada hasta el final (move_dest_ids)."""
        self.ensure_one()
        origin_moves = self.env['stock.move'].search([
            ('purchase_line_id', '=', self.id),
        ])

        chain = self.env['stock.move']
        to_process = origin_moves
        while to_process:
            chain |= to_process
            to_process = (to_process.mapped('move_dest_ids') - chain)

        return chain

    def _fix_crossed_move_links(self):
        """Corrige un problema observado en producción: varios stock.move
        de ORIGEN ligados a esta línea (por ejemplo, distintos lotes de
        recepción) terminan compartiendo el MISMO conjunto de
        move_dest_ids, en vez de que cada uno apunte solo a su propia
        continuación (ej. origen_A -> destino_A, origen_B -> destino_B).

        Ese cruce rompe el mecanismo interno de Odoo para reducir demanda:
        cuando necesita "fusionar" un ajuste de cantidad dentro de
        `move.move_orig_ids.move_dest_ids`, no encuentra un destino único
        y claro, y termina cayendo al buscador de reglas de
        reabastecimiento — que falla con
        "No se encontró ninguna regla de reabastecimiento...".

        Esta corrección SOLO actúa cuando puede resolver el cruce de forma
        totalmente inequívoca: empareja cada origen con el destino que
        tiene EXACTAMENTE la misma demanda (product_uom_qty), y solo si ese
        emparejamiento es 1 a 1 y cubre a todos los orígenes y destinos
        implicados. Si hay cualquier ambigüedad (cantidades repetidas,
        número de orígenes distinto al de destinos, etc.), no toca nada y
        lo deja reportado en el chatter para revisión manual — igual que
        el resto de este módulo.
        """
        self.ensure_one()
        origin_moves = self.env['stock.move'].search([
            ('purchase_line_id', '=', self.id),
            ('state', '!=', 'cancel'),
        ])
        if len(origin_moves) < 2:
            return

        # Agrupar los orígenes por la "firma" de su conjunto de destinos
        # (ordenado, para comparar conjuntos). Si dos o más orígenes
        # distintos comparten exactamente el mismo conjunto de más de un
        # destino, eso es el cruce que queremos corregir.
        signature_map = {}
        for move in origin_moves:
            dests = move.move_dest_ids.filtered(lambda m: m.state != 'cancel')
            if len(dests) <= 1:
                continue
            signature = tuple(sorted(dests.ids))
            signature_map.setdefault(signature, self.env['stock.move'])
            signature_map[signature] |= move

        crossed_groups = [
            (signature, moves) for signature, moves in signature_map.items()
            if len(moves) > 1
        ]
        if not crossed_groups:
            return

        for signature, moves in crossed_groups:
            destinations = self.env['stock.move'].browse(list(signature))

            if len(moves) != len(destinations):
                _logger.warning(
                    "purchase_qty_decrease_fix: enlaces cruzados en la "
                    "línea %s (orígenes %s <-> destinos %s) con número de "
                    "orígenes distinto al de destinos; no se corrige "
                    "automáticamente, requiere revisión manual.",
                    self.id, moves.ids, destinations.ids,
                )
                self._post_crossed_links_message(moves, destinations)
                continue

            pairing = {}
            used_destination_ids = set()
            ambiguous = False
            for move in moves:
                candidates = destinations.filtered(
                    lambda d, move=move: (
                        d.id not in used_destination_ids
                        and float_compare(
                            d.product_uom_qty, move.product_uom_qty,
                            precision_rounding=move.product_uom.rounding,
                        ) == 0
                    )
                )
                if len(candidates) != 1:
                    ambiguous = True
                    break
                pairing[move.id] = candidates
                used_destination_ids.add(candidates.id)

            if ambiguous or len(pairing) != len(moves):
                _logger.warning(
                    "purchase_qty_decrease_fix: enlaces cruzados en la "
                    "línea %s no se pudieron resolver de forma inequívoca "
                    "por cantidad; requiere revisión manual.", self.id,
                )
                self._post_crossed_links_message(moves, destinations)
                continue

            try:
                for move in moves:
                    match = pairing[move.id]
                    move.write({'move_dest_ids': [(6, 0, match.ids)]})
                _logger.info(
                    "purchase_qty_decrease_fix: se corrigieron enlaces "
                    "cruzados en la línea %s: %s", self.id,
                    {mid: pairing[mid].ids for mid in pairing},
                )
                self._post_crossed_links_message(
                    moves, destinations, resolved=True, pairing=pairing)
            except Exception:
                _logger.warning(
                    "purchase_qty_decrease_fix: no se pudieron corregir "
                    "los enlaces cruzados de la línea %s.",
                    self.id, exc_info=True,
                )
                self._post_crossed_links_message(moves, destinations)

    def _post_crossed_links_message(self, moves, destinations,
                                     resolved=False, pairing=None):
        """Deja constancia en el chatter de un cruce de enlaces detectado
        entre movimientos de origen y destino: si se corrigió solo, o si
        requiere revisión manual.
        """
        self.ensure_one()
        if resolved and pairing:
            lines = "".join(
                "<li>Origen %s (picking %s, demanda %s) &rarr; ahora "
                "enlazado solo a destino %s (picking %s)</li>"
                % (
                    move.id, move.picking_id.name or "-", move.product_uom_qty,
                    pairing[move.id].id, pairing[move.id].picking_id.name or "-",
                )
                for move in moves
            )
            body = (
                "<p><b>Enlaces cruzados corregidos automáticamente "
                "(módulo Purchase Qty Decrease Fix)</b></p>"
                "<p>Se detectó que varios movimientos de origen compartían "
                "el mismo conjunto de movimientos de destino en vez de "
                "tener cada uno el suyo propio (lo cual puede provocar el "
                "error \"No se encontró ninguna regla de "
                "reabastecimiento...\" al reducir la cantidad). Se "
                "corrigió emparejando cada origen con el destino de igual "
                "cantidad:</p><ul>%s</ul>" % lines
            )
        else:
            moves_lines = "".join(
                "<li>%s (picking %s, demanda %s)</li>"
                % (move.id, move.picking_id.name or "-", move.product_uom_qty)
                for move in moves
            )
            dest_lines = "".join(
                "<li>%s (picking %s, demanda %s)</li>"
                % (d.id, d.picking_id.name or "-", d.product_uom_qty)
                for d in destinations
            )
            body = (
                "<p><b>⚠ Enlaces cruzados detectados (módulo Purchase Qty "
                "Decrease Fix)</b></p>"
                "<p>Varios movimientos de origen comparten el mismo "
                "conjunto de movimientos de destino, pero no se pudo "
                "determinar de forma inequívoca cómo desenredarlos "
                "automáticamente (por ejemplo, hay demandas repetidas, o "
                "el número de orígenes no coincide con el de destinos). "
                "Esto puede provocar el error \"No se encontró ninguna "
                "regla de reabastecimiento...\" al reducir la cantidad. "
                "Requiere revisión manual:</p>"
                "<p><b>Orígenes involucrados:</b></p><ul>%s</ul>"
                "<p><b>Destinos involucrados:</b></p><ul>%s</ul>"
                % (moves_lines, dest_lines)
            )
        self.order_id.message_post(body=body)

    def _has_active_origin_move(self):
        """True si existe al menos un stock.move ligado DIRECTAMENTE (por
        purchase_line_id) a esta línea que no esté 'done' ni 'cancel'.

        Se usa para detectar, antes de escribir una nueva cantidad, si la
        línea ya se quedó sin ningún movimiento "vivo" (por ejemplo, porque
        este mismo módulo canceló todo en una reducción previa). Ese es
        precisamente el escenario en el que un aumento posterior puede hacer
        que Odoo genere la nueva demanda por el TOTAL de la línea en lugar
        de solo por la diferencia contra lo ya recibido.
        """
        self.ensure_one()
        return bool(self.env['stock.move'].search_count([
            ('purchase_line_id', '=', self.id),
            ('state', 'not in', ('done', 'cancel')),
        ]))

    # ------------------------------------------------------------------
    # write()
    # ------------------------------------------------------------------
    def write(self, vals):
        if 'product_qty' not in vals:
            return super().write(vals)

        new_qty = vals['product_qty']
        lines_to_clean = self.env['purchase.order.line']
        lines_to_check_increase = self.env['purchase.order.line']

        for line in self:
            if line.order_id.state not in ('purchase', 'done'):
                continue

            # Caso 1: la nueva cantidad queda igual o por debajo de lo ya
            # recibido. Es el caso donde Odoo genera el movimiento push
            # negativo que rompe la búsqueda de reglas de reabastecimiento.
            if float_compare(new_qty, line.qty_received,
                              precision_rounding=line.product_uom.rounding) <= 0:
                lines_to_clean |= line
                continue

            # Caso 2: es un aumento de cantidad. Si en este momento la línea
            # no tiene ningún movimiento de origen activo (por ejemplo,
            # porque este módulo los canceló todos en una reducción
            # anterior), marcamos la línea para revisar después del write
            # si Odoo generó la nueva demanda correctamente o por el total.
            if float_compare(new_qty, line.product_qty,
                              precision_rounding=line.product_uom.rounding) > 0:
                if not line._has_active_origin_move():
                    lines_to_check_increase |= line

        for line in lines_to_clean:
            # Antes de calcular qué cancelar, corregimos (si es posible de
            # forma inequívoca) cualquier enlace cruzado entre movimientos
            # de origen y destino: esto evita que Odoo, más adelante, se
            # quede sin un destino claro donde fusionar el ajuste de
            # cantidad y termine buscando una regla de reabastecimiento
            # que no existe.
            line._fix_crossed_move_links()

            pending_moves = line._get_pending_move_chain()
            skipped_moves = line._get_advanced_move_chain()

            if pending_moves:
                _logger.info(
                    "purchase_qty_decrease_fix: cancelando %s movimiento(s) "
                    "pendiente(s) de la línea %s (producto %s) antes de "
                    "reducir la cantidad de %s a %s.",
                    len(pending_moves), line.id, line.product_id.display_name,
                    line.product_qty, new_qty,
                )
                line._post_qty_decrease_fix_message(
                    pending_moves, new_qty, skipped_moves)
                pending_moves._action_cancel()
                try:
                    pending_moves.write({'product_uom_qty': 0.0})
                except Exception:
                    _logger.warning(
                        "purchase_qty_decrease_fix: no se pudo poner en 0 "
                        "la cantidad de los movimientos %s tras cancelarlos.",
                        pending_moves.ids, exc_info=True,
                    )
            elif skipped_moves:
                # No había nada que cancelar automáticamente, pero sí hay
                # movimientos con cantidad avanzada que requieren revisión.
                line._post_qty_decrease_fix_message(
                    self.env['stock.move'], new_qty, skipped_moves)

        result = super().write(vals)

        for line in lines_to_check_increase:
            line._fix_overdemand_after_increase(new_qty)

        return result

    # ------------------------------------------------------------------
    # Corrección del caso "aumento tras limpieza total"
    # ------------------------------------------------------------------
    def _fix_overdemand_after_increase(self, new_qty):
        """Corrige el caso en el que, tras subir la cantidad de una línea
        que no tenía ningún movimiento de origen activo, Odoo generó la
        nueva demanda pendiente por el TOTAL de la línea (new_qty) en lugar
        de solo por la diferencia contra lo ya recibido
        (new_qty - qty_received).

        Además, si el flujo es en varias etapas (p. ej. tránsito ->
        almacén), corrige también la(s) etapa(s) siguiente(s)
        (move_dest_ids) para que reflejen lo que YA está avanzado en la
        etapa anterior y aún no se ha movido (qty_received) — pero SOLO si
        ese movimiento posterior está encadenado exclusivamente a los
        movimientos de esta línea (ninguna otra línea de compra ni producto
        distinto aporta demanda a ese mismo movimiento). Si no se puede
        confirmar esa exclusividad, se deja para revisión manual.
        """
        self.ensure_one()

        precision = self.product_uom.rounding
        expected_pending = new_qty - self.qty_received
        if float_compare(expected_pending, 0.0,
                          precision_rounding=precision) <= 0:
            return

        origin_moves = self.env['stock.move'].search([
            ('purchase_line_id', '=', self.id),
        ]).filtered(lambda m: m.state not in ('done', 'cancel'))

        if not origin_moves:
            return

        total_origin_demand = sum(origin_moves.mapped('product_uom_qty'))
        if float_compare(total_origin_demand, expected_pending,
                          precision_rounding=precision) <= 0:
            # No hay sobre-demanda que corregir (o incluso está por debajo,
            # lo cual escapa al propósito de este método).
            return

        _logger.info(
            "purchase_qty_decrease_fix: detectada sobre-demanda tras "
            "aumentar la línea %s (producto %s) a %s (recibido %s, "
            "pendiente esperado %s, pendiente generado por Odoo %s). "
            "Corrigiendo movimiento(s) de origen.",
            self.id, self.product_id.display_name, new_qty,
            self.qty_received, expected_pending, total_origin_demand,
        )

        downstream_candidates = self.env['stock.move']
        failed_origin_moves = self.env['stock.move']

        if len(origin_moves) == 1:
            move = origin_moves
            downstream_candidates = move.move_dest_ids.filtered(
                lambda m: m.state not in ('done', 'cancel'))
            try:
                move.write({'product_uom_qty': expected_pending})
            except Exception:
                _logger.warning(
                    "purchase_qty_decrease_fix: no se pudo corregir la "
                    "demanda del movimiento de origen %s (línea %s) tras "
                    "el aumento de cantidad; requiere revisión manual.",
                    move.id, self.id, exc_info=True,
                )
                failed_origin_moves |= move
        else:
            # Caso poco común: varios movimientos de origen activos a la
            # vez. Repartimos la corrección proporcionalmente a su demanda
            # actual para no favorecer arbitrariamente a uno sobre otro.
            remaining = expected_pending
            moves_list = list(origin_moves)
            for idx, move in enumerate(moves_list):
                downstream_candidates |= move.move_dest_ids.filtered(
                    lambda m: m.state not in ('done', 'cancel'))
                if idx == len(moves_list) - 1:
                    share = remaining
                else:
                    share = (move.product_uom_qty / total_origin_demand) * expected_pending
                    remaining -= share
                try:
                    move.write({'product_uom_qty': share})
                except Exception:
                    _logger.warning(
                        "purchase_qty_decrease_fix: no se pudo corregir la "
                        "demanda del movimiento de origen %s (línea %s) "
                        "tras el aumento de cantidad; requiere revisión "
                        "manual.", move.id, self.id, exc_info=True,
                    )
                    failed_origin_moves |= move

        corrected_downstream, uncorrected_downstream, failed_downstream = (
            self._fix_downstream_leg(downstream_candidates, origin_moves)
        )

        self._post_qty_increase_fix_message(
            new_qty, expected_pending,
            origin_moves - failed_origin_moves,
            corrected_downstream,
            uncorrected_downstream,
            failed_origin_moves,
            failed_downstream,
        )

    def _fix_downstream_leg(self, downstream_moves, origin_moves):
        """Corrige la(s) etapa(s) siguiente(s) de la cadena (p. ej. tránsito
        -> almacén) para que su demanda refleje lo YA avanzado en la etapa
        anterior (self.qty_received) en lugar de heredar la demanda
        (posiblemente incorrecta) de la etapa anterior.

        Solo se corrige un movimiento si:
          - es del MISMO producto que esta línea, y
          - está encadenado EXCLUSIVAMENTE a movimientos de origen de esta
            línea (move_orig_ids no incluye ningún movimiento ajeno).

        Devuelve (corregidos, no_corregidos_por_seguridad,
        fallidos_al_intentar_corregir) para reportarlos en el chatter.
        """
        self.ensure_one()
        corrected = self.env['stock.move']
        uncorrected = self.env['stock.move']
        failed = self.env['stock.move']

        for dmove in downstream_moves:
            other_origins = dmove.move_orig_ids - origin_moves
            same_product = dmove.product_id.id == self.product_id.id
            if other_origins or not same_product:
                uncorrected |= dmove
                continue
            try:
                dmove.write({'product_uom_qty': self.qty_received})
                corrected |= dmove
            except Exception:
                _logger.warning(
                    "purchase_qty_decrease_fix: no se pudo corregir la "
                    "demanda del movimiento posterior %s (línea %s) tras "
                    "el aumento de cantidad; requiere revisión manual.",
                    dmove.id, self.id, exc_info=True,
                )
                failed |= dmove

        return corrected, uncorrected, failed

    # ------------------------------------------------------------------
    # Mensajes en el chatter
    # ------------------------------------------------------------------
    def _post_qty_decrease_fix_message(self, pending_moves, new_qty, skipped_moves=None):
        """Deja constancia en el chatter de la orden de compra de que este
        módulo intervino: qué línea, qué movimientos se cancelaron y por qué,
        y qué movimientos NO se tocaron por tener cantidad ya avanzada.
        """
        self.ensure_one()
        skipped_moves = skipped_moves or self.env['stock.move']

        moves_lines = "".join(
            "<li>%s (picking %s): %s &rarr; %s, cantidad %s</li>"
            % (
                move.id,
                move.picking_id.name or "-",
                move.location_id.display_name,
                move.location_dest_id.display_name,
                move.product_uom_qty,
            )
            for move in pending_moves
        )

        skipped_lines = "".join(
            "<li>%s (picking %s): %s &rarr; %s, cantidad avanzada %s "
            "(demanda %s) &mdash; requiere revisión manual</li>"
            % (
                move.id,
                move.picking_id.name or "-",
                move.location_id.display_name,
                move.location_dest_id.display_name,
                move.quantity_done,
                move.product_uom_qty,
            )
            for move in skipped_moves
        )

        cancelled_block = (
            "<p>Al reducir la cantidad pedida del producto <b>%s</b> "
            "de %s a %s (ya recibido: %s), se cancelaron automáticamente "
            "los siguientes movimientos pendientes para evitar el error "
            "\"No se encontró ninguna regla de reabastecimiento [...] en "
            "'Ubicaciones de Socios/Proveedor'\" (la cantidad mostrada abajo "
            "es la que tenían antes de cancelarse; después se pusieron en 0):</p>"
            "<ul>%s</ul>"
            % (
                self.product_id.display_name,
                self.product_qty,
                new_qty,
                self.qty_received,
                moves_lines,
            )
        ) if pending_moves else (
            "<p>Se redujo la cantidad pedida del producto <b>%s</b> "
            "de %s a %s (ya recibido: %s). No había movimientos pendientes "
            "sin avanzar que cancelar.</p>"
            % (
                self.product_id.display_name,
                self.product_qty,
                new_qty,
                self.qty_received,
            )
        )

        skipped_block = (
            "<p><b>Atención:</b> los siguientes movimientos tenían cantidad "
            "ya avanzada (introducida manualmente) y NO se cancelaron "
            "automáticamente para no perder esa información. Revísalos "
            "manualmente:</p><ul>%s</ul>" % skipped_lines
        ) if skipped_moves else ""

        body = (
            "<p><b>Ajuste automático por reducción de cantidad "
            "(módulo Purchase Qty Decrease Fix)</b></p>"
            + cancelled_block
            + skipped_block
            + "<p>Los movimientos de otros productos en los mismos "
              "traslados/pickings no se vieron afectados.</p>"
        )
        self.order_id.message_post(body=body)

    def _post_qty_increase_fix_message(self, new_qty, expected_pending,
                                        corrected_moves, corrected_downstream,
                                        uncorrected_downstream=None,
                                        failed_origin_moves=None,
                                        failed_downstream_moves=None):
        """Deja constancia en el chatter de que, tras un aumento de
        cantidad, se corrigió una sobre-demanda generada por Odoo (leg 1),
        y qué pasó con la(s) etapa(s) siguiente(s) de la cadena (leg 2):
        cuáles se corrigieron automáticamente, cuáles quedan pendientes de
        revisión manual (por no poder confirmar que son exclusivas de esta
        línea), y cuáles se intentaron corregir pero fallaron (por ejemplo,
        por un error de Odoo al escribir el movimiento) y requieren
        corrección manual urgente.
        """
        self.ensure_one()
        uncorrected_downstream = uncorrected_downstream or self.env['stock.move']
        failed_origin_moves = failed_origin_moves or self.env['stock.move']
        failed_downstream_moves = failed_downstream_moves or self.env['stock.move']

        corrected_lines = "".join(
            "<li>%s (picking %s): demanda corregida a %s</li>"
            % (move.id, move.picking_id.name or "-", move.product_uom_qty)
            for move in corrected_moves
        )

        downstream_corrected_block = ""
        if corrected_downstream:
            downstream_corrected_lines = "".join(
                "<li>%s (picking %s): demanda corregida a %s (lo ya "
                "avanzado en la etapa anterior)</li>"
                % (move.id, move.picking_id.name or "-", move.product_uom_qty)
                for move in corrected_downstream
            )
            downstream_corrected_block = (
                "<p>También se corrigió automáticamente la siguiente etapa "
                "de la cadena, al confirmarse que está encadenada "
                "exclusivamente a esta línea:</p>"
                "<ul>%s</ul>" % downstream_corrected_lines
            )

        downstream_uncorrected_block = ""
        if uncorrected_downstream:
            downstream_uncorrected_lines = "".join(
                "<li>%s (picking %s): %s &rarr; %s, cantidad actual %s "
                "&mdash; revisar manualmente, no se pudo confirmar que sea "
                "exclusivo de esta línea/producto</li>"
                % (
                    move.id,
                    move.picking_id.name or "-",
                    move.location_id.display_name,
                    move.location_dest_id.display_name,
                    move.product_uom_qty,
                )
                for move in uncorrected_downstream
            )
            downstream_uncorrected_block = (
                "<p><b>Atención:</b> los siguientes movimientos posteriores "
                "de la cadena NO se corrigieron automáticamente porque "
                "podrían consolidar cantidades de otros lotes, líneas o "
                "productos; revísalos manualmente:</p>"
                "<ul>%s</ul>" % downstream_uncorrected_lines
            )

        failed_block = ""
        failed_all = failed_origin_moves | failed_downstream_moves
        if failed_all:
            failed_lines = "".join(
                "<li>%s (picking %s): %s &rarr; %s, cantidad actual %s "
                "&mdash; <b>se intentó corregir automáticamente y falló</b>, "
                "revisar manualmente cuanto antes</li>"
                % (
                    move.id,
                    move.picking_id.name or "-",
                    move.location_id.display_name,
                    move.location_dest_id.display_name,
                    move.product_uom_qty,
                )
                for move in failed_all
            )
            failed_block = (
                "<p><b>⚠ Atención:</b> se intentó corregir automáticamente "
                "la demanda de los siguientes movimientos y la corrección "
                "falló (por ejemplo, por un error de Odoo al escribir el "
                "movimiento). La cantidad de la línea de compra SÍ se "
                "actualizó correctamente; solo estos movimientos de stock "
                "quedaron con demanda incorrecta y requieren corrección "
                "manual:</p><ul>%s</ul>" % failed_lines
            )

        body = (
            "<p><b>Ajuste automático por aumento de cantidad tras limpieza "
            "previa (módulo Purchase Qty Decrease Fix)</b></p>"
            "<p>Al subir la cantidad pedida del producto <b>%s</b> a %s "
            "(ya recibido: %s), Odoo generó una demanda pendiente por el "
            "total de la línea en lugar de solo la diferencia (%s). Se "
            "corrigieron los siguientes movimientos de origen:</p>"
            "<ul>%s</ul>"
            % (
                self.product_id.display_name,
                new_qty,
                self.qty_received,
                expected_pending,
                corrected_lines,
            )
            + downstream_corrected_block
            + downstream_uncorrected_block
            + failed_block
        )
        self.order_id.message_post(body=body)
