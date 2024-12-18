import io
import openpyxl
from openpyxl.styles import Font, PatternFill
from odoo.http import request, Response
from datetime import date, datetime
import calendar
import pandas as pd
import math
from odoo import api, fields, models

class AntiguedadDeSaldos(models.TransientModel):
    _name = 'antiguedad_de_saldos'

    def get_report(self, fecha):
        search_domain = [
            ('move_type', 'in', ['out_invoice']),
            ('state', 'in', ['posted']),
            ('invoice_date', '<=', fecha)
        ]
        
        datos = []
        lista = []
        
        records = self.env['account.move'].search(search_domain)

        # Extrae nombres de los registros relacionados
        for record in records:
            vals = {
                'Id': record.partner_id.id,
                'Cliente': record.partner_id.name,
                'RFC': record.edi_vat_receptor,
                'UUID': record.l10n_mx_edi_cfdi_uuid,
                'Dias de credito': record.partner_id.financial_profile.property_payment_term_id.name,
                'factura': record.name,
                'fecha factura': record.invoice_date,
                'Fecha límite': record.invoice_date_due,
                'TotalFac': record.amount_total,
                'Vendedor': record.invoice_user_id.name or '',
                #############################################################################################
                'divisa': record.currency_id.name
            }
            datos.append(vals)
        
        df = pd.DataFrame(datos)
        
        # Consulta consolidada para "Pagos" y "Notas de Crédito"
        query = """
            SELECT 
            	am2.id,
                am2."name" AS factura,
                rpu."name" AS cobrador,
                SUM(apr.debit_amount_currency) AS monto,
                am.currency_id AS divisa,
                CASE 
                    WHEN am.move_type = 'entry' THEN 'Pagos'
                    WHEN am.move_type = 'out_refund' THEN 'NC'
                END AS tipo
            FROM account_partial_reconcile apr
            JOIN account_move_line aml ON aml.id = apr.credit_move_id
            JOIN account_move am ON am.id = aml.move_id
            JOIN account_move_line aml2 ON aml2.id = apr.debit_move_id
            JOIN account_move am2 ON am2.id = aml2.move_id
            JOIN res_users ru ON apr.create_uid = ru.id
            JOIN res_partner rpu ON ru.partner_id = rpu.id
            WHERE am.move_type IN ('entry', 'out_refund')
            AND apr.credit_move_id IN (
                    SELECT aml.id 
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id 
                    JOIN account_account aa ON aa.id = aml.account_id 
                    WHERE aa.account_type = 'asset_receivable' 
                )
            AND apr.max_date <= %s
            GROUP BY am2."name", rpu."name", am.currency_id, am.move_type, am2.id
        """
        # Ejecutar la consulta y crear el DataFrame
        self.env.cr.execute(query, (fecha,))
        result = self.env.cr.dictfetchall()
        df2 = pd.DataFrame(result)

        #df2 = df2.drop(columns=['fecha'])
        df2['total_de_pagos'] = df2.groupby('factura')['monto'].transform('sum')

        df_pivoted = df2.pivot_table(index=['factura', 'total_de_pagos', 'cobrador'], 
                                            columns='tipo', 
                                            values='monto', 
                                            aggfunc='sum', 
                                            fill_value=0).reset_index()

        merged_df = pd.merge(df, df_pivoted, on='factura', how='left')
        
        merged_df['total_de_pagos'] = merged_df['total_de_pagos'].fillna(0)
        merged_df['restante'] = (merged_df['TotalFac'] - merged_df['total_de_pagos']).round(2)
        merged_df = merged_df.drop(merged_df[merged_df['restante'] == 0].index)
        merged_df = merged_df.drop(merged_df[merged_df['restante'] == ""].index)
        merged_df = merged_df.drop(columns=['total_de_pagos', 'cobrador'])
        
        new_names1 = {
            "Id": "ID Cliente",
            "Cliente": "Nombre del Cliente",
            "RFC": "RFC",
            "UUID": "UUID",
            "Dias de credito": "Días de crédito que tiene autorizados",
            "factura": "No. De Factura",
            "fecha factura": "Fecha de la Factura",
            "Fecha límite": "Fecha de Vencimiento",
            'divisa': 'Divisa',
            "TotalFac": "Importe de la Factura",
            "Pagos": "Importe por pagos realizados",
            "NC": "Importe de notas de crédito emitidas",
            "restante": "Saldo de la factura",
            "Vendedor": "Vendedor"
        }
        merged_df.rename(columns=new_names1, inplace=True)
        ordered_columns1 = list(new_names1.values())
        merged_df = merged_df[ordered_columns1]
        #####################################################################################################################################################
        merged_df['dias de atraso'] = (pd.to_datetime(fecha) - pd.to_datetime(merged_df['Fecha de Vencimiento'])).dt.days
        
        merged_df.loc[(merged_df['dias de atraso'] > 120), 'no c q poner :V'] = 'Más de 120'
        merged_df.loc[(merged_df['dias de atraso'] >= 91) & (merged_df['dias de atraso'] <= 120), 'no c q poner :V'] = '91-120'
        merged_df.loc[(merged_df['dias de atraso'] >= 61) & (merged_df['dias de atraso'] < 91), 'no c q poner :V'] = '61-90'
        merged_df.loc[(merged_df['dias de atraso'] >= 31) & (merged_df['dias de atraso'] < 61), 'no c q poner :V'] = '31-60'
        merged_df.loc[(merged_df['dias de atraso'] >= 1) & (merged_df['dias de atraso'] < 31), 'no c q poner :V'] = '1-30'
        merged_df.loc[(merged_df['dias de atraso'] < 1), 'no c q poner :V'] = 'En fecha'

        df_pivoted2 = merged_df.pivot_table(index=['ID Cliente', 'Nombre del Cliente', 'Vendedor', 'No. De Factura', 'Fecha de la Factura', 
                                                   'Fecha de Vencimiento', 'Divisa', 'Importe de la Factura'], 
                                            columns='no c q poner :V', 
                                            values='Saldo de la factura', 
                                            aggfunc='sum', 
                                            fill_value=0).reset_index()
        
        merged_df = merged_df.drop(columns=['dias de atraso', 'no c q poner :V'])
        
        lista.append(('integración de saldos', merged_df))
        #####################################################################################################################################################
        new_names2 = {
            "ID Cliente": "ID Cliente",
            "Nombre del Cliente": "Nombre del Cliente",
            "Vendedor": "Vendedor",
            "No. De Factura": "No. De Factura",
            "Fecha de la Factura": "Fecha de la Factura",
            "Fecha de Vencimiento": "Fecha de Vencimiento",
            'Divisa': 'Divisa',
            "Importe de la Factura": "Importe de la Factura",
            "En fecha": "En fecha",
            "1-30": "1-30",
            "31-60": "31-60",
            "61-90": "61-90",
            "91-120": "91-120",
            "Más de 120": "Más de 120"
        }
        df_pivoted2.rename(columns=new_names2, inplace=True)
        ordered_columns2 = list(new_names2.values())
        df_pivoted2 = df_pivoted2[ordered_columns2]
        
        lista.append(('Antiguedad de saldos', df_pivoted2))
        
        return lista