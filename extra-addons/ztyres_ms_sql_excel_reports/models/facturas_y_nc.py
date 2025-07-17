from openpyxl.styles import Font, PatternFill
from odoo.http import request, Response
from datetime import date, timedelta, datetime
import calendar
import pandas as pd
from odoo import api, fields, models
import re

class FacturasYNotasDeCredito(models.TransientModel):
    _name = 'facturas_y_notasdecredito'
    
    
    def sort_key(self, col):
        match = re.match(r'([A-Za-z]+)(\d+)', col)
        if match:
            return (match.group(1), int(match.group(2)))
        return (col, 0)  # fallback

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
        
        datos = []
        lista = []

        search_domain = [
                    ('move_type', 'in', ['out_invoice']),
                    ('state', 'in', ['posted']),
                    ('invoice_date', '>=', primer_dia_mes),
                    ('invoice_date', '<=', ultimo_dia_mes),
                ]

        records = self.env['account.move'].search(search_domain)

        # Extrae nombres de los registros relacionados
        for record in records:
            vals = {
                'Id': record.id,
                'Cliente': record.partner_id.name,
                'Factura': record.name,
                'Fecha': record.invoice_date,
                'Total': record.amount_total
            }
            datos.append(vals)

        df = pd.DataFrame(datos)

        query2 = """
                    SELECT 
                        am2.id AS id_fac,
                        apr.debit_amount_currency AS monto,
                        CASE 
                    		WHEN am.move_type = 'entry' THEN 'Pagos'
                    		WHEN am.move_type = 'out_refund' THEN 'NC'
                		END AS tipo
                    FROM account_partial_reconcile apr
                    JOIN account_move_line aml ON apr.credit_move_id = aml.id
                    JOIN account_move am ON aml.move_id = am.id
                    JOIN account_move_line aml2 ON apr.debit_move_id = aml2.id
                    JOIN account_move am2 ON aml2.move_id = am2.id
                    JOIN res_users ru ON apr.create_uid = ru.id
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
                            WHERE am.move_type IN ('out_invoice')
                            AND am.invoice_date BETWEEN %s AND %s
                        )
                    AND am.id IN (
                            SELECT am.id FROM account_move_line aml
                            JOIN account_move am ON aml.move_id = am.id
                            WHERE aml.display_type in ('product')
                        )
                """
        params = (primer_dia_mes, ultimo_dia_mes)
        self.env.cr.execute(query2, params)
        result2 = self.env.cr.dictfetchall()
        df2 = pd.DataFrame(result2)

        df2['tipo_num'] = df2.groupby(['id_fac', 'tipo']).cumcount() + 1
        df2['columna'] = df2['tipo'] + df2['tipo_num'].astype(str)
        
        df_pivot = df2.pivot(index='id_fac', columns='columna', values='monto').reset_index()
        df_pivot.fillna(0, inplace=True)
        
        merged_df = pd.merge(df, df_pivot, left_on='Id', right_on='id_fac', how='left')
        
        # Deja 'id_fac' primero, y ordena el resto
        cols = df_pivot.columns.tolist()
        id_col = ['Cliente', 'Factura', 'Fecha', 'Total']
        other_cols = sorted([col for col in cols if col != 'id_fac'], key=self.sort_key)

        merged_df = merged_df[id_col + other_cols]

        lista.append(('Facturas', merged_df))
        
        return lista