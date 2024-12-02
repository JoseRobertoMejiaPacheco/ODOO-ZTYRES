from odoo import api, fields, models
import math
import pandas as pd
import datetime
import numpy as np
from dateutil.relativedelta import relativedelta

class AvanceAsesor(models.TransientModel):
    _name = 'ztyres_reporte_avance_asesor'

    def get_report(self):
        ####Consulta Sql Probada
        query = """
              SELECT 
                zpb."name" AS marca, 
                aml."name", 
                zpt."name" AS tier,
                CASE 
                    WHEN am.move_type in ('out_refund') THEN -aml.quantity
                    ELSE aml.quantity
                END as cantidad,
                rp_customer."name" as cliente, 
                rp_salesperson."name" as vendedor
            FROM account_move_line aml 
            JOIN account_move am ON aml.move_id = am.id 
            JOIN product_product pp ON aml.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id 
            JOIN res_users ru ON am.invoice_user_id = ru.id  
            JOIN res_partner rp_customer ON aml.partner_id = rp_customer.id 
            JOIN res_partner rp_salesperson ON ru.partner_id = rp_salesperson.id  -- Unión para obtener el vendedor
            JOIN ztyres_products_tier zpt ON pt.tier_id = zpt.id 
            JOIN ztyres_products_brand zpb ON pt.brand_id = zpb.id 
            WHERE aml.date BETWEEN '2024-03-01' AND '2024-03-31'
            AND am.move_type IN ('out_invoice', 'out_refund')            
            AND am.state = 'posted'
            AND aml.display_type = 'product'
            AND pt.detailed_type = 'product'
        """
        ##Retornar la consulta sql
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()        
        #Crear dataframe dla consulta
        df = pd.DataFrame(result)
        
        query2 = """
            SELECT 
                so."name",
                so.date_order,
                zpb."name" AS marca, 
                sol."name",
                zpt."name" AS tier,
                sol.product_uom_qty AS cantidad,
                rp_customer."name" AS cliente,
                rp_salesperson."name" AS vendedor 
            FROM sale_order_line sol
            JOIN sale_order so on sol.order_id = so.id 
            JOIN res_users ru ON so.user_id = ru.id 
            JOIN res_partner rp_customer ON so.partner_invoice_id = rp_customer.id 
            JOIN res_partner rp_salesperson ON ru.partner_id = rp_salesperson.id  -- Unión para obtener el vendedor
            JOIN product_product pp ON sol.product_id = pp.id 
            JOIN product_template pt ON pp.product_tmpl_id = pt.id 
            JOIN ztyres_products_tier zpt ON pt.tier_id = zpt.id 
            JOIN ztyres_products_brand zpb ON pt.brand_id = zpb.id 
            WHERE so.date_order BETWEEN '2024-03-01' AND '2024-03-31'
            AND so.state NOT IN ('cancel')
            AND pt.detailed_type = 'product'
        """
        ##Retornar la consulta sql
        self.env.cr.execute(query2)
        result2 = self.env.cr.dictfetchall()
        df2 = pd.DataFrame(result2)
        
        submarca_a_marca = {
            'GOODYEAR': 'GOODYEAR',
            'KELLY': 'GOODYEAR',
            'DUNLOP': 'GOODYEAR',
            'SEIBERLING': 'GOODYEAR',
            'BRIDGESTONE': 'BRIDGESTONE',
            'FIRESTONE': 'BRIDGESTONE',
            'FUZION': 'BRIDGESTONE',
            'PIRELLI': 'PIRELLI',
            'CONTINENTAL': 'CONTINENTAL',
            'EUZKADI': 'CONTINENTAL',
            'KUMHO': 'KUMHO',
            'COOPER': 'COOPER',
            'MASTERCRAFT': 'COOPER',
            'STARFIRE': 'COOPER',
            'APTANY': 'APTANY',
            'DELINTE': 'DELINTE',
            'FIREMAX': 'FIREMAX',
            'MAXXIS': 'MAXXIS',
            'TORNEL': 'TORNEL'
        }
        
        otros_vendedores = {
            'DIEGO GOMEZ': 'DIEGO GOMEZ',
            'HUMBERTO MORENO': 'HUMBERTO MORENO',
            'MAURICIO RODRIGUEZ CASTAÑEDA': 'OTROS',
            'OMAR BARRAZA AGUILERA': 'OMAR BARRAZA AGUILERA',
            'RAMIRO BARRIOS MACÍAS': 'RAMIRO BARRIOS MACÍAS',
            'SERGIO VILLEGAS': 'SERGIO VILLEGAS',
            'VICTOR SALAS': 'OTROS',
            'DARIANA JANETH OROZCO VÁZQUEZ': 'OTROS',
            'Gilberto Cruz Pimentel': 'Gilberto Cruz Pimentel',
            'JOSE ROBERTO MEJIA PACHECO': 'OTROS',
            'RICARDO DE COSS': 'OTROS',
            'Sergio Sánchez Ortíz': 'OTROS',
            'José de Jesús Sotelo Piñón': 'OTROS',
            'KIMBERLY AILED LAMAS VEGA': 'OTROS',
            'GUADALUPE CASTRO': 'OTROS'
        }
        
        # Agregar una columna "submarca" al DataFrame utilizando el diccionario
        df['submarca'] = df['marca'].map(submarca_a_marca)
        df2['submarca'] = df2['marca'].map(submarca_a_marca)
        
        # Agregar una columna "Otros" al DataFrame utilizando el diccionario
        df['otros'] = df['vendedor'].map(otros_vendedores)
        df2['otros'] = df2['vendedor'].map(otros_vendedores)
        
        # Agrupar y sumar los valores por marca
        result_df = df.groupby('submarca')['cantidad'].sum().reset_index()
        result_df2 = df2.groupby('submarca')['cantidad'].sum().reset_index()
        
        # Agrupar y sumar los valores por vendedor
        result_df = df.groupby('otros')['vendedor'].sum().reset_index()
        result_df2 = df2.groupby('otros')['vendedor'].sum().reset_index()
        
        #crear tabla pivote con marcas y asesores
        pivot_df = df.pivot_table(index='submarca', columns='otros', values='cantidad', aggfunc='sum')
        pivot_df = pivot_df.fillna(0)
        pivot_df.reset_index(inplace=True)
        pivot_df.rename(columns={'otros': 'Total'}, inplace=True)
        
        #crear tabla pivote con tier de llantas y asesores
        pivot_df2 = df.pivot_table(index='tier', columns='otros', values='cantidad', aggfunc='sum')
        pivot_df2 = pivot_df2.fillna(0)
        pivot_df2.reset_index(inplace=True)
        pivot_df2.rename(columns={'vendedor': 'Total'}, inplace=True)
        
        #crear tabla pivote Cotizaciones por Vendedor
        pivot_df3 = df2.pivot_table(index='submarca', columns='otros', values='cantidad', aggfunc='sum')
        pivot_df3 = pivot_df3.fillna(0)
        pivot_df3.reset_index(inplace=True)
        pivot_df3.rename(columns={'otros': 'Total'}, inplace=True)
        
        #crear tabla pivote Cotizaciones con tier por Vendedor
        pivot_df4 = df2.pivot_table(index='tier', columns='otros', values='cantidad', aggfunc='sum')
        pivot_df4 = pivot_df4.fillna(0)
        pivot_df4.reset_index(inplace=True)
        pivot_df4.rename(columns={'vendedor': 'Total'}, inplace=True)
        
        #Combina las tablas Pivote VENTAS/COTIZACIONES
        merged_df = pd.merge(pivot_df, pivot_df3, on='submarca', suffixes=('_Ven', '_Cot'), how='inner')
        merged_df2 = pd.merge(pivot_df2, pivot_df4, on='tier', suffixes=('_Ven', '_Cot'), how='inner')
        
        #Ordena alfabéticamente las columnas
        merged_df = merged_df[merged_df.columns[0:1].tolist() + sorted(merged_df.columns[1:])]
        merged_df2 = merged_df2[merged_df2.columns[0:1].tolist() + sorted(merged_df2.columns[1:])]
        
        ##Instanciar la clase ztyres_ms_sql_excel_core que tiene el metodo para insertar un dataframe en sql server
        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(merged_df, 'reporte_avance_asesor_marca')
        reports_core.action_insert_dataframe(merged_df2, 'reporte_avance_asesor_tier')
        return