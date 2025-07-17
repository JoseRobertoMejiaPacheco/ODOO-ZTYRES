from odoo.http import request, Response
from datetime import date, datetime
import pandas as pd
import calendar
from odoo import api, fields, models

class VentasAcumuladas(models.TransientModel):
    _name = 'ventas_acumuladas'

    def get_report(self, mes, anio):
        
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        mes = mes.lower()
        
        if mes not in meses:
            raise ValueError(f"Nombre del mes '{mes}' no es válido.")
        
        mes_numero = meses[mes]
        
        # Obtener primer y último día del mes
        primer_dia = datetime(anio, mes_numero, 1)
        ultimo_dia = datetime(anio, mes_numero, calendar.monthrange(anio, mes_numero)[1])
        
        primer_dia_mes = pd.to_datetime(primer_dia)
        ultimo_dia_mes = pd.to_datetime(ultimo_dia)
        
        lista = []
        datos = []

        search_domain = [
                    ('move_id.move_type', 'in', ['out_invoice']),
                    ('move_id.state', 'in', ['posted']),
                    ('display_type',  '=', 'product'),
                    ('product_id.product_tmpl_id.detailed_type', '=', 'product'),
                    ('move_id.invoice_date', '>=', primer_dia_mes),
                    ('move_id.invoice_date', '<=', ultimo_dia_mes),
                    ('move_id.partner_id.id', 'in', [7102, 7181, 7101, 6994, 7097, 11190, 11202, 10938]),
                ]

        records = self.env['account.move.line'].search(search_domain)

        # Extrae nombres de los registros relacionados
        for record in records:
            vals = {
                'Id': record.move_id.id,
                'Cliente': record.move_id.partner_id.name,
                'Factura': record.move_id.name,
                'Fecha': record.move_id.invoice_date,
                'Producto': record.product_id.name,
                'Fabricante': record.product_id.manufacturer_id.name,
                'Lista origen': record.list_origin,
                'Cantidad': record.quantity * -1 if record.move_id.move_type == 'out_refund' else record.quantity,
                'Total': (record.price_subtotal * 1.16) * -1 if record.move_id.move_type == 'out_refund' else (record.price_subtotal * 1.16),
            }
            datos.append(vals)

        df = pd.DataFrame(datos)


        query2 = """
            SELECT 
                am.id AS id_nc,
                am."name" AS nc,
                am2.id AS id_fac,
                am2."name" AS factura,
                am2.x_studio_piezas_facturadas as total_llantas,
                aml.id as no_c,
                aml."name" as producto,
                am.payment_reference as aaaaahhh,
                SUM(apr.debit_amount_currency) AS monto,
                am.currency_id AS divisa,
                CASE 
                    WHEN am.move_type = 'entry' THEN 'Pagos'
                    WHEN am.move_type = 'out_refund' THEN 'NC'
                END AS tipo
            FROM account_partial_reconcile apr
            LEFT JOIN account_move_line aml ON apr.credit_move_id = aml.id
            LEFT JOIN account_move am ON aml.move_id = am.id
            LEFT JOIN account_move_line aml2 ON apr.debit_move_id = aml2.id
            LEFT JOIN account_move am2 ON aml2.move_id = am2.id
            LEFT JOIN res_users ru ON apr.create_uid = ru.id
            WHERE am.move_type IN ('out_refund', 'entry')
            AND apr.credit_move_id IN (
                    SELECT aml.id 
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id 
                    JOIN account_account aa ON aa.id = aml.account_id 
                    WHERE aa.account_type = 'asset_receivable' 
                )
            AND aml2.id IN (
            		SELECT aml.id FROM account_move_line aml
        			JOIN account_move am ON aml.move_id = am.id
        			WHERE am.partner_id IN (7102, 7181, 7101, 6994, 7097, 11190, 11202, 10938)
        			AND am.invoice_date BETWEEN %s AND %s
        			AND am.move_type IN ('out_invoice')
                )
            AND am.id IN (
                   	SELECT am.id FROM account_move_line aml
            		JOIN account_move am ON aml.move_id = am.id
            		WHERE aml.display_type in ('product')
            		AND aml."name" LIKE (%s)
                )
            GROUP BY am2."name", am.currency_id, am.move_type, am.id, am2.id, aml2.product_id, aml."name", aml.id, am."name", am.payment_reference
                """
        params = ("%Logistico%",)
        self.env.cr.execute(query2, (primer_dia_mes, ultimo_dia_mes, params))
        result2 = self.env.cr.dictfetchall()
        df2 = pd.DataFrame(result2)

        merged_df = df.merge(df2[['id_fac', 'total_llantas']], left_on='Id', right_on='id_fac', how='left')

        merged_df.drop(columns=['id_fac'], inplace=True)

        merged_df.loc[(merged_df['Lista origen'] != 'OUTLET') & (merged_df['total_llantas'] >= 300), 'Desc. Aplicado'] = '4%'
        merged_df.loc[(merged_df['Lista origen'] != 'OUTLET') & (merged_df['total_llantas'] >= 100) & (merged_df['total_llantas'] < 300), 'Desc. Aplicado'] = '2%'

        if 'Desc. Aplicado' not in merged_df.columns:
            merged_df['Desc. Aplicado'] = '0%'  # O un valor por defecto

        merged_df['Desc. Aplicado'] = merged_df['Desc. Aplicado'].str.rstrip('%').astype(float) / 100

        merged_df.loc[(merged_df['Fabricante'] == 'BRIDGESTONE') & (merged_df['Lista origen'] == 'MAYOREO'), 'Desc. en monto'] = (merged_df['Total'] * 0.9) * merged_df['Desc. Aplicado']

        merged_df.loc[(merged_df['Fabricante'] != 'BRIDGESTONE') & (merged_df['Lista origen'] != 'OUTLET'), 'Desc. en monto'] = merged_df['Total'] * merged_df['Desc. Aplicado']

        lista.append(('Reporte Venta Mensual', merged_df))
        
        return lista