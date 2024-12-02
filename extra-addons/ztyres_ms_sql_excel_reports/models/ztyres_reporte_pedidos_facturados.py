from odoo import api, fields, models
import pandas as pd
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

class PedidosFacturados(models.TransientModel):
    _name = 'ztyres_reporte_pedidos_facturados'
    
    def get_report(self):
        
        desired_fields = [
            'name',
            'volume_profile',
            'user_id'
        ]
        search_domain = [
            ('type', 'in', ['contact']),  # Filtrar por contactos
            ('partner_share', 'in', True)  # Solo aquellos que compartan como socio
        ]
        records = self.env['res.partner'].search_read(search_domain, fields=desired_fields)
        result3 = [{key: value[1] if isinstance(value, tuple) else value for key, value in record.items()} for record in records]
        df30 = pd.DataFrame(result3)
        
        df30 = df30.rename(columns={
            'name': 'cliente',
            'volume_profile': 'perfil',
            'user_id': 'vendedor'
        })
        
        df30.loc[(df30['perfil'] == 'AAA'), 'Meta'] = 1000
        df30.loc[(df30['perfil'] == 'AA'), 'Meta'] = 600
        df30.loc[(df30['perfil'] == 'A'), 'Meta'] = 300
        df30.loc[(df30['perfil'] == 'B'), 'Meta'] = 100
        df30.loc[(df30['perfil'] == 'C'), 'Meta'] = 30
        df30.loc[(df30['perfil'] == 'D'), 'Meta'] = 0
        
        df30.loc[(df30['vendedor'] == 'DIEGO GOMEZ'), 'Zona'] = 'AGS'
        df30.loc[(df30['vendedor'] == 'Gilberto Cruz Pimentel'), 'Zona'] = 'GTO'
        df30.loc[(df30['vendedor'] == 'SERGIO VILLEGAS'), 'Zona'] = 'LEÓN'
        df30.loc[(df30['vendedor'] == 'OMAR BARRAZA AGUILERA'), 'Zona'] = 'MICH'
        df30.loc[(df30['vendedor'] == 'RAMIRO BARRIOS MACÍAS'), 'Zona'] = 'GDL'
        df30.loc[(df30['vendedor'] == 'HUMBERTO MORENO'), 'Zona'] = 'PACIFICO'
        
        ####Consulta Sql Probada
        query = """
            SELECT 
            	rp2."name" AS cliente,
                so."name" AS pedido, 
                DATE(so.date_order) AS date_order,
                CASE 
                	WHEN DATE(so.date_order AT TIME ZONE 'America/Mexico_City') = CURRENT_DATE 
                    THEN 0
                ELSE DATE_PART('day', CURRENT_DATE - so.date_order AT TIME ZONE 'America/Mexico_City')
                END AS "Dias trascurridos",
                CASE 
           			WHEN so.state = 'sale' THEN 'Orden de Venta' 
           		ELSE 'Otro'
       			END AS "Estatus",
                CASE 
           			WHEN so.invoice_status in ('invoiced') THEN 'Facturado' 
           			WHEN so.invoice_status in ('no') and SUM(sol.qty_invoiced) != 0 THEN 'Facturado'
           		ELSE 'Orden de Venta'
           		END AS "Estatus Factura",
           		zpb."name" AS marca,
                CASE 
           			WHEN so.invoice_status in ('invoiced') THEN SUM(sol.qty_invoiced) 
           			WHEN so.invoice_status in ('no') and SUM(sol.qty_invoiced) != 0 THEN SUM(sol.qty_invoiced)
           		ELSE SUM(sol.product_uom_qty)
           		END AS "cantidad de llantas"
            FROM sale_order so 
            JOIN res_users ru ON so.user_id = ru.id
            JOIN res_partner rp ON ru.partner_id = rp.id
            JOIN sale_order_line sol ON so.id = sol.order_id 
            JOIN res_partner rp2 ON sol.order_partner_id = rp2.id
            JOIN product_product pp ON sol.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id 
            JOIN ztyres_products_brand zpb on pt.brand_id = zpb.id
            WHERE pt.detailed_type IN ('product')
            GROUP BY rp2."name", so."name", rp."name", so.date_order, so.invoice_status, so.state, zpb."name"
        """
        ##Retornar la consulta sql
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()        #Crear dataframe dla consulta
        df = pd.DataFrame(result)
        #---------------------------------------------------------------------------------------------------------------
        #---------------------------------------------------------------------------------------------------------------
        fecha_actual = date.today()
        # Obtén el primer día del mes actual
        primer_dia_mes = fecha_actual.replace(day=1)
        ultimo_dia_mes = primer_dia_mes.replace(day=28)  # Establece inicialmente el día 28
        ultimo_dia_mes = ultimo_dia_mes + pd.offsets.MonthEnd(0)  # Ajusta al último día del mes
        
        df = df.loc[(df['date_order'] >= primer_dia_mes) & (df['date_order'] <= ultimo_dia_mes)]
        
        df['date_order'] = pd.to_datetime(df['date_order'], errors='coerce')  # Convierte a datetime, trata errores
        df['semana_del_año'] = df['date_order'].dt.isocalendar().week  # Extrae la semana del año
        # Agregar "SEMANA" al inicio del número de semana
        df['semana_del_año_str'] = "SEMANA " + df['semana_del_año'].astype(str)  # Convertir a cadena y concatenar

        # Crear columnas separadas para día, mes y año
        df['día'] = df['date_order'].dt.day
        
        df = df.loc[(df['Estatus'] == 'Orden de Venta')]
        df = df.drop(columns=['pedido', 'Dias trascurridos'])
        
        grouped_df = df.groupby(['cliente', 'date_order', 'Estatus Factura', 'día', 'semana_del_año_str', 'marca'])['cantidad de llantas'].sum().reset_index()        
        
        merged_df = pd.merge(grouped_df, df30, on='cliente', how='left')
        
        ##Instanciar la clase ztyres_ms_sql_excel_core que tiene el metodo para insertar un dataframe en sql server
        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(merged_df, 'reporte_pedidos_facturados')
        return