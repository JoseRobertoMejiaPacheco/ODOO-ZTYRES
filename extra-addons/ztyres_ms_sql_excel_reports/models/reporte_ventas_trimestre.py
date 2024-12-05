from odoo import api, fields, models
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class Logsusuarios(models.TransientModel):
    _name = 'reporte_ventas_trimestre'

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
        
        # Obtener la fecha de hoy
        hoy = datetime.today()
        # Calcular el primer día del trimestre hace tres meses
        primer_dia_trimestre = (hoy - pd.DateOffset(months=3)).date()

        # Filtrar por los últimos tres meses
        df_filtrado = df[df['fecha'] >= primer_dia_trimestre]
        df_filtrado = df_filtrado.drop(columns=['fecha'])
        
        df_filtrado2 = df_filtrado.groupby(['cliente', 'vendedor', 'tier', 'medida'])['cantidad'].sum().reset_index()
        
        top_20_por_tier = (df_filtrado.groupby(['tier', 'medida'])['cantidad'].sum().groupby('tier', group_keys=False).apply(lambda x: x.nlargest(60)).reset_index())
        
        pivot_df = top_20_por_tier.pivot_table(index='medida', columns='tier', values='cantidad', aggfunc='sum')
        pivot_df = pivot_df.fillna(0)
        pivot_df.reset_index(inplace=True)
        
        ##Instanciar la clase ztyres_ms_sql_excel_core que tiene el metodo para insertar un dataframe en sql server
        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(df_filtrado2, 'ventas_trimestre')
        reports_core.action_insert_dataframe(pivot_df, 'top60')
        return