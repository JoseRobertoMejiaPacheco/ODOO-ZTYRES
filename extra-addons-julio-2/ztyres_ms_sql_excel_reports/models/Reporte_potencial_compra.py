from odoo import api, fields, models
import pandas as pd
import pytz
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

class PotencialCompra(models.TransientModel):
    _name = 'reporte_potencial_compra'
        
    def get_report(self):
        ####Consulta Sql Probada
        query = """
                SELECT 	
                    rp_customer.x_studio_grupo AS grupo,
                    rp_customer."name" as cliente, 
                    rp_salesperson."name" as vendedor,
                    aml."name", 
                    CASE 
                        WHEN am.move_type in ('out_refund') THEN -aml.quantity
                        ELSE aml.quantity
                    END as cantidad,
                    aml."date" AS fecha
                FROM account_move_line aml 
                JOIN account_move am ON aml.move_id = am.id 
                JOIN product_product pp ON aml.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id 
                JOIN res_partner rp_customer ON aml.partner_id = rp_customer.id
                JOIN res_users ru ON rp_customer.user_id = ru.id
                LEFT JOIN res_partner rp_salesperson ON ru.partner_id = rp_salesperson.id
                WHERE am.move_type IN ('out_invoice', 'out_refund')            
                AND am.state = 'posted'
                AND aml.display_type = 'product'
                AND pt.detailed_type = 'product'
                GROUP BY rp_customer.x_studio_grupo, rp_customer.name, aml."name", am.move_type, 
                        aml.quantity, aml.date, rp_salesperson."name"
        """
        ##Retornar la consulta sql
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()        #Crear dataframe dla consulta
        df = pd.DataFrame(result)
        df['fecha'] = pd.to_datetime(df['fecha'])
        df['año'] = df['fecha'].dt.year
        df['mes'] = df['fecha'].dt.month
        df = df.fillna('')
        
        query2 = """
            SELECT 
             	rp_customer."name" as cliente, 
                CASE 
                    WHEN am.move_type in ('out_refund') THEN -aml.quantity
                    ELSE aml.quantity
                END AS piezasxmes,
                aml."date" AS date_order
            FROM account_move_line aml 
            JOIN account_move am ON aml.move_id = am.id 
            JOIN product_product pp ON aml.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id 
            JOIN res_users ru ON am.invoice_user_id = ru.id  
            JOIN res_partner rp_customer ON aml.partner_id = rp_customer.id 
            JOIN res_partner rp_salesperson ON ru.partner_id = rp_salesperson.id  -- Unión para obtener el vendedor
            WHERE am.move_type IN ('out_invoice', 'out_refund')            
            AND am.state = 'posted'
            AND aml.display_type = 'product'
            AND pt.detailed_type = 'product'
        """
        self.env.cr.execute(query2)
        result2 = self.env.cr.dictfetchall()        #Crear dataframe dla consulta
        df2 = pd.DataFrame(result2)
        
        fecha_actual = date.today()
        # Obtén el primer día del mes actual
        primer_dia_mes = fecha_actual.replace(day=1)
        ultimo_dia_mes = primer_dia_mes.replace(day=28)  # Establece inicialmente el día 28
        ultimo_dia_mes = ultimo_dia_mes + pd.offsets.MonthEnd(0)  # Ajusta al último día del mes


        # Filtrar el DataFrame por el rango de fechas
        df2 = df2.loc[(df2['date_order'] >= primer_dia_mes) & (df2['date_order'] <= ultimo_dia_mes)]
        df2 = df2.drop(columns=['date_order'])
        
        
        pivot_df3 = df2.pivot_table(index='cliente', values='piezasxmes', aggfunc='sum', fill_value=0)
        
        # Utilizar pivot_table para crear una columna por cada año diferente
        pivot_df = df.pivot_table(index=['grupo','cliente', 'vendedor'], columns='año', values='cantidad', aggfunc='sum', fill_value=0)
        pivot_df.reset_index(inplace=True)
        pivot_df.columns.name = None
        pivot_df.drop(columns=[2020], inplace=True)

        # Calcular la cantidad de meses con al menos una compra por cliente y año
        compras_por_mes_df = df.groupby(['cliente', 'año', 'mes'])['cantidad'].apply(lambda x: 1 if x.sum() > 0 else 0).reset_index(name='mes_con_compra')
  
        # Utiliza pivot_table para crear una tabla pivote sumando 'mes_con_compra' por 'cliente' y 'año'
        pivot_df2 = compras_por_mes_df.pivot_table(index='cliente', columns='año', values='mes_con_compra', aggfunc='sum', fill_value=0)
        pivot_df2.reset_index(inplace=True)
        pivot_df2.columns.name = None
        pivot_df2.drop(columns=[2020], inplace=True)
        
        merged_df = pd.merge(pivot_df, pivot_df2, on='cliente', suffixes=('_Ven', '_Com'), how='left')
        
        merged_df2 = pd.merge(merged_df, pivot_df3, on='cliente', how='left')

        ##Instanciar la clase ztyres_ms_sql_excel_core que tiene el metodo para insertar un dataframe en sql server
        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(merged_df2, 'reporte_potencial_compra')
        return