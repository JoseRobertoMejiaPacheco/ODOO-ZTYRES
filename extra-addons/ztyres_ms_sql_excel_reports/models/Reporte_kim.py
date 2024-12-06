import pandas as pd
import math

search_domain = [
    ('move_type', 'in', ['out_invoice']),
    ('state', 'in', ['posted'])
]

datos = []

records = self.env['account.move'].search(search_domain)

# Extrae nombres de los registros relacionados
for record in records:
    vals = {
        'factura': record.name,
        'Cliente': record.partner_id.name,
        'Vendedor': record.invoice_user_id.name or '',
        'TotalFac': record.amount_total,
        'fecha factura': record.invoice_date,
        'Fecha límite': record.invoice_date_due,
        'divisa': record.currency_id.name
    }
    datos.append(vals)

df = pd.DataFrame(datos)
df = df.drop(columns=['TotalFac'])

# Consulta consolidada para "Pagos" y "Notas de Crédito"
query = """
    SELECT 
        am2."name" AS factura,
        rpu."name" AS cobrador,
        SUM(apr.debit_amount_currency) AS monto,
        DATE(apr.max_date) AS fecha_aplicación,
        DATE(am.date) AS fecha,
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
    GROUP BY am2."name", rpu."name", apr.max_date, am.currency_id, am.date, am.move_type
"""
# Ejecutar la consulta y crear el DataFrame
self.env.cr.execute(query)
result = self.env.cr.dictfetchall()
df2 = pd.DataFrame(result)

df2 = df2.drop(columns=['fecha'])

df_pivoted = df2.pivot_table(index=['factura', 'cobrador', 'fecha_aplicación'], 
                                    columns='tipo', 
                                    values='monto', 
                                    aggfunc='sum', 
                                    fill_value=0).reset_index()

merged_df = pd.merge(df, df_pivoted, on='factura', how='left')

#####################################################################################################################################################
query2 = """
    SELECT rp."name" AS cliente, 
           am."name" AS factura, 
           am.amount_total AS total, 
           am.invoice_date AS fecha_factura,
           am.invoice_date_due AS fecha_limite
    FROM account_move am 
    JOIN res_partner rp ON am.partner_id = rp.id 
    WHERE am.amount_residual <> 0
    AND am.move_type IN ('out_invoice', 'out_refund')
    AND state IN ('posted')
"""

self.env.cr.execute(query2)
result2 = self.env.cr.dictfetchall()
df3 = pd.DataFrame(result2)

query3 = """
    SELECT 
        am2."name" AS factura,
        rpu."name" AS cobrador,
        SUM(apr.debit_amount_currency) AS monto,
        DATE(apr.max_date) AS fecha_aplicación,
        DATE(am.date) AS fecha,
        am.currency_id AS divisa
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
    AND am2.amount_residual != 0
    AND apr.max_date >= '2024-12-02'
    GROUP BY am2."name", rpu."name", apr.max_date, am.currency_id, am.date, am.move_type
"""
# Ejecutar la consulta y crear el DataFrame
self.env.cr.execute(query3)
result3 = self.env.cr.dictfetchall()
df4 = pd.DataFrame(result3)

merged_df2 = pd.merge(df3, df4, on='factura', how='left')
merged_df2['monto'] = merged_df2['monto'].fillna(0)

#REEMPLAZAR FECHA DE ACUERDO A LO SOLICITADO "pd.to_datetime('2023-11-27')" Y apr.max_date EN LA CONULTA SQL (TIENEN QUE SER IGUALES)
merged_df2['dias de atraso'] = (pd.to_datetime('2024-12-02') - pd.to_datetime(merged_df2['fecha_limite'])).dt.days
merged_df2['restante'] = merged_df2['total'] - merged_df2['monto']
merged_df2.loc[(merged_df2['dias de atraso'] > 120), 'no c q poner :V'] = 'Antiguos'
merged_df2.loc[(merged_df2['dias de atraso'] >= 91) & (merged_df2['dias de atraso'] <= 120), 'no c q poner :V'] = '91 - 120'
merged_df2.loc[(merged_df2['dias de atraso'] >= 61) & (merged_df2['dias de atraso'] < 91), 'no c q poner :V'] = '61 - 90'
merged_df2.loc[(merged_df2['dias de atraso'] >= 31) & (merged_df2['dias de atraso'] < 61), 'no c q poner :V'] = '31 - 60'
merged_df2.loc[(merged_df2['dias de atraso'] >= 1) & (merged_df2['dias de atraso'] < 31), 'no c q poner :V'] = '1 - 30'
merged_df2.loc[(merged_df2['dias de atraso'] < 1), 'no c q poner :V'] = 'En fecha'

df_pivoted2 = merged_df2.pivot_table(index=['factura', 'total'], 
                                    columns='no c q poner :V', 
                                    values='restante', 
                                    aggfunc='sum', 
                                    fill_value=0).reset_index()

#####################################################################################################################################################

merged_df3 = pd.merge(merged_df, df_pivoted2, on='factura', how='left')

merged_df3.to_excel('/mnt/extra-addons/Reporte Kim 02.xlsx') 