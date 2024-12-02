from odoo import api, fields, models
import pandas as pd
import math
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class Forecast(models.TransientModel):
    _name = 'reporte_forecast'
    
    def convert_to_company_currency(self, currency_id, amount, date):
        if currency_id is not None and not math.isnan(amount) and not pd.isna(date):
            currency_record = self.env['res.currency'].browse(int(currency_id))
            converted_amount = currency_record._convert(
                amount,
                currency_record.env.company.currency_id,
                currency_record.env.company,
                date
                )
        else: 
            return 0
        return converted_amount

    def get_report(self):
        ####Consulta Sql Probada
        query = """
        SELECT 
        	pt.id as ptid,
            pt.cui as CIU, 
            zptm."name" AS Medida, 
            zps."name" AS Seg, 
            zpt."name" AS Uso, 
            zpm."name" AS Fabricante,
            inv.available AS inv,
            subquery.ultimo_costo_final AS costo_compra,
            subquery.moneda_pedido AS tipo_cambio,
            subquery.fecha_pedido_compra AS fecha_compra
        FROM product_template pt 
        LEFT JOIN ztyres_products_tire_measure zptm ON pt.tire_measure_id = zptm.id 
        LEFT JOIN ztyres_products_segment zps ON pt.segment_id = zps.id
        LEFT JOIN ztyres_products_type zpt ON pt.type_id = zpt.id
        LEFT JOIN ztyres_products_manufacturer zpm ON pt.manufacturer_id = zpm.id 
        LEFT JOIN product_product pp ON pt.id = pp.product_tmpl_id 
        LEFT JOIN 
            (SELECT DISTINCT ON (pp.product_tmpl_id)
                        pp.product_tmpl_id AS id,
                        aml.costo_final AS ultimo_costo_final,
                	    am.currency_id AS moneda_pedido, 
                        am."date" AS fecha_pedido_compra
                    FROM account_move am 
                    JOIN account_move_line aml ON am.id = aml.move_id
                    JOIN product_product pp ON aml.product_id = pp.id 
                    JOIN product_template pt ON pp.product_tmpl_id = pt.id 
                    WHERE am.state in ('posted')
                    AND am.move_type in ('in_invoice') 
                    AND aml.display_type in ('product')
                    AND aml.costo_final is not null 
                    AND aml.costo_final != 0
                    ORDER BY pp.product_tmpl_id, am."date" DESC
            ) subquery ON pt.id = subquery.id
        LEFT JOIN 
        	   (SELECT sq.product_id AS id, 
                    SUM(sq.quantity - sq.reserved_quantity) AS available
             	FROM stock_quant sq
             	JOIN stock_location sl ON sq.location_id = sl.id
             	WHERE sl.usage = 'internal'
             	GROUP BY sq.product_id
        ) inv ON pp.id = inv.id
        WHERE pp.active = true
        AND pt.detailed_type in ('product')
        """
        ##Retornar la consulta sql
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()        #Crear dataframe dla consulta
        df = pd.DataFrame(result)
        
        df['UCF'] = df.apply(lambda row: self.convert_to_company_currency(row['tipo_cambio'], row['costo_compra'], row['fecha_compra']), axis=1)
   
        df_pivoted = df.pivot_table(index=['ciu', 'medida', 'seg', 'uso'], 
                                    columns='fabricante', 
                                    values='UCF', 
                                    aggfunc='first', 
                                    fill_value=0)
        
        ######################################################################################
        df_tier4 = df_pivoted.copy()
        
        df_pivoted = df_pivoted.drop(columns=['APTANY', 'FALKEN', 'KUMHO', 'MAXXIS', 'SENTURY', 'SUNFULCESS', 'TORNEL', 'HANKOOK'])
        condicion = (df_pivoted[['BRIDGESTONE', 'CONTINENTAL', 'GOODYEAR', 'PIRELLI']] == 0).all(axis=1)
        df_pivoted = df_pivoted[~condicion]
        
        df_tier4 = df_tier4.drop(columns=['BRIDGESTONE', 'CONTINENTAL', 'GOODYEAR', 'PIRELLI', 'MAXXIS', 'KUMHO', 'FALKEN', 'TORNEL','HANKOOK'])
        condicion2 = (df_tier4[['APTANY', 'SENTURY', 'SUNFULCESS']] == 0).all(axis=1)
        df_tier4 = df_tier4[~condicion2]
        
        ######################################################################################
        df_filtro = df.copy()
        
        # Agregar la columna 'inv' al mismo df_pivoted
        df = df[df['fabricante'].isin(df_pivoted.columns)]
        df_pivoted['inv'] = df.groupby(['ciu', 'medida', 'seg', 'uso'])['inv'].sum()
        df_pivoted = df_pivoted.reset_index()
        
        df_filtro = df_filtro[df_filtro['fabricante'].isin(df_tier4.columns)]
        df_tier4['inv'] = df_filtro.groupby(['ciu', 'medida', 'seg', 'uso'])['inv'].sum()
        df_tier4 = df_tier4.reset_index()
        
        # Aplanar el índice de columnas
        df_pivoted.columns = [f'{col}' for col in df_pivoted.columns]
        df_pivoted = df_pivoted.reset_index()
        
        df_tier4.columns = [f'{col2}' for col2 in df_tier4.columns]
        df_tier4 = df_tier4.reset_index()
        #----------------------------------------------------------------------------------------------------------
        query2 = """
            select pt.id as id, pt.cui as ciu, zpm."name" as fabricante,
            (CASE 
            	WHEN am.move_type = 'out_refund'
            	THEN aml.quantity * -1 
            	ELSE aml.quantity END) 
            as cantidad,
            am.invoice_date as fecha_factura 
            from account_move_line aml 
            join account_move am on aml.move_id = am.id
            join product_product pp on aml.product_id = pp.id 
            join product_template pt on pp.product_tmpl_id = pt.id 
            join ztyres_products_manufacturer zpm on pt.manufacturer_id = zpm.id
            where aml.display_type in ('product')
            AND am.move_type IN ('out_invoice', 'out_refund')
            AND pp.active = true
            AND pt.detailed_type IN ('product')
        """
        ##Retornar la consulta sql
        self.env.cr.execute(query2)
        result2 = self.env.cr.dictfetchall()        #Crear dataframe dla consulta
        df2 = pd.DataFrame(result2)
        
        # Convertir la columna fecha_factura a datetime
        df2['fecha_factura'] = pd.to_datetime(df2['fecha_factura'])
        # Obtener la fecha actual
        fecha_actual = pd.to_datetime('today')
        # Calcular el primer día del mes hace 6 meses
        primer_dia_mes_antiguo = fecha_actual - pd.DateOffset(months=6) + pd.offsets.MonthBegin(1)
        # Filtrar los datos desde el primer día del mes más antiguo hasta la fecha actual
        df2 = df2[(df2['fecha_factura'] >= primer_dia_mes_antiguo) & (df2['fecha_factura'] <= fecha_actual)]
        # Agregar una columna con el nombre del mes correspondiente
        df2['mes'] = df2['fecha_factura'].dt.month_name()
        
        df3 = df2.copy()
        df2 = df2[df2['fabricante'].isin(df_pivoted.columns)]
        df2 = df2.drop(columns=['fabricante'])
        
        df3 = df3[df3['fabricante'].isin(df_tier4.columns)]
        df3 = df3.drop(columns=['fabricante'])
        
        # Pivotar los datos para crear una columna por cada mes diferente y agrupar "cantidad"
        df_pivoted2 = df2.pivot_table(index=['ciu'], 
                                    columns='mes', 
                                    values='cantidad', 
                                    aggfunc='sum', 
                                    fill_value=0)
        
                # Seleccionar todas las columnas numéricas
        columnas_numericas = df_pivoted2.select_dtypes(include='number')
        # Calcular el promedio horizontal
        df_pivoted2['PV'] = columnas_numericas.mean(axis=1).round(2)

        df_pivoted3 = df3.pivot_table(index=['ciu'], 
                                    columns='mes', 
                                    values='cantidad', 
                                    aggfunc='sum', 
                                    fill_value=0)
        
        # Seleccionar todas las columnas numéricas
        columnas_numericas = df_pivoted3.select_dtypes(include='number')
        # Calcular el promedio horizontal
        df_pivoted3['PV'] = columnas_numericas.mean(axis=1).round(2)
        # Aplanar el índice de columnas
        df_pivoted2.columns = [f'{col}' for col in df_pivoted2.columns]
        # Reiniciar el índice para obtener un DataFrame bien formateado
        df_final = df_pivoted2.reset_index()
        
        df_pivoted3.columns = [f'{col3}' for col3 in df_pivoted3.columns]
        # Reiniciar el índice para obtener un DataFrame bien formateado
        df_final2 = df_pivoted3.reset_index()
        
        
        merged_df = pd.merge(df_pivoted, df_final, on='ciu', how='outer')
        
        merged_df2 = pd.merge(df_tier4, df_final2, on='ciu', how='outer')

        new_names1 = {
            "ciu": "CIU",
            "medida": "Medida",
            "seg": "Seg",
            "uso": "Uso",
            "BRIDGESTONE": "BRIDGESTONE",	
            "CONTINENTAL": "CONTINENTAL",	
            "GOODYEAR": "GOODYEAR",	
            "PIRELLI": "PIRELLI",
            "July": "JUL",
            "August": "AGO",
            "September": "SEP",
            "October": "OCT",
            "November": "NOV",
            "December": "DIC",
            "PV": "PV",
            "inv": "Disponible"
        }
        
        new_names2 = {
            "ciu": "CIU",
            "medida": "Medida",
            "seg": "Seg",
            "uso": "Uso",
            "APTANY": "APTANY",	
            "SENTURY": "SENTURY",	
            "SUNFULCESS": "SUNFULCESS",
            "July": "JUL",
            "August": "AGO",
            "September": "SEP",
            "October": "OCT",
            "November": "NOV",
            "December": "DIC",
            "PV": "PV",
            "inv": "Disponible"
        }
        # Renombrar columnas en el DataFrame fusionado
        merged_df.rename(columns=new_names1, inplace=True)
        # Ordenar las columnas según el orden deseado
        ordered_columns1 = list(new_names1.values())
        merged_df = merged_df[ordered_columns1]
        # Realizar la división y manejar infinito
        merged_df['Niv. Inv'] = (merged_df['Disponible'] / merged_df['PV']).replace([np.inf, -np.inf], np.nan).round(2)

        merged_df2.rename(columns=new_names2, inplace=True)
        # Ordenar las columnas según el orden deseado
        ordered_columns2 = list(new_names2.values())
        merged_df2 = merged_df2[ordered_columns2]
        merged_df2['Niv. Inv'] = (merged_df2['Disponible'] / merged_df2['PV']).replace([np.inf, -np.inf], np.nan).round(2)

        ##Instanciar la clase ztyres_ms_sql_excel_core que tiene el metodo para insertar un dataframe en sql server
        reports_core = self.env['ztyres_ms_sql_excel_core']                
        reports_core.action_insert_dataframe(merged_df, 'forecastT1')
        reports_core.action_insert_dataframe(merged_df2, 'forecastT4')
        return