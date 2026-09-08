# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools
from odoo.exceptions import AccessError


class DashboardReservas(models.Model):
    _name = 'dashboard.reservas'
    _description = 'Dashboard Antigüedad de Reservas'
    _auto = False  # Vista SQL, no crea tabla
    _order = 'dias_reservada desc'

    # Campos del resultado
    codigo = fields.Char(string='Código', readonly=True)
    producto = fields.Char(string='Producto', readonly=True)
    marca = fields.Char(string='Marca', readonly=True)
    precio = fields.Float(string='Precio', readonly=True)
    picking = fields.Char(string='Transferencia', readonly=True)
    pedido_venta = fields.Char(string='Pedido de Venta', readonly=True)
    cliente = fields.Char(string='Cliente', readonly=True)
    vendedor = fields.Char(string='Vendedor', readonly=True)
    vendedor_uid = fields.Integer(string='UID Vendedor', readonly=True)
    cantidad_solicitada = fields.Float(string='Cantidad Solicitada', readonly=True)
    fecha_programada = fields.Datetime(string='Fecha Programada', readonly=True)
    fecha_reserva_aprox = fields.Datetime(string='Fecha Reserva Aprox.', readonly=True)
    dias_reservada = fields.Integer(string='Días Reservada', readonly=True)
    estado = fields.Char(string='Estado', readonly=True)

    def init(self):
        """Inicializa la vista SQL."""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW dashboard_reservas AS (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY (CURRENT_DATE - DATE(MAX(sm.date))) DESC) AS id,
                    pp.default_code                         AS codigo,
                    pt.name->>'es_MX'                       AS producto,
                    rb.name                                 AS marca,
                    sol.price_unit * SUM(sm.product_uom_qty) AS precio,
                    sp.name                                 AS picking,
                    so.name                                 AS pedido_venta,
                    rp.name                                 AS cliente,
                    rp_user.name                            AS vendedor,
                    ru.id                                   AS vendedor_uid,
                    SUM(sm.product_uom_qty)                 AS cantidad_solicitada,
                    sp.scheduled_date                       AS fecha_programada,
                    MAX(sm.date)                            AS fecha_reserva_aprox,
                    (CURRENT_DATE - DATE(MAX(sm.date)))     AS dias_reservada,
                    sp.state                                AS estado
                FROM stock_picking sp
                JOIN stock_picking_type spt
                    ON spt.id = sp.picking_type_id
                JOIN stock_move sm
                    ON sm.picking_id = sp.id
                JOIN product_product pp
                    ON pp.id = sm.product_id
                JOIN product_template pt
                    ON pt.id = pp.product_tmpl_id
                LEFT JOIN ztyres_products_brand rb
                    ON rb.id = pt.brand_id
                LEFT JOIN sale_order_line sol
                    ON sol.id = sm.sale_line_id
                LEFT JOIN sale_order so
                    ON so.name = sp.origin
                LEFT JOIN res_partner rp
                    ON rp.id = so.partner_id
                LEFT JOIN res_users ru
                    ON ru.id = so.user_id
                LEFT JOIN res_partner rp_user
                    ON rp_user.id = ru.partner_id
                LEFT JOIN stock_location sl_src
                    ON sl_src.id = sp.location_id
                LEFT JOIN stock_location sl_dest
                    ON sl_dest.id = sp.location_dest_id
                WHERE sp.state = 'assigned'
                  AND spt.code = 'outgoing'
                  AND sl_src.usage = 'internal'
                  AND sl_dest.usage = 'customer'
                GROUP BY
                    pp.default_code,
                    pt.name,
                    rb.name,
                    sol.price_unit,
                    sp.name,
                    so.name,
                    rp.name,
                    rp_user.name,
                    ru.id,
                    sp.scheduled_date,
                    sp.state
            )
        """)

    @api.model
    def _get_domain_filter(self):
        """
        Retorna el domain según el usuario actual.
        - Administradores y usuarios con grupo 'Ver Todos' ven todo.
        - Vendedores solo ven sus propios registros.
        """
        if (self.env.user.has_group('dashboard_reservas.group_dashboard_reservas_manager')
                or self.env.user._is_admin()):
            return []
        return [('vendedor_uid', '=', self.env.uid)]

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Inyecta automáticamente el filtro de vendedor."""
        domain = list(domain or []) + self._get_domain_filter()
        return super().search_read(domain=domain, fields=fields, offset=offset,
                                   limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = list(domain or []) + self._get_domain_filter()
        return super().read_group(domain, fields, groupby, offset=offset,
                                  limit=limit, orderby=orderby, lazy=lazy)

    def get_dashboard_data(self):
        """
        Método llamado desde JS para obtener los datos del dashboard
        incluyendo estadísticas resumidas.
        """
        domain = self._get_domain_filter()
        records = self.search_read(
            domain=domain,
            fields=['codigo', 'producto', 'marca', 'precio', 'picking', 'pedido_venta', 'cliente',
                    'vendedor', 'cantidad_solicitada', 'fecha_programada',
                    'fecha_reserva_aprox', 'dias_reservada', 'estado'],
            order='dias_reservada desc'
        )

        # Estadísticas resumidas
        total = len(records)
        criticos = sum(1 for r in records if r['dias_reservada'] and r['dias_reservada'] >= 30)
        alerta = sum(1 for r in records if r['dias_reservada'] and 15 <= r['dias_reservada'] < 30)
        normales = sum(1 for r in records if r['dias_reservada'] and r['dias_reservada'] < 15)
        max_dias = max((r['dias_reservada'] or 0 for r in records), default=0)

        return {
            'records': records,
            'stats': {
                'total': total,
                'criticos': criticos,
                'alerta': alerta,
                'normales': normales,
                'max_dias': max_dias,
            },
            'is_manager': self.env.user.has_group(
                'dashboard_reservas.group_dashboard_reservas_manager'
            ) or self.env.user._is_admin(),
        }
