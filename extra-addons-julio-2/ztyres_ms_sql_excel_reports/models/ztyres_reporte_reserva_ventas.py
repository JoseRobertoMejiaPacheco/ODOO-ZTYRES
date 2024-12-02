from odoo import api, fields, models
import pandas as pd
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

class ReservaVentas(models.TransientModel):
    _name = 'ztyres_reporte_reserva_ventas'
    
    def get_report(self):
        fecha_actual = date.today()
        # Obtén el primer día del mes actual
        primer_dia_mes = fecha_actual.replace(day=1)
        ultimo_dia_mes = primer_dia_mes.replace(day=28)  # Establece inicialmente el día 28
        ultimo_dia_mes = ultimo_dia_mes + pd.offsets.MonthEnd(0)  # Ajusta al último día del mes
        
        desired_fields = [
            'name',
            'user_id',
            'volume_profile'
        ]
        search_domain = [
            ('type', 'in', ['contact']),  # Filtrar por contactos
            ('partner_share', 'in', True), # Solo aquellos que compartan como socio
            ('active', 'in', True),
            ('category_id', 'not in', [11, 2, 13]),
            ('user_id', 'not in', False)
        ]
        records = self.env['res.partner'].search_read(search_domain, fields=desired_fields)
        result3 = [{key: value[1] if isinstance(value, tuple) else value for key, value in record.items()} for record in records]
        df30 = pd.DataFrame(result3)
        
        df30 = df30.rename(columns={
            'name': 'cliente',
            'user_id': 'vendedor',
            'volume_profile': 'perfil'
        })
        
        df30.loc[(df30['perfil'] == 'AAA'), 'meta'] = 1000
        df30.loc[(df30['perfil'] == 'AA'), 'meta'] = 600
        df30.loc[(df30['perfil'] == 'A'), 'meta'] = 300
        df30.loc[(df30['perfil'] == 'B'), 'meta'] = 100
        df30.loc[(df30['perfil'] == 'C'), 'meta'] = 30
        df30.loc[(df30['perfil'] == 'D'), 'meta'] = 0
        
        df30.loc[(df30['vendedor'] == 'DIEGO GOMEZ'), 'zona'] = 'AGS'
        df30.loc[(df30['vendedor'] == 'Gilberto Cruz Pimentel'), 'zona'] = 'GTO'
        df30.loc[(df30['vendedor'] == 'SERGIO VILLEGAS'), 'zona'] = 'LEÓN'
        df30.loc[(df30['vendedor'] == 'OMAR BARRAZA AGUILERA'), 'zona'] = 'MICH'
        df30.loc[(df30['vendedor'] == 'RAMIRO BARRIOS MACÍAS'), 'zona'] = 'GDL'
        df30.loc[(df30['vendedor'] == 'HUMBERTO MORENO'), 'zona'] = 'PACIFICO'
                
        ####Consulta Sql Probada
        query10 = """
            SELECT DISTINCT ON (so."name")
                rp2."name" AS cliente,
                rp."name" AS vendedor,
                CASE 
			    WHEN so.state in ('sale') THEN 'Orden de venta'
			    ELSE 'Cotizaciones'
			    END as state,
                DATE(so.date_order) AS date_order,
                SUM(sol.product_uom_qty) AS "cantidad de llantas"
            FROM sale_order so
            LEFT JOIN sale_order_line sol ON so.id = sol.order_id  
            LEFT JOIN res_partner rp2 ON sol.order_partner_id = rp2.id 
            LEFT JOIN product_product pp ON sol.product_id = pp.id 
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id 
            LEFT JOIN res_users ru ON so.user_id = ru.id
            LEFT JOIN res_partner rp ON ru.partner_id = rp.id
            WHERE pt.detailed_type = 'product'
            AND sol.qty_invoiced = 0
            AND so.state not in ('cancel')
            AND so.user_id not in (31, 25)
            GROUP BY rp2."name", so."name", so.date_order, so.state, rp."name"
        """
        ##Retornar la consulta sql
        self.env.cr.execute(query10)
        result10 = self.env.cr.dictfetchall()        #Crear dataframe dla consulta
        df10 = pd.DataFrame(result10)
        #df10['date_order'] = pd.to_datetime(df10['date_order'])
        df10 = df10.loc[(df10['date_order'] >= primer_dia_mes) & (df10['date_order'] <= ultimo_dia_mes)]
        #---------------------------------------------------------------------------------------------------------------
        # Campos deseados
        desired_fields20 = [
            'partner_id',
            'move_id',
            'move_type',
            'quantity',
            'date'
        ]
        # Dominio de búsqueda, con coma entre las condiciones
        search_domain20 = [
            ('display_type', 'in', ['product']),
            ('product_type', 'in', ['product']),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('parent_state', 'in', ['posted']),
            ('move_id.date', '>=', primer_dia_mes),
            ('move_id.date', '<=', ultimo_dia_mes),
            ('move_id.invoice_user_id', 'not in', [31, 25])
        ]

        records20 = self.env['account.move.line'].search_read(search_domain20 ,fields=desired_fields20)
        
        # Mapear los datos del campo relacionado 'invoice_user_id' desde 'move_id'
        for record in records20:
            move = self.env['account.move'].browse(record['move_id'][0])
            record['invoice_user_id'] = move.invoice_user_id.name  # A
        
        result20 = [{key: value[1] if isinstance(value, tuple) else value for key, value in record.items()} for record in records20]
        df20 = pd.DataFrame(result20)
        df20 = df20.drop(columns=['id'])
        df20.loc[df20['move_type'] == 'out_refund', 'quantity'] *= -1


        df20 = df20.rename(columns={
            'partner_id': 'cliente',
            'invoice_user_id' : 'vendedor',
            'quantity': 'cantidad de llantas',
            'date': 'date_order',
            'move_type': 'state'
        })
        df20['state'] = 'Timbrado'
        
        #---------------------------------------------------------------------------------------------------------------
        df_concatenado = pd.concat([df20, df10], ignore_index=True)
        #---------------------------------------------------------------------------------------------------------------        
        
        df_concatenado['date_order'] = pd.to_datetime(df_concatenado['date_order'], errors='coerce')  # Convierte a datetime, trata errores
        df_concatenado['semana_del_año'] = df_concatenado['date_order'].dt.isocalendar().week  # Extrae la semana del año
        # Agregar "SEMANA" al inicio del número de semana
        df_concatenado['semana_del_año_str'] = "SEMANA " + df_concatenado['semana_del_año'].astype(str)  # Convertir a cadena y concatenar

        # Crear columnas separadas para día, mes y año
        df_concatenado['día'] = df_concatenado['date_order'].dt.day
        
        df_concatenado = df_concatenado.groupby(['cliente', 'vendedor', 'date_order', 'state', 'día', 'semana_del_año_str'])['cantidad de llantas'].sum().reset_index()        
        
        merged_df = pd.merge(df30, df_concatenado, on=['cliente', 'vendedor'], how='outer')
        
        new_order = ['id', 'cliente', 'perfil', 'vendedor', 'meta', 'zona', 'date_order', 'state', 'día', 'semana_del_año_str', 'cantidad de llantas']
        merged_df = merged_df[new_order]

        ##Instanciar la clase ztyres_ms_sql_excel_core que tiene el metodo para insertar un dataframe en sql server
        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(merged_df, 'reporte_reserva_ventas')
        return