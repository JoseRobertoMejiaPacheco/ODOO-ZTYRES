from odoo import api, fields, models
import math
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

class MyModel(models.TransientModel):
    _name = 'reporte_codigos_no_comprados'

    def get_qty(self,product_tmpl_id):
        domain = [('product_tmpl_id', 'in', [product_tmpl_id])]
        pp = self.env['product.product'].search(domain)
        free_qty = pp.free_qty
        return max(0, free_qty)

    def get_all_products(self):
        desired_fields = [
            'id',
            'default_code',
            'name',
            'tire_measure_id',
            'model_id',
            'brand_id',
            'manufacturer_id',
            'segment_id',
            'tier_id',
            'qty_available'
        ]

        records = self.env['product.template'].search_read([('detailed_type', 'in', ['product'])], fields=desired_fields)
        # Extraer solo los valores de las tuplas
        result = [{key: value[1] if isinstance(value, tuple) else value for key, value in record.items()} for record in records]
        df = pd.DataFrame(result)

        query = """
            SELECT pt.id AS id, 
                   am.invoice_date AS invoice_date
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
            JOIN product_product pp ON aml.product_id = pp.id  
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            WHERE pt.detailed_type IN ('product')
            AND am.move_type IN ('in_invoice')   
            AND pt.active = true
        """
        self.env.cr.execute(query)
        result2 = self.env.cr.dictfetchall()        #Crear dataframe de la consulta
        df2 = pd.DataFrame(result2)
        
        # Obtener la fecha actual
        fecha_actual = date.today()
        fecha_5_meses_atras = fecha_actual - pd.DateOffset(months=5)
        primer_dia_5_meses_atras = pd.to_datetime(fecha_5_meses_atras.replace(day=1))
        ultimo_dia_mes_actual = pd.to_datetime(fecha_actual.replace(day=1)) + pd.offsets.MonthEnd(0)
        
        df2 = df2.loc[(df2['invoice_date'] >= primer_dia_5_meses_atras) & (df2['invoice_date'] <= ultimo_dia_mes_actual)]
        df2.drop(columns=['invoice_date'])
        
        ids_a_eliminar = df2['id'].tolist()
        
        df_filtrado = df[~df['id'].isin(ids_a_eliminar)]
        
        query3 = """
        SELECT pp.product_tmpl_id AS id,
               SUM(pol.product_qty - pol.qty_received) AS BO
        FROM purchase_order_line pol
        JOIN product_product AS pp ON pol.product_id = pp.id
        JOIN purchase_order po ON pol.order_id = po.id
        WHERE po.state IN ('purchase') 
        AND po.invoice_status NOT IN ('cancel') 
        AND (pol.product_qty - pol.qty_received) > 0
        GROUP BY pp.product_tmpl_id;
        """
        self.env.cr.execute(query3)
        result3 = self.env.cr.dictfetchall()        #Crear dataframe de la consulta
        df3 = pd.DataFrame(result3)
        
        query4 = """
        SELECT  
            pp.product_tmpl_id as id,
            SUM(sq.quantity) AS transito 
        FROM stock_quant sq
        JOIN product_product AS pp ON sq.product_id = pp.id
        WHERE location_id in (53, 24686, 24687) 
        GROUP BY pp.product_tmpl_id
        """
        self.env.cr.execute(query4)
        result4 = self.env.cr.dictfetchall()        #Crear dataframe de la consulta
        df4 = pd.DataFrame(result4)

        merged_df = pd.merge(df_filtrado, df3,  on='id', how='left')
        merged_df2 = pd.merge(merged_df, df4,  on='id', how='left')

        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(merged_df2, 'reporte_codigos_no_comprados')

        return 