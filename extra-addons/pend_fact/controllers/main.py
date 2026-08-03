import logging
import calendar
from odoo import http
from odoo.http import request
from datetime import date

_logger = logging.getLogger(__name__)


def _rango(year, month, date_from, date_to):
    if date_from and date_to:
        return date_from, date_to
    if year and month:
        last_day = calendar.monthrange(int(year), int(month))[1]
        return f"{year}-{int(month):02d}-01", f"{year}-{int(month):02d}-{last_day}"
    y = int(year) if year else date.today().year
    return f"{y}-01-01", f"{y}-12-31"


class PendFact(http.Controller):

    @http.route('/pend_fact/data', type='json', auth='user')
    def get_data(self, year=None, month=None, date_from=None, date_to=None):
        _logger.info("pend_fact ► year=%s month=%s date_from=%s date_to=%s",
                     year, month, date_from, date_to)

        start_date, end_date = _rango(year, month, date_from, date_to)
        _logger.info("pend_fact ► rango %s → %s", start_date, end_date)

        # ── Zona horaria del servidor ──────────────────────────────────────
        # so.date_order se guarda en UTC. Convertimos a la tz del servidor
        # para que la fecha mostrada coincida con la que ve el usuario en Odoo.
        tz = request.env.user.tz or 'America/Mexico_City'

        cr = request.env.cr

        # ── Query principal ────────────────────────────────────────────────
        # Usa qty_delivered y qty_invoiced — campos calculados por Odoo que
        # ya consideran devoluciones, NC y cualquier ajuste interno.
        # Mucho más simple y confiable que recalcular desde stock_move.
        cr.execute("""
            SELECT
                so.name                                                 AS venta,
                -- Convertir UTC → tz local para la fecha correcta
                (so.date_order AT TIME ZONE 'UTC' AT TIME ZONE %(tz)s)::date
                                                                        AS fecha,
                rp.name                                                 AS cliente,
                COALESCE(ru.name, 'Sin vendedor')                       AS vendedor,
                COALESCE(pt.name->>'es_MX', pt.name->>'en_US')         AS producto,
                SUM(sol.qty_delivered)                                  AS entregado,
                SUM(sol.qty_invoiced)                                   AS facturado,
                SUM(sol.qty_delivered - sol.qty_invoiced)               AS pendiente
            FROM sale_order_line sol
            JOIN sale_order       so  ON so.id  = sol.order_id
            JOIN res_partner      rp  ON rp.id  = so.partner_id
            LEFT JOIN res_users   rsu ON rsu.id = so.user_id
            LEFT JOIN res_partner ru  ON ru.id  = rsu.partner_id
            JOIN product_product  pp  ON pp.id  = sol.product_id
            JOIN product_template pt  ON pt.id  = pp.product_tmpl_id
            WHERE (so.date_order AT TIME ZONE 'UTC' AT TIME ZONE %(tz)s)::date
                      >= %(start)s
              AND (so.date_order AT TIME ZONE 'UTC' AT TIME ZONE %(tz)s)::date
                      <= %(end)s
              AND pt.type = 'product'
            GROUP BY
                so.name,
                (so.date_order AT TIME ZONE 'UTC' AT TIME ZONE %(tz)s)::date,
                rp.name, ru.name,
                COALESCE(pt.name->>'es_MX', pt.name->>'en_US'),
                pp.product_tmpl_id
            HAVING SUM(sol.qty_delivered - sol.qty_invoiced) > 0.001
               OR  SUM(sol.qty_delivered - sol.qty_invoiced) < -0.001
            ORDER BY ABS(SUM(sol.qty_delivered - sol.qty_invoiced)) DESC, so.name
        """, {'start': start_date, 'end': end_date, 'tz': tz})

        rows_raw = cr.fetchall()
        _logger.info("pend_fact ► filas: %d", len(rows_raw))

        rows_fact = []
        rows_nc   = []
        ordenes_fact = set()
        ordenes_nc   = set()
        total_pend_fact = 0.0
        total_pend_nc   = 0.0

        for i, r in enumerate(rows_raw):
            pendiente = float(r[7])
            base = {
                'id':        i,
                'venta':     r[0],
                'fecha':     str(r[1]),
                'cliente':   r[2],
                'vendedor':  r[3],
                'producto':  r[4],
                'entrega':   round(float(r[5]), 2),
                'facturado': round(float(r[6]), 2),
                'nc':        0,
            }
            if pendiente > 0.001:
                rows_fact.append({**base, 'pendiente': round(pendiente, 2)})
                total_pend_fact += pendiente
                ordenes_fact.add(r[0])
            elif pendiente < -0.001:
                rows_nc.append({**base, 'pendiente_nc': round(abs(pendiente), 2)})
                total_pend_nc += abs(pendiente)
                ordenes_nc.add(r[0])

        # ── NC no ligadas: solo las que tienen lineas de producto almacenable ──
        cr.execute("""
            SELECT DISTINCT ON (am.id)
                am.id, am.name, am.invoice_date, rp.name, am.amount_total
            FROM account_move am
            JOIN res_partner rp ON rp.id = am.partner_id
            WHERE am.move_type     = 'out_refund'
              AND am.state         = 'posted'
              AND am.invoice_date >= %(start)s
              AND am.invoice_date <= %(end)s
              AND EXISTS (
                SELECT 1 FROM account_move_line aml3
                JOIN product_product  pp3 ON pp3.id = aml3.product_id
                JOIN product_template pt3 ON pt3.id = pp3.product_tmpl_id
                WHERE aml3.move_id      = am.id
                  AND aml3.display_type = 'product'
                  AND pt3.type          = 'product'
              )
              AND NOT EXISTS (
                SELECT 1 FROM account_move_line aml2
                JOIN sale_order_line_invoice_rel s ON s.invoice_line_id = aml2.id
                WHERE aml2.move_id = am.id
              )
            ORDER BY am.id, am.invoice_date DESC
        """, {'start': start_date, 'end': end_date})

        nc_sueltas = [{
            'move_id':  r[0],
            'nc_name':  r[1],
            'nc_fecha': str(r[2]) if r[2] else '',
            'cliente':  r[3],
            'total':    round(float(r[4] or 0), 2),
            'lineas':   [],
        } for r in cr.fetchall()]

        return {
            'rows':             rows_fact,
            'rows_nc':          rows_nc,
            'total_pend':       round(total_pend_fact, 2),
            'total_pend_nc':    round(total_pend_nc, 2),
            'total_ordenes':    len(ordenes_fact),
            'total_ordenes_nc': len(ordenes_nc),
            'total_lineas':     len(rows_fact),
            'total_lineas_nc':  len(rows_nc),
            'start_date':       start_date,
            'end_date':         end_date,
            'nc_sueltas':       nc_sueltas,
        }

    @http.route('/pend_fact/nc_lineas', type='json', auth='user')
    def get_nc_lineas(self, move_id):
        cr = request.env.cr
        cr.execute("""
            SELECT COALESCE(pt.name->>'es_MX', pt.name->>'en_US'),
                   aml.quantity, aml.price_unit, aml.price_subtotal
            FROM account_move_line aml
            JOIN product_product  pp ON pp.id = aml.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE aml.move_id      = %(id)s
              AND aml.display_type = 'product'
              AND pt.type          = 'product'
            ORDER BY aml.id
        """, {'id': move_id})
        return [{'producto': r[0] or '—', 'cantidad': float(r[1] or 0),
                 'precio': float(r[2] or 0), 'subtotal': float(r[3] or 0)}
                for r in cr.fetchall()]

    @http.route('/pend_fact/orden', type='json', auth='user')
    def get_orden(self, venta):
        """Análisis de pedido usando qty_delivered y qty_invoiced de Odoo."""
        cr = request.env.cr
        tz = request.env.user.tz or 'America/Mexico_City'

        cr.execute("""
            SELECT
                COALESCE(pt.name->>'es_MX', pt.name->>'en_US')     AS producto,
                sol.product_uom_qty                                  AS pedido,
                sol.qty_delivered                                    AS entregado,
                sol.qty_invoiced                                     AS facturado,
                sol.qty_delivered - sol.qty_invoiced                 AS pendiente,
                so.name                                              AS venta,
                (so.date_order AT TIME ZONE 'UTC'
                              AT TIME ZONE %(tz)s)::date             AS fecha,
                rp.name                                              AS cliente,
                COALESCE(ru.name, 'Sin vendedor')                    AS vendedor,
                -- Facturas y NC ligadas para referencia
                (SELECT STRING_AGG(DISTINCT am2.name, ', ')
                 FROM sale_order_line_invoice_rel slir2
                 JOIN account_move_line aml2 ON aml2.id = slir2.invoice_line_id
                 JOIN account_move am2 ON am2.id = aml2.move_id
                 WHERE slir2.order_line_id = sol.id
                   AND am2.move_type = 'out_invoice'
                   AND am2.state = 'posted')                         AS facturas,
                (SELECT STRING_AGG(DISTINCT am2.name, ', ')
                 FROM sale_order_line_invoice_rel slir2
                 JOIN account_move_line aml2 ON aml2.id = slir2.invoice_line_id
                 JOIN account_move am2 ON am2.id = aml2.move_id
                 WHERE slir2.order_line_id = sol.id
                   AND am2.move_type = 'out_refund'
                   AND am2.state = 'posted')                         AS notas_credito
            FROM sale_order_line sol
            JOIN sale_order       so  ON so.id  = sol.order_id
            JOIN res_partner      rp  ON rp.id  = so.partner_id
            LEFT JOIN res_users   rsu ON rsu.id = so.user_id
            LEFT JOIN res_partner ru  ON ru.id  = rsu.partner_id
            JOIN product_product  pp  ON pp.id  = sol.product_id
            JOIN product_template pt  ON pt.id  = pp.product_tmpl_id
            WHERE so.name  = %(venta)s
              AND pt.type  = 'product'
            ORDER BY COALESCE(pt.name->>'es_MX', pt.name->>'en_US')
        """, {'venta': venta, 'tz': tz})

        rows = cr.fetchall()
        if not rows:
            return {'found': False, 'venta': venta}

        lineas = [{
            'producto':      r[0] or '—',
            'pedido':        round(float(r[1] or 0), 2),
            'entregado':     round(float(r[2] or 0), 2),
            'facturado':     round(float(r[3] or 0), 2),
            'pendiente':     round(float(r[4] or 0), 2),
            'facturas':      r[9]  or '—',
            'notas_credito': r[10] or '—',
        } for r in rows]

        return {
            'found':    True,
            'venta':    rows[0][5],
            'fecha':    str(rows[0][6]),
            'cliente':  rows[0][7],
            'vendedor': rows[0][8],
            'lineas':   lineas,
        }

    @http.route('/pend_fact/auditoria', type='json', auth='user')
    def get_auditoria(self, venta, producto):
        """Detalle movimiento a movimiento para auditar."""
        cr = request.env.cr
        cr.execute("""
            SELECT sm.id, sp.name, spt.code, sm.product_uom_qty, sm.date::date,
                   CASE spt.code WHEN 'outgoing' THEN  sm.product_uom_qty
                                 WHEN 'incoming' THEN -sm.product_uom_qty
                                 ELSE 0 END AS cantidad_neta
            FROM sale_order_line sol
            JOIN sale_order so ON so.id = sol.order_id
            JOIN product_product pp ON pp.id = sol.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            JOIN stock_move sm ON sm.sale_line_id = sol.id
            JOIN stock_picking sp ON sp.id = sm.picking_id
            JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
            WHERE so.name = %(v)s
              AND COALESCE(pt.name->>'es_MX', pt.name->>'en_US') = %(p)s
              AND sm.state = 'done'
              AND spt.code IN ('outgoing', 'incoming')
            ORDER BY sm.date, sm.id
        """, {'v': venta, 'p': producto})
        moves = cr.fetchall()

        cr.execute("""
            SELECT am.id, am.name, am.move_type, am.invoice_date, am.state,
                   aml.quantity,
                   CASE am.move_type WHEN 'out_invoice' THEN  aml.quantity
                                     WHEN 'out_refund'  THEN -aml.quantity
                                     ELSE 0 END AS cantidad_neta
            FROM sale_order_line sol
            JOIN sale_order so ON so.id = sol.order_id
            JOIN product_product pp ON pp.id = sol.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            JOIN sale_order_line_invoice_rel slir ON slir.order_line_id = sol.id
            JOIN account_move_line aml ON aml.id = slir.invoice_line_id
            JOIN account_move am ON am.id = aml.move_id
            WHERE so.name = %(v)s
              AND COALESCE(pt.name->>'es_MX', pt.name->>'en_US') = %(p)s
              AND am.state = 'posted'
              AND am.move_type IN ('out_invoice', 'out_refund')
              AND (aml.display_type = 'product' OR aml.display_type IS NULL)
            ORDER BY am.invoice_date, am.id
        """, {'v': venta, 'p': producto})
        facturas = cr.fetchall()

        ts = sum(float(m[5]) for m in moves)
        tf = sum(float(f[6]) for f in facturas)
        out = [m for m in moves if m[2] == 'outgoing']
        inc = [m for m in moves if m[2] == 'incoming']

        return {
            'venta': venta, 'producto': producto,
            'movimientos': [{'move_id': m[0], 'picking': m[1], 'tipo': m[2],
                             'cantidad': float(m[3]), 'cantidad_neta': float(m[5]),
                             'fecha': str(m[4])} for m in moves],
            'facturas': [{'move_id': f[0], 'documento': f[1], 'tipo': f[2],
                          'cantidad': float(f[5]), 'cantidad_neta': float(f[6]),
                          'fecha': str(f[3]) if f[3] else '',
                          'estatus': f[4]} for f in facturas],
            'resumen': {
                'total_salidas':   round(sum(float(m[3]) for m in out), 2),
                'total_devoluc':   round(sum(float(m[3]) for m in inc), 2),
                'entrega_neta':    round(ts, 2),
                'total_facturado': round(sum(float(f[5]) for f in facturas if f[2]=='out_invoice'), 2),
                'total_nc':        round(sum(float(f[5]) for f in facturas if f[2]=='out_refund'), 2),
                'facturado_neto':  round(tf, 2),
                'diferencia':      round(ts - tf, 2),
                'cuadra':          abs(ts - tf) < 0.01,
            }
        }
