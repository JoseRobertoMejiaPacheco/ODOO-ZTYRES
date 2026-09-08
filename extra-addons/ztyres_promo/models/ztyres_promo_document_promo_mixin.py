# -*- coding: utf-8 -*-
"""
Mixin reutilizable para calcular, sobre un documento de venta
(cotización, orden de venta o factura), qué promociones aprobadas o
confirmadas (`ztyres_promo.notas_credito` con status = 'approve_p' o
'done') aplican y cuánto se ganaría en Nota de Crédito.

IMPORTANTE: esto es solo informativo. En ningún punto se crea una
Nota de Crédito real (account.move) — únicamente se calcula y muestra
el monto/porcentaje estimado; la NC se sigue generando manualmente
desde el flujo normal de `ztyres_promo.notas_credito` (acción
"Confirmar NC").

El texto que se muestra (parte 'Global') NO lo redacta este código:
se toma del campo `promo_ganada_message` configurado en cada
promoción (ver ztyres_promo_notas_credito.py), reemplazando los
marcadores {promocion}/{monto}/{porcentaje}. Solo se usa una frase
por defecto como respaldo si esa promoción no tiene texto configurado
(por ejemplo, promociones creadas antes de que existiera este campo).

Se usa desde `ztyres_promo_sale_order.py`, `ztyres_promo_account_move.py`
y sus equivalentes de línea, para no duplicar la lógica de
agregación/render.
"""
from datetime import date
from html import escape

from odoo import models


class _SafeFormatDict(dict):
    """Para `str.format_map`: si el texto configurado por el usuario
    referencia un marcador que no reconocemos (ej. escribió mal
    '{monot}'), lo deja tal cual en vez de reventar con un error."""

    def __missing__(self, key):
        return '{%s}' % key


