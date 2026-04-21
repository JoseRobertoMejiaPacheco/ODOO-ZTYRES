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

        hoy = date.today()

        primer_dia_mes_actual = hoy.replace(day=1)
        siguiente_mes = (primer_dia_mes_actual.replace(day=28) + timedelta(days=4))
        ultimo_dia_mes_actual = siguiente_mes.replace(day=1) - timedelta(days=1)
        
        primer_dia_mes_actual = pd.to_datetime(primer_dia_mes_actual)
        ultimo_dia_mes_actual = pd.to_datetime(ultimo_dia_mes_actual)

        # Definir las fechas para el filtro
        primer_dia_año = pd.to_datetime('2026-01-01')
        ultimo_dia_año = pd.to_datetime('2026-12-31')

        meses_es = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
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
            'HUMBERTO MORENO',
            'Alvaro Ivan Andrade Rosales',
            'JOSE AARON FONSECA RADA',
            'CHRISTIAN GUADALUPE NORIEGA PALACIOS',
        ]
        
        vendedores = [
            'Alvaro Ivan Andrade Rosales',
            'CHRISTIAN GUADALUPE NORIEGA PALACIOS',
            'DIEGO GOMEZ',
            'HUMBERTO MORENO',
            'JOSE AARON FONSECA RADA',
            'OTROS',
            'RICARDO DE COSS'
        ]
        

        # Consulta SQL combinada
        query = """
			SELECT DISTINCT ON (so."name")
                rp."name" AS vendedor,
                so.date_order AS fecha,
                zpm."name" AS fabricante,
                SUM(sol.product_uom_qty) AS "cantidad de llantas"
            FROM sale_order so
            LEFT JOIN sale_order_line sol ON so.id = sol.order_id  
            LEFT JOIN res_partner rp2 ON sol.order_partner_id = rp2.id 
            LEFT JOIN product_product pp ON sol.product_id = pp.id 
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id 
            LEFT JOIN res_users ru ON so.user_id = ru.id
            LEFT JOIN res_partner rp ON ru.partner_id = rp.id
            LEFT JOIN ztyres_products_manufacturer zpm ON pt.manufacturer_id = zpm.id
            WHERE pt.detailed_type = 'product'
            AND so.date_order BETWEEN %s AND %s
            AND sol.qty_invoiced = 0
            AND so.state not IN ('cancel')
            GROUP BY rp2."name", so."name", so.date_order, rp."name", zpm."name"
        """
        # Ejecutar la consulta
        self.env.cr.execute(query, (primer_dia_mes_actual, ultimo_dia_mes_actual))
        result = self.env.cr.dictfetchall()
        df = pd.DataFrame(result)
        
        if result:
            df = pd.DataFrame(result)
        else:
            columns = [desc[0] for desc in self.env.cr.description]
            df = pd.DataFrame(columns=columns)
        
        df['fecha'] = pd.to_datetime(df['fecha'])
        df['mes'] = df['fecha'].dt.month.map(meses_es)
        df.loc[df['vendedor'].isin (ventas_lic), 'vendedor'] = 'RICARDO DE COSS'
        df.loc[~df['vendedor'].isin(vendedores_Actuales + ventas_lic), 'vendedor'] = 'OTROS'
        
        df['vendedor'] = pd.Categorical(df['vendedor'], categories=vendedores, ordered=True)
        
        #TABLA DE ORDEN DE VENTA Y COTIZACIONES POR FABRICANTE Y VENDEDOR
        pivot_fabricante_vendedor = pd.pivot_table(df, values='cantidad de llantas', index=['fabricante'], columns=['vendedor'], aggfunc='sum', fill_value=0)
        pivot_fabricante_vendedor.reset_index(inplace=True)
        pivot_fabricante_vendedor = pivot_fabricante_vendedor.reindex(columns= ['fabricante'] + vendedores, fill_value=0)
        
        query2 = """
            SELECT
            	rcs."name" AS estado,
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
                am.currency_id AS divisa
            FROM account_move_line aml 
            LEFT JOIN account_move am ON aml.move_id = am.id 
            LEFT JOIN product_product pp ON aml.product_id = pp.id
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
            LEFT JOIN ztyres_products_manufacturer zpm ON pt.manufacturer_id = zpm.id
            LEFT JOIN res_partner rp ON am.partner_id = rp.id
            LEFT JOIN res_users ru ON rp.user_id = ru.id
            LEFT JOIN res_partner rp2 ON ru.partner_id = rp2.id
            LEFT JOIN res_country_state rcs ON rp.state_id = rcs.id
            WHERE am.invoice_date BETWEEN %s AND %s
            AND am.state IN ('posted')
            AND am.move_type IN ('out_invoice', 'out_refund')
            AND pt.detailed_type IN ('product')
            AND aml.display_type IN ('product')
            GROUP BY rcs."name", zpm."name", rp2."name", pt.id, ru.id, am.invoice_date, am.currency_id, aml.move_id, am.currency_id
            ORDER BY rp2."name"
        """
        # Ejecutar la consulta
        self.env.cr.execute(query2, (primer_dia_año, ultimo_dia_año))
        result2 = self.env.cr.dictfetchall()
        df2 = pd.DataFrame(result2)
        
        df2['fecha'] = pd.to_datetime(df2['fecha'])
    
        df2['mes'] = df2['fecha'].dt.month.map(meses_es)
        df2.loc[df2['vendedor'].isin (ventas_lic), 'vendedor'] = 'RICARDO DE COSS'
        df2.loc[~df2['vendedor'].isin(vendedores_Actuales + ventas_lic), 'vendedor'] = 'OTROS'
        
        df2['subtotal'] = df2.apply(lambda row: self.convert_to_company_currency(row['divisa'], row['subtotal'], row['fecha']), axis=1)
        df2['vendedor'] = pd.Categorical(df2['vendedor'], categories=vendedores, ordered=True)
        
        orden_meses = [meses_es[m] for m in range(1, 13)]
        
        vendedores = [
            'Alvaro Ivan Andrade Rosales',
            'CHRISTIAN GUADALUPE NORIEGA PALACIOS',
            'DIEGO GOMEZ',
            'HUMBERTO MORENO',
            'JOSE AARON FONSECA RADA',
            'OTROS',
            'RICARDO DE COSS'
        ]
        
        #TABLA DE FACTURAS POR FABRICANTE Y VENDEDOR
        df_x_mes = df2.copy()
        df_x_mes = df_x_mes[(df_x_mes['fecha'] >= primer_dia_mes_actual) & (df_x_mes['fecha'] <= ultimo_dia_mes_actual)]
        pivot_fabricante_vendedor_fact = pd.pivot_table(df_x_mes, values='cantidad', index=['fabricante'], columns=['vendedor'], aggfunc='sum', fill_value=0)
        pivot_fabricante_vendedor_fact.reset_index(inplace=True)
        pivot_fabricante_vendedor_fact = pivot_fabricante_vendedor_fact.reindex(columns= ['fabricante'] + vendedores, fill_value=0)
        
        #TABLA DE FACTURAS POR FABRICANTE Y MES LLANTAS
        pivot_fabricante_mes = pd.pivot_table(df2, values='cantidad', index=['fabricante'], columns=['mes'], aggfunc='sum', fill_value=0)
        pivot_fabricante_mes = pivot_fabricante_mes.reset_index()
        pivot_fabricante_mes = pivot_fabricante_mes.reindex(columns=['fabricante'] + orden_meses, fill_value=0)
        
        #TABLA DE FACTURAS POR FABRICANTE Y MES SUBTOTAL
        pivot_fabricante_mes_subtotal = pd.pivot_table(df2, values='subtotal', index=['fabricante'], columns=['mes'], aggfunc='sum', fill_value=0)
        pivot_fabricante_mes_subtotal = pivot_fabricante_mes_subtotal.reset_index()
        pivot_fabricante_mes_subtotal = pivot_fabricante_mes_subtotal.reindex(columns= ['fabricante'] + orden_meses, fill_value=0)
        
        #TABLA DE FACTURAS POR MES Y VENDEDOR LLANTAS
        pivot_mes_vendedor = pd.pivot_table(df2, values='cantidad', index=['mes'], columns=['vendedor'], aggfunc='sum', fill_value=0)
        pivot_mes_vendedor = pivot_mes_vendedor.reset_index()
        pivot_mes_vendedor = pivot_mes_vendedor.reindex(columns= ['mes'] + vendedores, fill_value=0)
                # ordenar filas por mes
        pivot_mes_vendedor['mes'] = pd.Categorical(
            pivot_mes_vendedor['mes'],
            categories=orden_meses,
            ordered=True
        )

        pivot_mes_vendedor = pivot_mes_vendedor.sort_values('mes')
        
        
        #TABLA DE FACTURAS POR MES Y VENDEDOR SUBTOTAL
        pivot_mes_vendedor_subtotal = pd.pivot_table(df2, values='subtotal', index=['mes'], columns=['vendedor'], aggfunc='sum', fill_value=0)
        pivot_mes_vendedor_subtotal = pivot_mes_vendedor_subtotal.reset_index()
        pivot_mes_vendedor_subtotal = pivot_mes_vendedor_subtotal.reindex(columns= ['mes'] + vendedores, fill_value=0)
        # ordenar filas por mes
        pivot_mes_vendedor_subtotal['mes'] = pd.Categorical(
            pivot_mes_vendedor_subtotal['mes'],
            categories=orden_meses,
            ordered=True
        )

        pivot_mes_vendedor_subtotal = pivot_mes_vendedor_subtotal.sort_values('mes')
        
        

        #TABLA DE FACTURAS POR ESTADO Y MARCA
        pivot_estado_fabricante = pd.pivot_table(df_x_mes, values='cantidad', index=['fabricante'], columns=['estado'], aggfunc='sum', fill_value=0)
        pivot_estado_fabricante = pivot_estado_fabricante.reset_index()

        column_order = pivot_estado_fabricante.columns

        total_row = pivot_estado_fabricante.sum(numeric_only=True)
        total_row = total_row.reindex(column_order, fill_value=0)
        total_row['fabricante'] = 'Total'

        pivot_estado_fabricante = pd.concat(
            [pd.DataFrame([total_row]), pivot_estado_fabricante],
            ignore_index=True
        )

        # query3 = """
        #     SELECT 
        #         zpnc.nombre,
        #         rp.name AS cliente,
        #         rp2.name AS vendedor,
        #         zpm."name" AS fabricante,
        #         SUM(zpl.quantity) AS total_llantas,
        #         MAX(zpncl.total_nc_untaxed) AS total_nc_untaxed,
        #         zpnc.start_date,
        #         zpnc.end_date 
        #     FROM ztyres_promo_lines zpl
        #     JOIN ztyres_promo_notas_credito zpnc ON zpl.definitive_nc_id = zpnc.id
        #     JOIN ztyres_promo_notas_credito_lines zpncl 
        #         ON zpncl.definitive_nc_id = zpnc.id
        #         AND zpncl.partner_id = zpl.partner_id
        #         AND zpncl.total_nc_untaxed > 0
        #     JOIN res_partner rp ON zpl.partner_id = rp.id
        #     LEFT JOIN res_users ru ON rp.user_id = ru.id
        #     LEFT JOIN res_partner rp2 ON ru.partner_id = rp2.id
        #     JOIN (
        #         SELECT DISTINCT default_code, manufacturer_id
        #         FROM product_template
        #     ) pt ON zpl.product_code = pt.default_code 
        #     JOIN ztyres_products_manufacturer zpm ON pt.manufacturer_id = zpm.id
        #     WHERE zpl.state = 'valid'
        #     AND zpnc.start_date >= %s
        #     AND zpnc.end_date <= %s
        #     AND zpnc.status IN ('done')
        #     GROUP BY 
        #         zpnc.nombre,
        #         rp.name,
        #         rp2.name,
        #         zpm."name",
        #         zpnc.start_date,
        #         zpnc.end_date
        #     ORDER BY total_llantas DESC
        # """
        # # Ejecutar la consulta
        # self.env.cr.execute(query3, (primer_dia_año, ultimo_dia_año))
        # result3 = self.env.cr.dictfetchall()
        # df3 = pd.DataFrame(result3)
        
        # df3['start_date'] = pd.to_datetime(df3['start_date'])
        # df3['end_date'] = pd.to_datetime(df3['end_date'])
        # df3['mes'] = pd.to_datetime(df3['start_date']).dt.month.map(meses_es)
        # df3.loc[~df3['vendedor'].isin(vendedores_Actuales + ventas_lic), 'vendedor'] = 'OTROS'
        # df3['vendedor'] = pd.Categorical(df3['vendedor'], categories=vendedores, ordered=True)
        
        # #TABLA DE PROMOCIONES POR FABRICANTE Y VENDEDOR
        # df_promo_mes = df3.copy()
        # df_promo_mes = df_promo_mes[(df_promo_mes['start_date'] >= primer_dia_mes_actual) & (df_promo_mes['end_date'] <= ultimo_dia_mes_actual)]
        # pivot_fabricante_vendedor_promo = pd.pivot_table(df_promo_mes, values='total_llantas', index=['fabricante'], columns=['vendedor'], aggfunc='sum', fill_value=0)
        # pivot_fabricante_vendedor_promo.reset_index(inplace=True)
        # pivot_fabricante_vendedor_promo = pivot_fabricante_vendedor_promo.reindex(columns=['fabricante'] + vendedores, fill_value=0)
        # pivot_fabricante_vendedor_promo['Total'] = pivot_fabricante_vendedor_promo[vendedores].sum(axis=1)
        
        # #TABLA DE PROMOCIONES POR FABRICANTE Y MES
        # pivot_fabricante_mes_promo = pd.pivot_table(df3, values='total_llantas', index=['fabricante'], columns=['mes'], aggfunc='sum', fill_value=0)
        # pivot_fabricante_mes_promo = pivot_fabricante_mes_promo.reset_index()
        # pivot_fabricante_mes_promo = pivot_fabricante_mes_promo.reindex(columns= ['fabricante'] + orden_meses, fill_value=0)
        
        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(pivot_fabricante_vendedor, 'venta_diaria_cotizaciones')
        reports_core.action_insert_dataframe(pivot_fabricante_vendedor_fact, 'venta_diaria_facturas')
        reports_core.action_insert_dataframe(pivot_fabricante_mes, 'venta_por_marca')
        reports_core.action_insert_dataframe(pivot_fabricante_mes_subtotal, 'venta_por_marca_subtotal')
        reports_core.action_insert_dataframe(pivot_mes_vendedor, 'venta_por_mes_vendedor')
        reports_core.action_insert_dataframe(pivot_mes_vendedor_subtotal, 'venta_por_mes_vendedor_subtotal')
        reports_core.action_insert_dataframe(pivot_estado_fabricante, 'venta_por_estado_marca')
        # reports_core.action_insert_dataframe(pivot_fabricante_vendedor_promo, 'promociones_por_vendedor')
        # reports_core.action_insert_dataframe(pivot_fabricante_mes_promo, 'promociones_por_mes')