import io
import openpyxl
from openpyxl.styles import Font, PatternFill
from odoo.http import request, Response
from datetime import date
import calendar
import pandas as pd
from odoo import api, fields, models
from odoo.addons.inv_promo.wizard.models.lista_de_precios import codes, codes2, codes3

class ReporteVentas(models.TransientModel):
    _name = 'reporte_ventas'

    def get_report(self):
        fecha_actual = date.today()
        # Obtén el primer día del mes actual
        primer_dia_mes = fecha_actual.replace(day=1)
        ultimo_dia_mes = primer_dia_mes.replace(day=28)  # Establece inicialmente el día 28
        ultimo_dia_mes = ultimo_dia_mes + pd.offsets.MonthEnd(0)  # Ajusta al último día del mes
        lista = []

        query = """
            SELECT rp."name" AS vendedor, 
                zpb."name" AS marca, 
                zpt."name" AS tier, 
                SUM(CASE
                WHEN am.move_type IN ('out_refund') THEN -aml.quantity
                ELSE aml.quantity
                END) AS cantidad
            FROM account_move_line aml 
            LEFT JOIN account_move am ON aml.move_id = am.id 
            LEFT JOIN product_product pp ON aml.product_id = pp.id
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id 
            LEFT JOIN res_users ru ON am.invoice_user_id = ru.id
            LEFT JOIN res_partner rp ON ru.partner_id = rp.id
            LEFT JOIN ztyres_products_tier zpt ON pt.tier_id = zpt.id
            LEFT JOIN ztyres_products_brand zpb ON pt.brand_id = zpb.id
            WHERE am.invoice_date BETWEEN %s AND %s
            AND am.state IN ('posted')
            AND am.move_type IN ('out_invoice', 'out_refund')
            AND pt.detailed_type IN ('product')
            AND aml.display_type IN ('product')
            AND ru.id NOT IN (31, 78, 54, 89)
            GROUP BY rp."name", zpb."name", zpt."name"
            ORDER BY rp."name", zpb."name"
            """
        ##Retornar la consulta sql
        self.env.cr.execute(query, (primer_dia_mes, ultimo_dia_mes))
        result = self.env.cr.dictfetchall() 
        df = pd.DataFrame(result)
        
        # Inicializar pivot_df como un DataFrame vacío si no hay resultados
        if df.empty:
            pivot_df = pd.DataFrame(columns=['marca', 'vendedor', 'cantidad'])  # Define las columnas esperadas
            pivot_df2 = pd.DataFrame(columns=['tier', 'vendedor', 'cantidad'])  # Define las columnas esperadas
            lista.append(('Ventas por Marca', pivot_df))
            lista.append(('ventas por tier', pivot_df2))
        else:
            # Crear el pivot_df usando los resultados
            pivot_df = df.pivot_table(index='marca', columns='vendedor', values='cantidad', aggfunc='sum', fill_value=0)
            pivot_df.reset_index(inplace=True)
            pivot_df2 = df.pivot_table(index='tier', columns='vendedor', values='cantidad', aggfunc='sum', fill_value=0)
            pivot_df2.reset_index(inplace=True)
            lista.append(('Ventas por Marca', pivot_df))
            lista.append(('ventas por tier', pivot_df2))

        codes_tuple = tuple(codes)
        codes_tuple2 = tuple(codes2)
        codes_tuple3 = tuple(codes3)
        codes_combined = codes_tuple + codes_tuple2 + codes_tuple3
        
        query3 = """
            select
                pt.id AS id,
            	aml."name" AS producto,
            	rp."name" AS vendedor, 
                SUM(CASE
                WHEN am.move_type IN ('out_refund') THEN -aml.quantity
                ELSE aml.quantity
                END) AS cantidad
            FROM account_move_line aml 
            LEFT JOIN account_move am ON aml.move_id = am.id 
            LEFT JOIN product_product pp ON aml.product_id = pp.id
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id 
            LEFT JOIN res_users ru ON am.invoice_user_id = ru.id
            LEFT JOIN res_partner rp ON ru.partner_id = rp.id
            WHERE am.invoice_date BETWEEN %s AND %s
            AND am.state IN ('posted')
            AND am.move_type IN ('out_invoice', 'out_refund')
            AND pt.detailed_type IN ('product')
            AND aml.display_type IN ('product')
            AND ru.id NOT IN (31, 78, 54, 89)
            AND pt.id IN %s
            GROUP BY rp."name", aml."name", pt.id
            ORDER BY rp."name"
            """
        ##Retornar la consulta sql
        self.env.cr.execute(query3, (primer_dia_mes, ultimo_dia_mes, codes_combined))
        result3 = self.env.cr.dictfetchall() 
        df3 = pd.DataFrame(result3)
        
        # Inicializar pivot_df como un DataFrame vacío si no hay resultados
        if df3.empty:
            pivot_df3 = pd.DataFrame(columns=['producto', 'vendedor', 'cantidad']) 
            pivot_df5 = pd.DataFrame(columns=['producto', 'vendedor', 'cantidad']) 
            pivot_df6 = pd.DataFrame(columns=['producto', 'vendedor', 'cantidad']) 
            lista.append(('Promo del mes', pivot_df3))
            lista.append(('Promo Bridgestone', pivot_df5))
            lista.append(('Promo T4-Plus', pivot_df6))
        else:
            pivot_df3 = df3[df3['id'].isin(codes_tuple2)]
            pivot_df3 = pivot_df3.pivot_table(index='producto', columns='vendedor', values='cantidad', aggfunc='sum', fill_value=0)
            pivot_df3.reset_index(inplace=True)
            
            pivot_df5 = df3[df3['id'].isin(codes_tuple)]
            pivot_df5 = pivot_df5.pivot_table(index='producto', columns='vendedor', values='cantidad', aggfunc='sum', fill_value=0)
            pivot_df5.reset_index(inplace=True)
            
            pivot_df6 = df3[df3['id'].isin(codes_tuple3)]
            pivot_df6 = pivot_df6.pivot_table(index='producto', columns='vendedor', values='cantidad', aggfunc='sum', fill_value=0)
            pivot_df6.reset_index(inplace=True)
            
            lista.append(('Promo del mes', pivot_df3))
            lista.append(('Promo Bridgestone', pivot_df5))
            lista.append(('Promo T4-Plus', pivot_df6))
            
