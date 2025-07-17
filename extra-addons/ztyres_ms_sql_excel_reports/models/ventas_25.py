from odoo import api, fields, models
import math
import pandas as pd
from datetime import datetime, timedelta, date
import numpy as np
from dateutil.relativedelta import relativedelta
from functools import reduce
from odoo.addons.inv_promo.wizard.models.lista_de_precios import codes, codes2, codes3

class MyModel(models.TransientModel):
    _name = 'reporte_ventas25'
    
    def convert_to_company_currency(self, currency_id, amount, date):
        currency_id = self.env['res.currency'].browse(currency_id)
        converted_amount = currency_id._convert(
            amount,
            currency_id.env.company.currency_id,
            currency_id.env.company,
            date
        )
        return converted_amount
    
    def get_report(self):
        
        desired_fields = [
            'name',
            'user_id'
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
            'user_id': 'vendedor'
        })

        # Definir las fechas para el filtro
        primer_dia_mes = pd.to_datetime('2025-01-01')
        ultimo_dia_mes = pd.to_datetime('2025-12-31')

        meses_es = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }

        # Lista de usuarios no vendedores
        no_vendedores = [25, 31, 115]

        # Consulta SQL combinada
        query = """
            SELECT
                zpm."name" as fabricante,
                rp."name" AS vendedor, 
                SUM(CASE
                WHEN am.move_type IN ('out_refund') THEN -aml.quantity
                ELSE aml.quantity
                END) AS cantidad,
                CASE
                WHEN ru.id IN %s THEN 'ventas_lic'
                ELSE 'ventas'
                END AS no_c,
                SUM(CASE
                WHEN am.move_type IN ('out_refund') THEN aml.price_subtotal * -1
                ELSE aml.price_subtotal
                END) AS subtotal,
                am.currency_id AS divisa,
                am.invoice_date AS fecha
            FROM account_move_line aml 
            LEFT JOIN account_move am ON aml.move_id = am.id 
            LEFT JOIN product_product pp ON aml.product_id = pp.id
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
            LEFT JOIN  ztyres_products_manufacturer zpm ON pt.manufacturer_id = zpm.id
            LEFT JOIN res_users ru ON am.invoice_user_id = ru.id
            LEFT JOIN res_partner rp ON ru.partner_id = rp.id
            WHERE am.invoice_date BETWEEN %s AND %s
            AND am.state IN ('posted')
            AND am.move_type IN ('out_invoice', 'out_refund')
            AND pt.detailed_type IN ('product')
            AND aml.display_type IN ('product')
            GROUP BY zpm."name", rp."name", pt.id, ru.id, am.invoice_date, am.currency_id
            ORDER BY rp."name"
        """
        # Ejecutar la consulta
        self.env.cr.execute(query, (tuple(no_vendedores), primer_dia_mes, ultimo_dia_mes))
        result = self.env.cr.dictfetchall()
        df = pd.DataFrame(result)
        
        ventas_lic = [
            'DARIANA JANETH OROZCO VAZQUEZ',
            'MOISÉS ALFARO VÁZQUEZ',
            'CARMEN MIRELES',
            'ATXEL MIGUEL RAMIREZ HIDALGO',
            'JUANA PATRICIA REYES GOMES',
            'RICARDO DE COSS'
        ]
        
        vendedores_Actuales = [
            'DIEGO GOMEZ',
            'HUMBERTO MORENO',
            'RAMIRO BARRIOS MACÍAS',
            'JOSE AARON FONSECA RADA'
        ]
        
        df.loc[df['vendedor'].isin (ventas_lic), 'vendedor'] = 'RICARDO DE COSS'
        df.loc[~df['vendedor'].isin(vendedores_Actuales + ventas_lic), 'vendedor'] = 'OTROS'

        
        df['fecha'] = pd.to_datetime(df['fecha'])
        df['mes'] = df['fecha'].dt.month.map(meses_es)
        df.loc[(df['fabricante'] == 'SUNFULCESS', 'fabricante')] = 'FIREMAX'
        df.loc[(df['fabricante'] == 'SENTURY', 'fabricante')] = 'DELINTE'
        
        df['subtotal2'] = df.apply(lambda row: self.convert_to_company_currency(row['divisa'], row['subtotal'], row['fecha']), axis=1)

        df2_ventas = df.copy()
        df3_totales = df.copy()

        df = df.loc[(df['no_c'] == 'ventas_lic')]
        df2_ventas = df2_ventas.loc[(df2_ventas['no_c'] == 'ventas')]

        df_pivoted = df.pivot_table(index=['fabricante'], 
                                    columns='mes', 
                                    values='cantidad', 
                                    aggfunc='sum', 
                                    fill_value=0)

        df_pivoted2 = df2_ventas.pivot_table(index=['fabricante'], 
                                            columns='mes', 
                                            values='cantidad', 
                                            aggfunc='sum', 
                                            fill_value=0)
        
        df_pivoted3 = df3_totales.pivot_table(index=['mes'], 
                                              columns='vendedor', 
                                              values='subtotal2', 
                                              aggfunc='sum', 
                                              fill_value=0)
                    
        nuevas = []
        for col in ['RICARDO DE COSS', 'OTROS']:
            if col in df_pivoted3.columns:
                nuevas.append(col)
                
        otras = [col for col in df_pivoted3.columns if col not in nuevas]
        df_pivoted3 = df_pivoted3[nuevas + otras]
        
        df_pivoted4 = df3_totales.pivot_table(index=['mes'], 
                                      columns='vendedor', 
                                      values='cantidad', 
                                      aggfunc='sum', 
                                      fill_value=0)
        
        nuevas = []
        for col in ['RICARDO DE COSS', 'OTROS']:
            if col in df_pivoted4.columns:
                nuevas.append(col)
                
        otras = [col for col in df_pivoted4.columns if col not in nuevas]
        df_pivoted4 = df_pivoted4[nuevas + otras]
        
        orden_meses = [meses_es[m] for m in range(1, 13)]

        df_pivoted = df_pivoted.reindex(columns=orden_meses).reset_index()
        df_pivoted2 = df_pivoted2.reindex(columns=orden_meses).reset_index()
        df_pivoted3 = df_pivoted3.reindex(index=orden_meses).reset_index()
        df_pivoted4 = df_pivoted4.reindex(index=orden_meses).reset_index()
        

        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(df_pivoted, 'ventas_lic')
        reports_core.action_insert_dataframe(df_pivoted2, 'ventas_vendedores')
        reports_core.action_insert_dataframe(df_pivoted3, 'ventas_totales')
        reports_core.action_insert_dataframe(df_pivoted4, 'ventas_totales_cantidad')
        return 