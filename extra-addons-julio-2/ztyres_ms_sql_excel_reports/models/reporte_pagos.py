from odoo import api, fields, models
import pandas as pd
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import pytz

class ReservaVentas(models.TransientModel):
    _name = 'ztyres_reporte_pagos'
    
    def utc_to_local(self, date):
        local = pytz.timezone("America/Mexico_City")
        return pytz.utc.localize(date).astimezone(local).date()#,DEFAULT_SERVER_DATETIME_FORMAT

    
    def get_report(self):
        fecha_actual = date.today()
        # Obtén el primer día del mes actual
        primer_dia_mes = fecha_actual.replace(day=1)
        ultimo_dia_mes = primer_dia_mes.replace(day=28)  # Establece inicialmente el día 28
        ultimo_dia_mes = ultimo_dia_mes + pd.offsets.MonthEnd(0)  # Ajusta al último día del mes
    
        #primer_dia_mes = pd.to_datetime('2024-04-01')  # Primer día de abril de 2024
        #ultimo_dia_mes = pd.to_datetime('2024-04-30')  # Último día de abril de 2024
        
        desired_fields = [
            'name',
            'volume_rate',
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
            'volume_rate': 'perfil',
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
        
        #---------------------------------------------------------------------------------------------------------------
        ####Consulta Sql Probada
      
        query10 = """
                select 
                     rp.name as cliente,
                     rpu."name" as  cobrador,
                     apr.debit_amount_currency as amount,
                     apr.create_date AS "Fecha Aplicación"
                FROM account_partial_reconcile apr
                JOIN account_move_line aml ON aml.id = apr.credit_move_id
                JOIN account_move am ON am.id = aml.move_id
                join res_partner rp on am.partner_id = rp.id
                join res_users ru on apr.create_uid = ru.id 
                join res_partner rpu on ru.partner_id  = rpu.id  
                and am.move_type = 'entry'
                WHERE   
                apr.credit_move_id  IN (
                    SELECT aml.id FROM account_move_line aml
                    join account_move am on am.id = aml.move_id 
                    join account_account aa on aa.id = aml.account_id 
                    where aa.account_type = 'asset_receivable' 
                )  
        """
        self.env.cr.execute(query10)
        result10 = self.env.cr.dictfetchall()        #Crear dataframe de la consulta
        df10 = pd.DataFrame(result10)
        # Convertir las fechas a la zona horaria local
        df10['date_order_local'] = df10['Fecha Aplicación'].apply(self.utc_to_local)
        
        df10 = df10.loc[(df10['date_order_local'] >= primer_dia_mes) & (df10['date_order_local'] <= ultimo_dia_mes)]
        
        #---------------------------------------------------------------------------------------------------------------
  
        
        df10['date_order_local'] = pd.to_datetime(df10['date_order_local'], errors='coerce')  # Convierte a datetime, trata errores
        df10['semana_del_año'] = df10['date_order_local'].dt.isocalendar().week  # Extrae la semana del año
        # Agregar "SEMANA" al inicio del número de semana
        df10['semana_del_año_str'] = "SEMANA " + df10['semana_del_año'].astype(str)  # Convertir a cadena y concatenar

        # Crear columnas separadas para día, mes y año
        df10['día'] = df10['date_order_local'].dt.day
        
        #df10 = df10.groupby(['cliente', 'cobrador', 'date_order_local', 'día', 'semana_del_año_str'])['amount'].sum().reset_index()        
        
        merged_df = pd.merge(df30, df10, on='cliente', how='outer')
        
        colum_selec = merged_df[['cliente', 'perfil', 'vendedor', 'Meta', 'Zona', 'cobrador', 'amount', 'date_order_local', 'día', 'semana_del_año_str']]
        
        ##Instanciar la clase ztyres_ms_sql_excel_core que tiene el metodo para insertar un dataframe en sql server
        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(colum_selec, 'reporte_pagos')
        return