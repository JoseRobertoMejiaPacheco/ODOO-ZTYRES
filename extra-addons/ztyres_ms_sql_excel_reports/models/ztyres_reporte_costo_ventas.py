from odoo import api, fields, models
import math
import pandas as pd
import datetime
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

class ReservacostoVentas(models.TransientModel):
    _name = 'ztyres_reporte_costo_ventas'

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
            SELECT am.invoice_date AS fecha_factura,
         		   aml.move_id, 
                   aml.move_name, 
                   zpm."name" AS fabricante,
                   pp.default_code, 
                   aml."name" AS producto,
                   zptm."name" AS medida,
                   zps."name" AS segmento,
                   zpt."name" AS tipo,
                   CASE 
                       WHEN am.move_type in ('out_refund') THEN -aml.quantity
                       ELSE aml.quantity
                   END as Cantidad,
                   aml.price_unit AS precio_unitario,
                   aml.discount AS descuento_aplicado,
                   CASE 
                   		WHEN pol.x_studio_costo_final = 0 THEN pol.price_unit
                   		ELSE  pol.x_studio_costo_final
                   END AS costo_compra,
                   pol.tipo_cambio AS tipo_cambio,
                   pol.fecha_compra AS fecha_compra,
                   aml2.price_unit,
                   aml2.tipo_cambio2,
                   aml2.fecha_compra2
            FROM account_move_line aml 
            JOIN product_product pp ON aml.product_id = pp.id
            JOIN account_move am ON aml.move_id = am.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id 
            JOIN ztyres_products_manufacturer zpm ON pt.manufacturer_id = zpm.id 
            JOIN ztyres_products_tire_measure zptm ON pt.tire_measure_id = zptm.id 
            JOIN ztyres_products_segment zps ON pt.segment_id = zps.id  
            JOIN ztyres_products_type zpt ON pt.type_id = zpt.id 
            LEFT JOIN (
                SELECT DISTINCT ON (pt.id)
                    pt.id AS id,
                    pp.id as id2,
                    pol.price_unit AS price_unit,  
                    pol.x_studio_costo_final AS x_studio_costo_final,
                    po.currency_id AS tipo_cambio,
                    po.date_order AS fecha_compra
                FROM product_template pt
                JOIN product_product pp ON pt.id = pp.product_tmpl_id
                JOIN purchase_order_line pol ON pp.id = pol.product_id
                JOIN purchase_order po ON pol.order_id = po.id
                WHERE po.state = 'purchase'
                ORDER BY pt.id, po.date_order DESC
            ) AS pol ON pp.id = pol.id2
            LEFT JOIN (
            	SELECT DISTINCT ON (pt.id)
                    pt.id AS id,
                    pp.id as id2,
                    aml.price_unit AS price_unit,  
                    am.currency_id AS tipo_cambio2,
                    am.invoice_date as fecha_compra2
                FROM product_template pt
                JOIN product_product pp ON pt.id = pp.product_tmpl_id
                JOIN account_move_line aml ON pp.id = aml.product_id
                JOIN account_move am ON aml.move_id = am.id
                WHERE aml.display_type = 'product'
            	AND pt.detailed_type = 'product'
            	AND am.move_type IN ('in_invoice', 'in_refund')
            	AND am.state = 'posted'
            	ORDER BY pt.id, am.invoice_date DESC
            ) AS aml2 ON pp.id = aml2.id2
            WHERE aml.display_type = 'product'
            AND pt.detailed_type = 'product'
            AND am.move_type IN ('out_invoice', 'out_refund')
            AND am.state = 'posted'
        """
        ##Retornar la consulta sql
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()        
        #Crear dataframe dla consulta
        df = pd.DataFrame(result)
        #---------------------------------------------------------------------------------------------------------------
        fecha_actual = date.today()
        # Obtén el primer día del mes actual
        primer_dia_mes = fecha_actual.replace(day=1)
        ultimo_dia_mes = primer_dia_mes.replace(day=28)  # Establece inicialmente el día 28
        ultimo_dia_mes = ultimo_dia_mes + pd.offsets.MonthEnd(0)  # Ajusta al último día del mes

        df = df.loc[(df['fecha_factura'] >= primer_dia_mes) & (df['fecha_factura'] <= ultimo_dia_mes)]
        #---------------------------------------------------------------------------------------------------------------
        
        df['costo_de_compra'] = df.apply(lambda row: self.convert_to_company_currency(row['tipo_cambio'], row['costo_compra'], row['fecha_compra']), axis=1)
        
        df['costo_factura'] = df.apply(lambda row: self.convert_to_company_currency(row['tipo_cambio2'], row['price_unit'], row['fecha_compra2']), axis=1)
        
        df['precio_unitario'] *= (1 - (df['descuento_aplicado']/100))
        
        columnas_seleccionadas = df[['fecha_factura', 'move_id', 'move_name', 'fabricante', 'default_code', 'producto', 'medida', 'segmento', 'tipo', 'cantidad', 'precio_unitario', 'costo_de_compra', 'costo_factura']]

        ##Instanciar la clase ztyres_ms_sql_excel_core que tiene el metodo para insertar un dataframe en sql server
        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(columnas_seleccionadas, 'reporte_costo_ventas')
        return 
    