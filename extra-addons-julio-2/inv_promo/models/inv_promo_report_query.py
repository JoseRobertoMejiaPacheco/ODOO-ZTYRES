from odoo import models, fields, api
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

class InvPromo(models.TransientModel):
    _inherit = 'inv_promo.report'
    _description = 'inv_promo.inv_promo'

    def insert_data(self):
        cr = self.env.cr  # Obtén el cursor de la base de datos
        query = self._table_query()  # Construye la consulta SQL
        cr.execute(query)  # Ejecuta la consulta SQL con parámetros
        return self.create(cr.dictfetchall())
        
    # Definir la función _table_query
    def _table_query(self):
        query = '%s %s %s %s' % (self._select(), 
                                        #_get_active_pricelist(),
                                        self._from(),
                                        self._join(),
                                        self._group_by())  
        return query


    def _get_active_pricelist(self):
        query = ''
        PPIDS = [(1, 'mayoreo'), (113, 'promocion')]        
        for id, name in PPIDS:
            query += self._get_price_sql(id, name)
        # Eliminar la última coma si está presente en la cadena
        if ',' in query:
            query = query[:query.rfind(',')]
        return query
            
        
    def _select(self):
        return '''
    SELECT 
        pt.id AS product_id,
        pt.default_code,
        pt.tire_measure_id, 
        pt.layer_id, 
        pt.speed_id, 
        pt.index_of_load_id,
        pt.model_id, 
        pt.brand_id,
        pt.tier_id,
        sum(tr.transit) AS transit,
        tr.fecha as fecha,
        sum(sq.available) AS available,
        sum(bo.purchase_backorder) AS backorder
    '''
        
        
    def _get_price_sql(self,id,name):
        return '''(
        SELECT fixed_price
        FROM product_pricelist_item ppi
        WHERE ppi.product_tmpl_id = pp.product_tmpl_id
        AND ppi.pricelist_id = %s 
        LIMIT 1
    ) AS %s,
        '''%(id,name)
 
    def _from(self):
        return '''FROM product_product pp'''

        
    def _join(self):
        return '''
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            LEFT JOIN (
                SELECT 
                    sq.product_id, 
                    SUM(sq.quantity - sq.reserved_quantity) AS available
                FROM 
                    stock_quant sq
                JOIN 
                    stock_location sl ON sq.location_id = sl.id
                WHERE 
                    sl.usage = 'internal'
                GROUP BY 
                    sq.product_id
            ) sq ON sq.product_id = pp.id
            LEFT JOIN (
                WITH latest_purchase_dates AS (
                    SELECT  
                        pp.id AS id,
                        MAX(po.date_planned) AS latest_date
                    FROM stock_quant sq
                    JOIN product_product pp ON sq.product_id = pp.id
                    JOIN purchase_order_line pol ON pp.id = pol.product_id 
                    JOIN purchase_order po ON pol.order_id = po.id
                    WHERE sq.location_id IN (53, 24686, 24687) 
                    AND po.state = 'purchase'
                    GROUP BY pp.id
                )
                SELECT 
                    pp.id AS product_id,
                    SUM(sq.quantity) AS transit,
                    DATE(lpd.latest_date + INTERVAL '10 days') AS fecha
                FROM stock_quant sq
                JOIN product_product pp ON sq.product_id = pp.id
                JOIN latest_purchase_dates lpd ON pp.id = lpd.id
                WHERE sq.location_id IN (53, 24686, 24687) 
                GROUP BY pp.id, lpd.latest_date
                ORDER BY pp.id
            ) tr ON tr.product_id = pp.id
            LEFT JOIN (
                SELECT 
                    pp.id as id,
                    SUM(pol.product_qty - pol.qty_received) as purchase_backorder 
                FROM 
                    purchase_order_line pol
                JOIN 
                    product_product AS pp ON pol.product_id = pp.id
                JOIN 
                    purchase_order po ON pol.order_id = po.id
                WHERE 
                    po.state IN ('purchase') AND
                    po.invoice_status NOT IN ('cancel') AND
                    (pol.product_qty - pol.qty_received) > 0 
                GROUP BY pp.id
            ) bo on bo.id = pp.id
            WHERE NOT (sq.available = 0 AND tr.transit = 0)'''

        
    def _group_by(self):
        return '''
    GROUP BY 
        pt.id, 
        pt.default_code,
        pt.tire_measure_id,
        pt.layer_id,
        pt.speed_id,
        pt.index_of_load_id,
        pt.model_id,
        pt.brand_id,
        pt.tier_id,
        sq.available,
        tr.transit,
        tr.fecha,
        bo.purchase_backorder
    ORDER BY 
        pt.tire_measure_id ASC'''