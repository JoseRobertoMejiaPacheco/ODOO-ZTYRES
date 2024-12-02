from odoo import api, fields, models
import pandas as pd
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

class Logsusuarios(models.TransientModel):
    _name = 'reporte_porcentaje_ventas'

    def get_report(self):
        ####Consulta Sql Probada
        query = """
              SELECT 
                zptm."name" AS medida,
                zpt."name" AS tier,
                CASE 
                    WHEN am.move_type in ('out_refund') THEN -aml.quantity
                    ELSE aml.quantity
                END as cantidad,
                rp_customer."name" as cliente, 
                rp_salesperson."name" as vendedor,
                am.invoice_date as fecha
            FROM account_move_line aml 
            JOIN account_move am ON aml.move_id = am.id 
            JOIN product_product pp ON aml.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id 
            JOIN res_users ru ON am.invoice_user_id = ru.id  
            JOIN res_partner rp_customer ON aml.partner_id = rp_customer.id 
            JOIN res_partner rp_salesperson ON ru.partner_id = rp_salesperson.id  -- Unión para obtener el vendedor
            JOIN ztyres_products_tier zpt ON pt.tier_id = zpt.id 
            JOIN ztyres_products_tire_measure zptm ON pt.tire_measure_id = zptm.id  
            WHERE am.move_type IN ('out_invoice', 'out_refund')            
            AND am.state = 'posted'
            AND aml.display_type = 'product'
            AND pt.detailed_type = 'product'
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
        primer_dia_mes = pd.to_datetime('2022-01-01')  # Primer día de abril de 2024
        df['fecha'] = pd.to_datetime(df['fecha'])
        df_filtrado = df.loc[(df['fecha'] >= primer_dia_mes) & (df['fecha'] <= ultimo_dia_mes)]
        df_filtrado["Año"] = df_filtrado["fecha"].dt.isocalendar().year  # Extrae el año
        
        df_filtrado2 = df_filtrado.groupby(['cliente', 'vendedor', 'Año'])['cantidad'].sum().reset_index()

        
        ##Instanciar la clase ztyres_ms_sql_excel_core que tiene el metodo para insertar un dataframe en sql server
        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(df_filtrado2, 'porcentaje_ventas')
        return