class ZtyresPromoDocumentMixin(models.AbstractModel):
    _name = 'ztyres_promo.document_promo_mixin'
    _description = 'Evaluación de promociones ganadas para documentos de venta'

    # --- TEMPORAL --------------------------------------------------
    # Corte de arranque: documentos con fecha anterior a esta no se
    # evalúan (quedan en 0 / texto vacío), para que al instalar el
    # módulo no se "reactiven" miles de cotizaciones/facturas
    # históricas de golpe. De aquí en adelante sí se calcula normal.
    # Quitar esta constante y su chequeo en compute_promo_ganada
    # cuando ya no se necesite este resguardo.
    _PROMO_EVAL_CUTOFF_DATE = date(2026, 7, 19)
    # -----------------------------------------------------------------

    # Estados de promoción que cuentan como "vigentes" para este cálculo:
    # Promoción Aprobada (approve_p) o Confirmado (done).
    _PROMO_EVAL_VALID_STATUSES = ('approve_p', 'done')

    def _get_approved_promotions(self, doc_date):
        """Promociones aprobadas o confirmadas, y vigentes a `doc_date`
        (dentro de su start_date/end_date, cuando estén definidos)."""
        domain = [('status', 'in', list(self._PROMO_EVAL_VALID_STATUSES))]
        if doc_date:
            domain += [
                '|', ('start_date', '=', False), ('start_date', '<=', doc_date),
                '|', ('end_date', '=', False), ('end_date', '>=', doc_date),
            ]
        return self.env['ztyres_promo.notas_credito'].search(domain)

    def _evaluate_promotions(self, partner, doc_date, lines, quantity_field, edi_vat_receptor=False):
        """Evalúa todas las promociones aprobadas y vigentes contra las
        líneas dadas y retorna la lista de resultados (uno por
        promoción que sí aplica). Compartido por `compute_promo_ganada`
        y `compute_promo_ganada_line_details` para no evaluar dos veces."""
        if not doc_date or doc_date < self._PROMO_EVAL_CUTOFF_DATE:
            return []

        results = []
        for promo in self._get_approved_promotions(doc_date):
            result = promo.evaluate_document(
                partner, doc_date, lines, quantity_field, edi_vat_receptor=edi_vat_receptor
            )
            if result:
                results.append(result)
        return results

    def compute_promo_ganada(self, partner, doc_date, lines, quantity_field, edi_vat_receptor=False):
        """Evalúa todas las promociones aprobadas y vigentes contra las
        líneas dadas. Solo calcula/muestra el resultado; no crea
        ninguna NC.

        :return: (monto_total_ganado, texto_html) — texto_html es False
            si ninguna promoción aplica.
        """
        results = self._evaluate_promotions(partner, doc_date, lines, quantity_field, edi_vat_receptor)

        # Las promociones configuradas como 'no mostrar' (opción por
        # defecto de `promo_display_mode`) no deben aparecer en
        # ningún lado del documento: ni en la cotización/factura
        # (backend), ni en sus PDF. Se excluyen aquí, antes de armar
        # el texto y el monto agregado, para que ni el texto ni el
        # monto mostrado las incluyan.
        results = [r for r in results if (r['promo'].promo_display_mode or 'none') != 'none']
        if not results:
            return 0.0, False

        total = sum(r['ganado'] for r in results)
        return total, self._render_promo_text(results)

    def compute_promo_ganada_line_details(self, partner, doc_date, lines, quantity_field, edi_vat_receptor=False):
        """Para cada línea, arma su propio texto — usando el mismo
        `promo_ganada_message` configurado en cada promoción, pero con
        el monto ganado de ESA línea puntual (no el total del
        documento) — y el monto total ganado en ella (sumado si más
        de una promoción aplica a la misma línea).

        Respeta `promo_display_mode` de cada promoción: una promoción
        configurada como 'global' NO aparece a nivel de línea (solo en
        el resumen del documento completo); 'product' o 'both' sí
        aparecen aquí. Es lo mismo que decide qué se muestra en el
        resumen del documento (`_render_promo_item`), solo que del
        lado de la línea.

        A diferencia de `compute_promo_ganada`, este texto es texto
        plano (para un campo Text en la línea, no un campo Html), así
        que NO se escapa: si el usuario escribió comillas u otros
        caracteres en su mensaje, se ven tal cual.

        :return: dict {line.id: (monto_ganado, texto_o_False)}
        """
        results = self._evaluate_promotions(partner, doc_date, lines, quantity_field, edi_vat_receptor)

        per_line_amount = {}
        per_line_messages = {}
        for result in results:
            promo = result['promo']
            display_mode = promo.promo_display_mode or 'global'
            if display_mode not in ('product', 'both'):
                # Esta promoción está configurada para mostrarse solo
                # a nivel global (documento completo); no aparece
                # desglosada por línea.
                continue

            discount_percent = result['discount_percent']
            for line_id, ganado in result.get('line_ganado_map', {}).items():
                if ganado <= 0:
                    continue
                per_line_amount[line_id] = per_line_amount.get(line_id, 0.0) + ganado
                per_line_messages.setdefault(line_id, []).append(
                    self._render_promo_message(promo, ganado, discount_percent)
                )

        return {
            line_id: (per_line_amount[line_id], '\n'.join(per_line_messages[line_id]))
            for line_id in per_line_amount
        }

    def _render_promo_text(self, results):
        items_html = ''.join(self._render_promo_item(r) for r in results)
        return (
            '<div>'
            '<strong>Promoción(es) aprobada(s) ganadas en este documento:</strong>'
            '<ul>%s</ul>'
            '</div>'
        ) % items_html

    def _render_promo_item(self, result):
        """Según `promo_display_mode` configurado en la propia promoción:
        - 'global': el texto configurado en `promo_ganada_message`.
        - 'product': solo el desglose por producto (con el nombre de
          la promoción como encabezado, ya que no se muestra su texto).
        - 'both': las dos cosas.
        """
        promo = result['promo']
        display_mode = promo.promo_display_mode or 'global'
        show_global = display_mode in ('global', 'both')
        show_product = display_mode in ('product', 'both')

        body = ''
        if show_global:
            body += escape(self._render_promo_message(
                promo,
                result['ganado'],
                result['discount_percent'],
                gift_card_amount=result.get('gift_card_amount', 0.0),
            ))
        else:
            body += '<strong>%s</strong>' % escape(promo.nombre or promo.display_name)

        if show_product:
            body += self._render_promo_product_breakdown(result)

        return '<li>%s</li>' % body

    def _render_promo_message(
        self,
        promo,
        ganado,
        discount_percent,
        gift_card_amount=0.0,
    ):
        """Arma el mensaje de una promoción para un monto dado
        (puede ser el total del documento o el de una línea puntual),
        usando `promo_ganada_message` (el texto configurado por el
        usuario en la promoción) con sus marcadores reemplazados. Si
        la promoción no tiene texto configurado, usa una frase por
        defecto (compatibilidad con promociones creadas antes de que
        existiera este campo). NO escapa el resultado — quien llame a
        esto decide si necesita escaparlo (HTML) o no (texto plano)."""
        porcentaje = (
            ('{:.1f}'.format(discount_percent)).rstrip('0').rstrip('.') + '%'
            if discount_percent is not None else ''
        )
        promocion_name = promo.nombre or promo.display_name

        # En una tarjeta de regalo entregada por fuera, `ganado` es cero
        # por diseño (no hay NC). Si `{monto}` se armara con él, el
        # aviso diría "¡Ganaste $0.00!" en la cara del cliente, que es
        # lo contrario de lo que la promoción quiere comunicar. El monto
        # que se muestra es el valor de la tarjeta.
        tarjeta = '${:,.2f}'.format(gift_card_amount) if gift_card_amount else ''
        monto = tarjeta if gift_card_amount and not ganado else '${:,.2f}'.format(ganado)

        template = promo.promo_ganada_message
        if not template:
            porcentaje_suffix = ' (%s)' % porcentaje if porcentaje else ''
            if gift_card_amount and not ganado:
                return '%s: %s en tarjeta de regalo' % (promocion_name, tarjeta)
            return '%s%s: %s ganado en NC' % (promocion_name, porcentaje_suffix, monto)

        return self._format_message(
            template,
            promocion=promocion_name,
            monto=monto,
            porcentaje=porcentaje,
            tarjeta=tarjeta,
        )

    def _format_message(self, template, **values):
        """Reemplaza los marcadores (`{promocion}`, `{monto}`,
        `{porcentaje}`, ...) de un texto configurado por el usuario.
        No escapa nada — ver `_render_promo_message`."""
        try:
            return template.format_map(_SafeFormatDict(values))
        except Exception:
            return template

    def _render_promo_product_breakdown(self, result):
        product_lines = [l for l in result.get('lines', []) if l['ganado'] > 0]
        if not product_lines:
            return ''

        items_html = ''.join(
            '<li>%s: <strong>$%s</strong></li>' % (
                escape(l['product_name']),
                '{:,.2f}'.format(l['ganado']),
            )
            for l in product_lines
        )
        return '<ul>%s</ul>' % items_html
