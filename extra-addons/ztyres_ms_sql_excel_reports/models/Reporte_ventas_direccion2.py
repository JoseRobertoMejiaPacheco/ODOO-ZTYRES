from odoo import api, fields, models
import math
import pandas as pd
from datetime import datetime, timedelta, date
import numpy as np
from dateutil.relativedelta import relativedelta
from functools import reduce

class ReporteVentasDireccion(models.TransientModel):
    _name = 'reporte_ventas_direccion'
    
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
        # Definir las fechas para el filtro
        primer_dia_año = pd.to_datetime('2026-01-01')
        ultimo_dia_año = pd.to_datetime('2026-12-31')

        meses_es = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        meses_mapping = {
            "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
            "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
            "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
        }
        
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
            'JOSE AARON FONSECA RADA',
            'Alvaro Ivan Andrade Rosales',
            'CHRISTIAN GUADALUPE NORIEGA PALACIOS',
            'JOSE MARIANO JAIME MARQUEZ',
            'LAURA MONSERRAT TORRES VAZQUEZ',
            'HUMBERTO MORENO',
        ]
        
        vendedores = [
            'DIEGO GOMEZ',
            'JOSE AARON FONSECA RADA',
            'Alvaro Ivan Andrade Rosales',
            'CHRISTIAN GUADALUPE NORIEGA PALACIOS',
            'JOSE MARIANO JAIME MARQUEZ',
            'LAURA MONSERRAT TORRES VAZQUEZ',
            'HUMBERTO MORENO',
            'OTROS',
            'RICARDO DE COSS'
        ]
        # Consulta SQL combinada
        query = """
            SELECT DISTINCT ON (so."name")
                rp."name" AS vendedor,
                so.date_order AS fecha,
                zpm."name" AS fabricante,
                SUM(sol.product_uom_qty) AS "cantidad",
                SUM(sol.price_subtotal) AS "subtotal",
                so.currency_id AS "divisa",
                rcs.code AS "estado"
            FROM sale_order so
            LEFT JOIN sale_order_line sol ON so.id = sol.order_id  
            LEFT JOIN res_partner rp2 ON sol.order_partner_id = rp2.id 
            LEFT JOIN product_product pp ON sol.product_id = pp.id 
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id 
            LEFT JOIN res_users ru ON so.user_id = ru.id
            LEFT JOIN res_partner rp ON ru.partner_id = rp.id
            LEFT JOIN ztyres_products_manufacturer zpm ON pt.manufacturer_id = zpm.id
            LEFT JOIN res_country_state rcs ON rp2.state_id = rcs.id
            WHERE pt.detailed_type = 'product'
            AND so.date_order BETWEEN %s AND %s
            AND sol.qty_invoiced = 0
            AND so.state not IN ('cancel')
            GROUP BY rp2."name", so."name", so.date_order, rp."name", zpm."name", so.currency_id, rcs.code, rp2."name"
        """
        # Ejecutar la consulta
        self.env.cr.execute(query, (primer_dia_año, ultimo_dia_año))
        result = self.env.cr.dictfetchall()
        df = pd.DataFrame(result)
        
        df['fecha'] = pd.to_datetime(df['fecha'])
        df['mes'] = df['fecha'].dt.month.map(meses_es)
        df.loc[df['vendedor'].isin (ventas_lic), 'vendedor'] = 'RICARDO DE COSS'
        df.loc[~df['vendedor'].isin(vendedores_Actuales + ventas_lic), 'vendedor'] = 'OTROS'
        
        df['vendedor'] = pd.Categorical(df['vendedor'], categories=vendedores, ordered=True)
        df['mes'] = (df['fecha'].dt.month_name().replace(meses_mapping))
        df['año'] = (df['fecha'].dt.year.astype(str))
        df['Tipo'] = 'COTIZACIONES'


        query2 = """
            SELECT
                rp."name" as cliente,
            	rcs.code AS estado,
                zpm."name" AS fabricante,
                rp2."name" AS vendedor, 
                SUM(CASE
                WHEN am.move_type IN ('out_refund') THEN -aml.quantity
                ELSE aml.quantity
                END) AS cantidad,
                SUM(CASE
                WHEN am.move_type IN ('out_refund') THEN aml.price_subtotal * -1
                ELSE aml.price_subtotal
                END) AS subtotal,
                am.invoice_date AS fecha,
                am.currency_id AS divisa,
                rp.country_id AS country
            FROM account_move_line aml 
            LEFT JOIN account_move am ON aml.move_id = am.id 
            LEFT JOIN product_product pp ON aml.product_id = pp.id
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
            LEFT JOIN ztyres_products_manufacturer zpm ON pt.manufacturer_id = zpm.id
            LEFT JOIN res_partner rp ON am.partner_id = rp.id
            LEFT JOIN res_users ru ON rp.user_id = ru.id
            LEFT JOIN res_partner rp2 ON ru.partner_id = rp2.id
            LEFT JOIN res_country_state rcs ON rp.state_id = rcs.id
            WHERE am.state IN ('posted')
            AND am.move_type IN ('out_invoice', 'out_refund')
            AND pt.detailed_type IN ('product')
            AND aml.display_type IN ('product')
            GROUP BY rcs.code, zpm."name", rp2."name", pt.id, ru.id, am.invoice_date, rp.country_id, 
                     aml.move_id, am.currency_id, rp."name"
        """
        # Ejecutar la consulta
        self.env.cr.execute(query2)
        result2 = self.env.cr.dictfetchall()
        df2 = pd.DataFrame(result2)
        
        df3 = df2.copy()
        df2['fecha'] = pd.to_datetime(df2['fecha'])
        df2 = df2[df2['fecha'].between(primer_dia_año, ultimo_dia_año)]
        df2.drop(columns=['country'], inplace=True)
        
        df2['mes'] = df2['fecha'].dt.month.map(meses_es)
        df2.loc[df2['vendedor'].isin (ventas_lic), 'vendedor'] = 'RICARDO DE COSS'
        df2.loc[~df2['vendedor'].isin(vendedores_Actuales + ventas_lic), 'vendedor'] = 'OTROS'
        
        df2['subtotal'] = df2.apply(lambda row: self.convert_to_company_currency(row['divisa'], row['subtotal'], row['fecha']), axis=1)
        df2['vendedor'] = pd.Categorical(df2['vendedor'], categories=vendedores, ordered=True)
        
        df2['Tipo'] = 'FACTURADO'
        cols = ['estado', 'fabricante', 'vendedor', 'cantidad', 'subtotal', 'fecha', 'divisa', 'mes', 'Tipo']
        df = df[cols]
        df2 = df2[cols]
        df_final = pd.concat([df, df2], ignore_index=True)
        df_final['cantidad'] = df_final['cantidad'].astype(int)
        
        search_domain = [
            ('invoice_date', '>=', primer_dia_año),
            ('invoice_date', '<=', ultimo_dia_año),
            ('move_type', 'in', ['out_invoice']),  # aquí junto ambas
            ('state', 'in', ['posted'])
            ]
        datos = []
        records = self.env['account.move'].search(search_domain)
        for record in records:
            lineas = record.line_ids.filtered(lambda l: l.account_id.reconcile)
            partials = lineas.matched_credit_ids
            notas_credito_pr = partials.filtered(
                lambda pr:
                    pr.credit_move_id.move_id.move_type == 'out_refund'
                    and all(
                        line.product_id.detailed_type != 'product'
                        for line in pr.credit_move_id.move_id.invoice_line_ids
                    )
            )
            total_nc = sum(notas_credito_pr.mapped('amount'))
            vals = {
                # 'movimiento': record.name,
                'estado': record.partner_id.state_id.name,
                'fabricante': "", 
                'vendedor': record.invoice_user_id.name or '',
                'cantidad': 0,
                'subtotal': total_nc,
                'fecha': record.invoice_date,
                'divisa': record.currency_id.id
            }
            datos.append(vals)
        df4 = pd.DataFrame(datos)
        df4['fecha'] = pd.to_datetime(df4['fecha'])
        df4['mes'] = (df4['fecha'].dt.month_name().replace(meses_mapping))
        df4['Tipo'] = 'Nota de Crédito'
        
        df_final2 = pd.concat([df_final, df4], ignore_index=True)
        
        df3.columns = df3.columns.str.strip().str.lower()

        df3 = df3[df3['country'].isin([156])]

        # ==========================================
        # 3. Últimos 6 meses
        # ==========================================
        df3['fecha'] = pd.to_datetime(df3['fecha'])
        hoy = pd.Timestamp.today()
        fecha_max = hoy.replace(day=1)
        primer_dia_mes_actual = fecha_max.replace(day=1)
        fecha_inicio = primer_dia_mes_actual - relativedelta(months=6)
        fecha_fin = primer_dia_mes_actual - pd.Timedelta(days=1)

        df3 = df3[
            (df3['fecha'] >= fecha_inicio) &
            (df3['fecha'] <= fecha_fin)
        ].copy()
        
        ventas_cliente = (
            df3.groupby('cliente', as_index=False)['subtotal']
            .sum()
            .sort_values('subtotal', ascending=False)
        )

        total_general = ventas_cliente['subtotal'].sum()

        ventas_cliente['acumulado'] = ventas_cliente['subtotal'].cumsum()
        ventas_cliente['porcentaje_acumulado'] = (
            ventas_cliente['acumulado'] / total_general
        )

        clientes_80 = ventas_cliente[
            ventas_cliente['porcentaje_acumulado'] <= 0.80
        ]['cliente']

        df3 = df3[df3['cliente'].isin(clientes_80)].copy()
        
        df3['mes'] = df3['fecha'].dt.month.map(meses_es)

        df_resultado = (df3.groupby(['cliente', 'fabricante', 'mes'],as_index=False)
                           .agg(cantidad_total=('cantidad', 'sum'))
                           .sort_values(['cliente', 'cantidad_total'], ascending=[True, False]))
        
        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(df_final2, 'venta_anual')
        reports_core.action_insert_dataframe(df_resultado, 'detalle_ultimos_6_meses')