from odoo import api, fields, models
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta

class Logsusuarios(models.TransientModel):
    _name = 'ztyres_reporte_usuarios'

    def get_report(self):
        ####Consulta Sql Probada
        query = """
        select rp2."name" AS cliente, 
        	   rcs."name" AS estado, 
        	   rc."name"->>'es_MX' AS ciudad, 
        	   rp."name" AS usuario, 
               so."name" AS pedido, 
        	   sovl.visit_count as visitas, 
        	   sovl.create_date, 
        	   sovl.visit_date 
        FROM sale_order_visit_log sovl 
        JOIN res_users ru ON sovl.user_id = ru.id 
        JOIN res_partner rp ON ru.partner_id  = rp.id
        JOIN sale_order so ON sovl.order_id = so.id
        JOIN res_partner rp2 ON so.partner_id = rp2.id
        JOIN res_country_state rcs ON rp2.state_id = rcs.id
        JOIN res_city rc ON rp2.city_id = rc.id 
        WHERE sovl.user_id NOT IN (1, 2)
        """
        ##Retornar la consulta sql
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()        #Crear dataframe dla consulta
        df = pd.DataFrame(result)
        
        pivot_df = df.pivot_table(index=['pedido', 'cliente', 'estado', 'ciudad'], columns='usuario', values='visitas', aggfunc='sum', fill_value=0)
        pivot_df.reset_index(inplace=True)
        
        ##Instanciar la clase ztyres_ms_sql_excel_core que tiene el metodo para insertar un dataframe en sql server
        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(pivot_df, 'reporte_usuarios')
        return