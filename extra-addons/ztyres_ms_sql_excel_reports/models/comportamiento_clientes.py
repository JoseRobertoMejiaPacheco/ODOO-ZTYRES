from odoo import api, fields, models
import pandas as pd
import math
from datetime import datetime, date,timedelta
from dateutil.relativedelta import relativedelta

class ComportamientoClientes(models.TransientModel):
    _name = 'comportamiento_clientes'

    def convert_to_company_currency(self, currency_id, amount, date):
        currency_record = self.env['res.currency'].browse(currency_id.id)
        converted_amount = currency_record._convert(
            amount,
            currency_record.env.company.currency_id,
            currency_record.env.company,
            date
        )
        return converted_amount if converted_amount else 0    
    
    def get_report(self):
        
        lista = []
        datos = []
        
        hoy = date.today()

        primer_dia_mes_actual = hoy.replace(day=1)
        ultimo_dia_intervalo = primer_dia_mes_actual - timedelta(days=1)
        primer_dia_intervalo = primer_dia_mes_actual - relativedelta(months=12)
        
        search_domain = [
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', 'in', ['posted']),
            ('invoice_date_due', '>=', primer_dia_intervalo),
            ('invoice_date_due', '<=', ultimo_dia_intervalo),
            ('partner_id', 'not in', [11296, 11298, 11297, 11299, 8355]),
        ]

        records = self.env['account.move'].search(search_domain)

        # Extrae nombres de los registros relacionados
        for record in records:
            vals = {
                'factura': record.name,
                'Cliente': record.partner_id.name,
                'Grupo': record.partner_id.x_studio_grupo or '',
                'limite credito': record.partner_id.credit_limit,
                'Vendedor': record.invoice_user_id.name or '',
                'fecha factura': record.invoice_date,
                'Fecha límite': record.invoice_date_due,
                'dias de credito': (record.invoice_date_due - record.invoice_date).days if record.invoice_date and record.invoice_date_due else None,
                'TotalFac': record.amount_total,
                'divisa': record.currency_id.name,
                'move_type': record.move_type,
                'tipo' : record.x_studio_tipo,
                'piezas' : record.x_studio_piezas_facturadas
            }
            datos.append(vals)

        df = pd.DataFrame(datos)
        
        df10 = df[(df['move_type'].isin(['out_invoice']))]
        df10 = df10.drop(columns=['move_type', 'tipo'])
        
        df10["fecha factura"] = pd.to_datetime(df10["fecha factura"], errors="coerce")
        df10['Compras mensuales $'] = (df10.groupby([df10['Cliente'], df10['fecha factura'].dt.to_period('M')])['TotalFac'].transform('sum'))
        
        df10['Piezas mensuales'] = (df10.groupby([df10['Cliente'], df10['fecha factura'].dt.to_period('M')])['piezas'].transform('sum'))

        #df = df.drop(columns=['divisa'])
        
        # Consulta consolidada para "Pagos" y "Notas de Crédito", (11296, 11298, 11297, 11299, 8355)
        query = """
            SELECT 
                am2."name" AS factura,
                SUM(apr.debit_amount_currency) AS Pagos,
                MAX(am.date) FILTER (WHERE am.move_type = 'entry') AS ultima_fecha_aplicación,
                am.currency_id AS divisa,
                am2.amount_residual AS monto_restante
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
            AND am2.invoice_date_due BETWEEN %s AND %s
            AND apr.debit_amount_currency <> 0
            AND am2.partner_id NOT IN (11296, 11298, 11297, 11299, 8355)
            GROUP BY am2."name", am.currency_id, am2.amount_residual;

        """
        # Ejecutar la consulta y crear el DataFrame
        self.env.cr.execute(query, (primer_dia_intervalo, ultimo_dia_intervalo))
        result = self.env.cr.dictfetchall()
        df2 = pd.DataFrame(result)

        df2 = df2.drop(columns=['divisa'])
        

        merged_df = pd.merge(df10, df2, on='factura', how='left')
        
        merged_df.loc[merged_df['pagos'].isna(), 'monto_restante'] = merged_df['TotalFac']
        
        merged_df['monto_restante'] = merged_df['monto_restante'].fillna(0)
        
        merged_df = merged_df.rename(columns={'monto_restante': 'monto restante'})
        
        merged_df["ultima_fecha_aplicación"] = pd.to_datetime(merged_df["ultima_fecha_aplicación"], errors="coerce")
        merged_df["Fecha límite"] = pd.to_datetime(merged_df["Fecha límite"], errors="coerce")
        merged_df["ultima_fecha_aplicación"].fillna(pd.Timestamp.today().normalize(), inplace=True)
        merged_df["dias de atraso"] = (merged_df["ultima_fecha_aplicación"] - merged_df["Fecha límite"]).dt.days.clip(lower=0)
        
        cols = ['Cliente'] + [col for col in merged_df.columns if col != 'Cliente']
        merged_df = merged_df[cols]
        
        merged_df.sort_values(by=['Cliente'], inplace=True)
        
        merged_df['atrasos dias prom ponderado'] = (
            merged_df.groupby('Cliente')['dias de atraso']
            .transform(lambda s: (s * merged_df.loc[s.index, 'TotalFac']).sum() / merged_df.loc[s.index, 'TotalFac'].sum())
            .round(2)
        )
        

        #merged_df['atrasos dias prom (%)'] = (
        #    (merged_df.groupby('Cliente')['dias de atraso'].transform('sum') / merged_df.groupby('Cliente')['dias de credito'].transform('sum')).clip(lower=0) * 100).round(2)
        #merged_df['atrasos dias prom (%)'] = merged_df['atrasos dias prom (%)'].fillna(0).replace([math.inf, -math.inf], 0)
        
        merged_df['atraso en dinero (%)'] = (
            (merged_df.groupby('Cliente')['monto restante'].transform('sum') / merged_df.groupby('Cliente')['TotalFac'].transform('sum')).clip(lower=0) * 100).round(2)
        merged_df['atraso en dinero (%)'] = merged_df['atraso en dinero (%)'].fillna(0).replace([math.inf, -math.inf], 0)
        
        merged_df['atraso en facturas (%)'] = (
            (merged_df.groupby('Cliente')['dias de atraso'].transform(lambda x: (x > 0).sum()) / merged_df.groupby('Cliente')['factura'].transform('count')) * 100).round(2)
        
        merged_df['# Facturas'] = merged_df.groupby('Cliente')['factura'].transform('count')
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        df20 = df[(df['move_type'].isin(['out_refund']) & (df['tipo'].isin(['Devolución'])))]
        df20 = df20.drop(columns=['move_type', 'tipo'])
        
        df20 = df20.groupby('Cliente', as_index=False)['TotalFac'].sum()
        df20 = df20.rename(columns={'TotalFac': 'Devoluciones'})
        
        merged_df2 = pd.merge(merged_df, df20, on='Cliente', how='left')
        
        query3 = """
            select rp."name" as cliente, 
                so.unlock_financial as autorizaciones
            from sale_order so 
            join res_partner rp on so.partner_id = rp.id
            where so.state in ('sale')
            and so.date_order between %s and %s
            and so.unlock_financial in (True)
            and so.partner_id not in (11296, 11298, 11297, 11299, 8355)
        """
        # Ejecutar la consulta y crear el DataFrame
        self.env.cr.execute(query3, (primer_dia_intervalo, ultimo_dia_intervalo))
        result3 = self.env.cr.dictfetchall()
        df4 = pd.DataFrame(result3)
        df4 = df4.rename(columns={'cliente': 'Cliente'})
        
        df4 = df4.groupby('Cliente', as_index=False)['autorizaciones'].count()
        
        merged_df4 = pd.merge(merged_df2, df4, on='Cliente', how='left')
        
        ordered_columns = [
            'Cliente', 
            'Grupo',
            'limite credito',
            'Compras mensuales $', 
            'Piezas mensuales', 
            'factura',
            'fecha factura', 
            'Fecha límite',
            'TotalFac',
            'dias de credito',
            'pagos',
            'ultima_fecha_aplicación',
            'monto restante',
            'dias de atraso',
            'atrasos dias prom ponderado', 
            'atraso en dinero (%)', 
            'atraso en facturas (%)', 
            '# Facturas', 
            'Devoluciones', 
            'autorizaciones', 
        ]
        
        merged_df4 = merged_df4[ordered_columns]
        
        lista.append(("Comportamiento", merged_df4))
                    
        return lista