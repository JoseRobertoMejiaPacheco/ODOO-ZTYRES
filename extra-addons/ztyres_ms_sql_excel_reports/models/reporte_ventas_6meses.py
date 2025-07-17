from odoo import api, fields, models
import pandas as pd
import math
import numpy as np
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class Ventas6Meses(models.TransientModel):
    
    _name = 'ventas_6_meses'
    
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
        
        lista = []
        
        # Obtener la fecha actual
        fecha_actual = pd.Timestamp.today()
        
        meses_mapping = {
            "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
            "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
            "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
        }
        
        ultimos_6_meses = pd.date_range(end=fecha_actual, periods=6, freq='MS').strftime('%B')

        query = """
            SELECT
                rp."name" AS cliente,
                pt."name" ->> 'en_US' AS producto,
                (CASE 
            	    WHEN am.move_type = 'out_refund'
            	        THEN aml.quantity * -1 
            	        ELSE aml.quantity 
                    END) AS cantidad,
                aml.price_total AS total,
                aml.currency_id AS divisa,
                am.invoice_date AS fecha_factura
            FROM account_move_line aml
            JOIN account_move am ON aml.move_id = am.id
            JOIN product_product pp ON aml.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            JOIN ztyres_products_manufacturer zpm ON pt.manufacturer_id = zpm.id
            JOIN res_partner rp ON am.partner_id = rp.id
            WHERE am.state IN ('posted')
            AND am.move_type IN ('out_invoice', 'out_refund')
            AND pt.detailed_type IN ('product')
            AND aml.display_type IN ('product')
            AND zpm."name" IN ('BRIDGESTONE')
            """
        ##Retornar la consulta sql
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall() 
        df = pd.DataFrame(result)

        df['pesos'] = df.apply(lambda row: self.convert_to_company_currency(row['divisa'], row['total'], row['fecha_factura']), axis=1)

        # Convertir la columna fecha_factura a datetime
        df['fecha_factura'] = pd.to_datetime(df['fecha_factura'])
        
        # Calcular el primer día del mes hace 6 meses
        primer_dia_mes_antiguo = fecha_actual - pd.DateOffset(months=6) + pd.offsets.MonthBegin(1)

        df = df[(df['fecha_factura'] >= primer_dia_mes_antiguo) & (df['fecha_factura'] <= fecha_actual)]
        
        df['mes'] = df['fecha_factura'].dt.month_name().replace(meses_mapping)
        
        orden_meses = [meses_mapping[m] for m in ultimos_6_meses]
        
        df['mes'] = pd.Categorical(df['mes'], categories=orden_meses, ordered=True)
        
        df_pivoted = df.pivot_table(index=['cliente'], 
                                    columns='mes', 
                                    values=['cantidad', 'pesos'], 
                                    aggfunc='sum', 
                                    fill_value=0)
        
        lista.append(('Venta 6 Menses', df_pivoted))
        lista.append(('Venta 6', df))
        
        return lista