from datetime import datetime, timedelta, date
import pandas as pd
import calendar
import pytz
from odoo import fields,models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

class Logsusuarios(models.TransientModel):
    _name = 'ztyres_pedidos_diarios'

    def get_report(self):
        ####Consulta Sql Probada
        query = """
            SELECT DISTINCT ON (so."name") 
                rp."name" AS vendedor, 
                so."name" AS pedido, 
                SUM(sol.product_uom_qty) AS total_product_qty,
                so.date_order::DATE AS date_order
            FROM sale_order so 
            JOIN res_users ru ON so.user_id = ru.id
            JOIN res_partner rp ON ru.partner_id = rp.id
            JOIN sale_order_line sol ON so.id = sol.order_id 
            GROUP BY so."name", rp."name", date_order
        """
        ##Retornar la consulta sql
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()        #Crear dataframe dla consulta
        df = pd.DataFrame(result)
        
        query2 = """
            SELECT DISTINCT ON (am."name") 
                rp."name" AS vendedor,
                am."name" AS factura, 
                SUM(aml.quantity) AS cantidad,
                am.invoice_date  AS invoice_date
            FROM account_move am 
            JOIN account_move_line aml ON aml.move_id = am.id 
            JOIN res_users ru ON am.invoice_user_id = ru.id 
            JOIN res_partner rp ON ru.partner_id = rp.id
            WHERE am.move_type = 'out_invoice'            
            AND am.state = 'posted'
            AND aml.display_type = 'product'
            GROUP BY rp."name", am."name", am.invoice_date;
        """
        ##Retornar la consulta sql
        self.env.cr.execute(query2)
        result2 = self.env.cr.dictfetchall()        #Crear dataframe dla consulta
        df2 = pd.DataFrame(result2)


        # Obtén la fecha actual
        fecha_actual = date.today()
        # Obtén el primer día del mes actual
        primer_dia_mes = pd.to_datetime(fecha_actual.replace(day=1))
        ultimo_dia_mes = primer_dia_mes.replace(day=28)  # Establece inicialmente el día 28
        ultimo_dia_mes = ultimo_dia_mes + pd.offsets.MonthEnd(0)  # Ajusta al último día del mes


        # Filtrar el DataFrame por el rango de fechas
        filtered_df = df.loc[(df['date_order'] >= primer_dia_mes) & (df['date_order'] <= ultimo_dia_mes)]
        filtered_df2 = df2.loc[(df2['invoice_date'] >= primer_dia_mes) & (df2['invoice_date'] <= ultimo_dia_mes)]
        #------------------------------------------------------------------------------------------------------#
        
        # Contar el número de pedidos por vendedor
        filtered_df3 = filtered_df.groupby(['vendedor', 'date_order']).agg({'pedido': 'count', 'total_product_qty': 'sum'}).reset_index()
        filtered_df4 = filtered_df2.groupby(['vendedor', 'invoice_date']).agg({'factura': 'count', 'cantidad': 'sum'}).reset_index()
        #------------------------------------------------------------------------------------------------------#
        
        ##Instanciar la clase ztyres_ms_sql_excel_core que tiene el metodo para insertar un dataframe en sql server
        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(filtered_df3, 'reporte_pedidos_diarios')
        reports_core.action_insert_dataframe(filtered_df4, 'reporte_facturas_diarias')
        return