###########################################################################################################################################
        desired_fields = [
            'name',
            'user_id',
            'volume_profile'
        ]
        search_domain = [
            ('type', 'in', ['contact']),  # Filtrar por contactos
            ('partner_share', 'in', True), # Solo aquellos que compartan como socio
            ('active', 'in', True),
            ('category_id', 'not in', [11, 2, 13])
        ]
        records = self.env['res.partner'].search_read(search_domain, fields=desired_fields)
        result3 = [{key: value[1] if isinstance(value, tuple) else value for key, value in record.items()} for record in records]
        df30 = pd.DataFrame(result3)
        
        df30 = df30.rename(columns={
            'name': 'cliente',
            'user_id': 'vendedor',
            'volume_profile': 'perfil'
        })
        
        df30['perfil'] = df30['perfil'].fillna('Sin Perfil')
        
        df30.loc[(df30['perfil'] == 'AAA'), 'meta'] = 1000
        df30.loc[(df30['perfil'] == 'AA'), 'meta'] = 600
        df30.loc[(df30['perfil'] == 'A'), 'meta'] = 300
        df30.loc[(df30['perfil'] == 'B'), 'meta'] = 100
        df30.loc[(df30['perfil'] == 'C'), 'meta'] = 30
        df30.loc[(df30['perfil'] == 'D'), 'meta'] = 0
        df30.loc[(df30['perfil'] == 'Sin Perfil'), 'meta'] = ''
        
        df30.loc[(df30['vendedor'] == 'DIEGO GOMEZ'), 'zona'] = 'AGS'
        df30.loc[(df30['vendedor'] == 'SERGIO VILLEGAS'), 'zona'] = 'GTO'
        df30.loc[(df30['vendedor'] == 'IGNACIO FLORES GONZALEZ'), 'zona'] = 'MICH'
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
            AND so.date_order BETWEEN %s AND %s
            AND sol.qty_invoiced = 0
            AND so.state not IN ('cancel')
            AND so.user_id not IN (31, 25)
            GROUP BY rp2."name", so."name", so.date_order, so.state, rp."name"
        """
        ##Retornar la consulta sql
        self.env.cr.execute(query10, (primer_dia_mes, ultimo_dia_mes))
        result10 = self.env.cr.dictfetchall()        #Crear dataframe dla consulta
        df10 = pd.DataFrame(result10)
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
            ('move_id.partner_id.active', 'in', [True, False])
        ]

        records20 = self.env['account.move.line'].search_read(search_domain20 ,fields=desired_fields20)
        
        # Mapear los datos del campo relacionado 'invoice_user_id' desde 'move_id'
        for record in records20:
            move = self.env['account.move'].browse(record['move_id'][0])
            record['invoice_user_id'] = move.invoice_user_id.name  
        
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
        merged_df['state'] = merged_df['state'].fillna('Sin Pedido')
        merged_df['cantidad de llantas'] = merged_df['cantidad de llantas'].fillna(0) 
        
        new_order = ['id', 'cliente', 'perfil', 'vendedor', 'meta', 'zona', 'date_order', 'state', 'día', 'semana_del_año_str', 'cantidad de llantas']
        merged_df = merged_df[new_order]
        pivot_df4 = merged_df.pivot_table(index=['cliente', 'perfil', 'vendedor', 'meta', 'zona'], columns='state', values='cantidad de llantas', aggfunc='sum', fill_value=0)
        pivot_df4.reset_index(inplace=True)
        
        if 'Sin Pedido' in pivot_df4.columns:
            pivot_df4 = pivot_df4.drop(columns=['Sin Pedido'])
        if 'Timbrado' in pivot_df4.columns:
            pivot_df4['Timbrado'] = pivot_df4['Timbrado'].replace(0, '')
        if 'Orden de venta' in pivot_df4.columns:
            pivot_df4['Orden de venta'] = pivot_df4['Orden de venta'].replace(0, '')
        if 'Cotizaciones' in pivot_df4.columns:
            pivot_df4['Cotizaciones'] = pivot_df4['Cotizaciones'].replace(0, '')
            
        lista.append(('Reporte Reserva Ventas', pivot_df4))
        
        return lista