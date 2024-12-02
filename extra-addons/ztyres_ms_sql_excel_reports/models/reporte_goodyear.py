from odoo import api, fields, models
import pandas as pd
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

class reporteGoodyear(models.TransientModel):
    _name = 'reporte_goodyear'

    def get_report(self):
        ####Consulta Sql Probada
        query = """
            SELECT pt.default_code AS sku_goodyear,
                CASE 
                WHEN am.move_type in ('out_refund') THEN -aml.quantity
                ELSE aml.quantity
                END as volume_vendas,
                CASE 
                WHEN am.move_type in ('out_refund') THEN -aml.price_subtotal 
                ELSE aml.price_subtotal
                END as faturamento_bruto,
                am.invoice_date AS data_faturamento,
                rp."name" AS cliente
            FROM account_move_line aml 
            JOIN account_move am ON aml.move_id = am.id
            JOIN product_product pp ON aml.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id 
            JOIN ztyres_products_tier zpt ON pt.tier_id = zpt.id 
            JOIN res_partner rp ON am.partner_id = rp.id
            WHERE aml.display_type = 'product'
            AND pt.detailed_type = 'product'
            AND am.move_type IN ('out_invoice')
            AND am.state = 'posted'    
            AND pt.manufacturer_id IN (6)
            AND rp.id NOT IN (7468, 7107, 7091, 11078, 7401, 11092)
        """
        ##Retornar la consulta sql
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()        #Crear dataframe dla consulta
        df = pd.DataFrame(result)
        
        fecha_actual = date.today()
        # Obtén el primer día del mes actual
        primer_dia_mes = fecha_actual.replace(day=1)
        ultimo_dia_mes = primer_dia_mes.replace(day=28)  # Establece inicialmente el día 28
        ultimo_dia_mes = ultimo_dia_mes + pd.offsets.MonthEnd(0)  # Ajusta al último día del mes
        
        # start_date = pd.to_datetime('2024-07-01')
        # end_date = pd.to_datetime('2024-07-31')
        
        df = df.loc[(df['data_faturamento'] >= primer_dia_mes) & (df['data_faturamento'] <= ultimo_dia_mes)]
        
        df['codigo_goodyear_distribuidor'] = 336968
        
        new_names = {
            "sku_goodyear": "sku_goodyear",
            "volume_vendas": "volume_vendas",
            "faturamento_bruto": "faturamento_bruto",
            "data_faturamento": "data_faturamento",
            "codigo_goodyear_distribuidor": "codigo_goodyear_distribuidor",	
            "cliente": "cliente"
        }
        
        ordered_columns1 = list(new_names.values())
        df = df[ordered_columns1]
        
        ##Instanciar la clase ztyres_ms_sql_excel_core que tiene el metodo para insertar un dataframe en sql server
        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(df, 'reporte_goodyear')
        return