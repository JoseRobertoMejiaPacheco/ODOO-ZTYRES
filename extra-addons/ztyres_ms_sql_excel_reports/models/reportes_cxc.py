from odoo import api, fields, models
import pandas as pd
from pandas.api.types import CategoricalDtype
from datetime import datetime, timedelta, date
import calendar
from dateutil.relativedelta import relativedelta

class reportescxc(models.TransientModel):

    _name = 'reportes_cobranza'
    
    def convert_to_company_currency(self, currency_id, amount, date):
        # Si divisa o amount están en NaN → regresar sin convertir
        if pd.isna(currency_id) or pd.isna(amount):
            return amount
        
        currency_id = self.env['res.currency'].browse(currency_id)
        converted_amount = currency_id._convert(
            amount,
            currency_id.env.company.currency_id,
            currency_id.env.company,
            date
        )
        return converted_amount

    def get_report(self, mes, anio):
        hoy = pd.Timestamp.today().normalize()
        
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        mes = mes.lower()
        
        if mes not in meses:
            raise ValueError(f"Nombre del mes '{mes}' no es válido.")
        
        mes_numero = meses[mes]

        primer_dia_año = date(anio, 1, 1)
        ultimo_dia_año = date(anio, 12, calendar.monthrange(anio, 12)[1])
        
        año_inicio = pd.to_datetime(primer_dia_año)
        año_fin = pd.to_datetime(ultimo_dia_año)
        
        primer_dia_mes = datetime(anio, mes_numero, 1)
        ultimo_dia_mes = datetime(anio, mes_numero, calendar.monthrange(anio, mes_numero)[1])
    
        mes_inicio = pd.to_datetime(primer_dia_mes)
        mes_fin = pd.to_datetime(ultimo_dia_mes)
        
        lista = []
        
        meses_mapping = {
            "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
            "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
            "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
        }

        status_clientes = [
            ('VICTOR HUGO VARGAS ZARAGOZA', 'EXTRAJUDICIAL'),
            ('TEREZA GARCIA MERCADO', 'EXTRAJUDICIAL'),
            ('RUBEN AYALA QUINTERO', 'EXTRAJUDICIAL'),
            ('ROBERTO GONTES LEON', 'EXTRAJUDICIAL'),
            ('RINES Y LLANTAS DE GDL', 'EXTRAJUDICIAL'),
            ('OSCAR ADRIAN HIGUERA MARTINEZ', 'EXTRAJUDICIAL'),
            ('NEUMATICOS Y RINES INDUSTRIALES', 'EXTRAJUDICIAL'),
            ('MAURICIO ALVA MARTINEZ', 'EXTRAJUDICIAL'),
            ('MARISOL GONZALEZ MENDOZA', 'EXTRAJUDICIAL'),
            ('LLANTERA LOMELI', 'EXTRAJUDICIAL'),
            ('KEVIN YERAY GARCIA MERCADO', 'EXTRAJUDICIAL'),
            ('JOSE ANTONIO ABONCE VILLAGOMEZ', 'EXTRAJUDICIAL'),
            ('JAIME DEL RIO MENDOZA', 'EXTRAJUDICIAL'),
            ('IDEAL LLANTA', 'EXTRAJUDICIAL'),
            ('GONTEZ MULTILLANTAS', 'EXTRAJUDICIAL'),
            ('FRANCISCO EMMANUEL PEREZ CASTRO', 'EXTRAJUDICIAL'),
            ('EMMANUEL CARBAJAL ZEPEDA', 'EXTRAJUDICIAL'),
            ('COMERCIALIZADORA PEGUZA', 'EXTRAJUDICIAL'),
            ('CIPRIANO ONTIVEROS CAMPOS', 'EXTRAJUDICIAL'),
            ('ALDAHIR ANTONIO LOPEZ SERAFIN', 'EXTRAJUDICIAL'),
            ('GL TIRES GRUP', 'EXTRAJUDICIAL')
        ]

        search_domain = [
            '|',  # <-- Este OR combina las dos siguientes condiciones
            '&',  # <-- Primer bloque: fecha >= y <=
                ('invoice_date_due', '>=', año_inicio),
                ('invoice_date_due', '<=', año_fin),
            ('amount_residual', '>', 0),
            ('move_type', 'in', ['out_invoice']),  # aquí junto ambas
            ('state', 'in', ['posted']),
            ('partner_id', 'not in', [11296, 11298, 11297, 11299, 8355])
            ]

        datos = []

        records = self.env['account.move'].search(search_domain)

        # Extrae nombres de los registros relacionados
        for record in records:
            
            lineas = record.line_ids.filtered(lambda l: l.account_id.reconcile)

            partials = lineas.matched_credit_ids

            notas_credito_pr = partials.filtered(lambda pr: pr.credit_move_id.move_id.move_type == 'out_refund')

            total_nc = sum(notas_credito_pr.mapped('amount'))
            #print (total_nc)
            
            vals = {
                'factura': record.name,
                'Cliente': record.partner_id.name,
                'Términos de pago del cliente': record.partner_id.property_payment_term_id.name,
                'Vendedor': record.invoice_user_id.name or '',
                'fecha factura': record.invoice_date,
                'Fecha límite': record.invoice_date_due,
                'por vencer': record.amount_total,
                'importe adeudado': record.amount_residual,
                'divisa': record.currency_id.id,
                'NC aplicada': total_nc
            }
            clientes_dict = {t[0]: t[1] for t in status_clientes}
            if record.partner_id.name in clientes_dict:
                vals.update({'Status': clientes_dict[record.partner_id.name]})
            else:
                vals.update({'Status': 'COBRANZA'})
            datos.append(vals)

        df = pd.DataFrame(datos)
        
        df['Fecha límite'] = pd.to_datetime(df['Fecha límite'])
        
        df['dias de atraso'] = (hoy - df['Fecha límite']).dt.days
        
        df['mes'] = (
            df['Fecha límite'].dt.month_name().replace(meses_mapping) + " " +
            df['Fecha límite'].dt.year.astype(str)
        )

        df['mes_aux'] = df['Fecha límite'].dt.to_period('M').dt.to_timestamp()
        
        df['por vencer'] = df.apply(lambda row: self.convert_to_company_currency(row['divisa'], row['por vencer'], row['fecha factura']), axis=1)
        df['importe adeudado'] = df.apply(lambda row: self.convert_to_company_currency(row['divisa'], row['importe adeudado'], row['fecha factura']), axis=1)

        copy = df.copy()
        
        mask = (
                (copy['Fecha límite'] >= mes_inicio) &
                (copy['Fecha límite'] <= mes_fin) &
                ((copy['dias de atraso'] <= 0) | (copy['importe adeudado'] == 0))
            )
        
        df.loc[mask, 'Status'] = df.loc[mask, 'Status'].replace({'COBRANZA': 'SIN VENCER'})

        # Máscara para identificar los que deben ser VENCIDO
        mask_vencido = (
            (copy['Fecha límite'] >= mes_inicio) &
            (copy['Fecha límite'] <= mes_fin) &
            (copy['dias de atraso'] > 0) &
            (copy['importe adeudado'] > 0)
        )

        # Aplicar directamente al dataframe principal
        df.loc[mask_vencido, 'Status'] = df.loc[mask_vencido, 'Status'].replace({'COBRANZA': 'VENCIDO'})
        
        lista.append(('facturas', df))
        #-------------------------------------------------------------------------------------------------------------------------------------------------
        query = """
                    SELECT 
                        ap.id,
                        rp."name" AS cliente,
                        rp2."name" AS vendedor,
                        CASE 
                            WHEN apt."name"->>'es_MX' = 'Pago inmediato' THEN 'Inmediato'
                            ELSE 'Credito'
                        END AS terminos_pago,
                        CASE 
                            WHEN am."ref" like %s THEN 'Inmediato'
                            ELSE 'Credito'
                        END AS diario,
                        am.journal_id as diario_id,
                        am.amount_total_signed AS importe_total,
                        am."date" as fecha_aplicación,
                        -- Campos agregados desde qr
                        qr.factura_id,
                        qr.factura,
                        qr.fecha_límite,
                        qr.cobrador,
                        qr.movimiento,
                        qr.cobrado,
                        qr.fecha,
                        qr.divisa,
                        qr.tipo
                    FROM account_payment ap 
                    LEFT JOIN account_move am ON ap.move_id = am.id
                    LEFT JOIN res_partner rp ON ap.partner_id = rp.id
                    LEFT JOIN discount_profiles_financial_discount dpfd ON rp.financial_profile = dpfd.id
                    LEFT JOIN account_payment_term apt ON dpfd.property_payment_term_id = apt.id
                    LEFT JOIN res_users ru2 ON rp.user_id = ru2.id
                    LEFT JOIN res_partner rp2 ON ru2.partner_id = rp2.id
                    LEFT JOIN (
                        SELECT 
                            am.id AS factura_id,
                            am2."name" AS factura,
                            am2.invoice_date_due AS fecha_límite,
                            rp."name" as Cliente, 
                            rpu."name" AS cobrador,
                            am."name" as movimiento,
                            SUM(apr.debit_amount_currency) AS cobrado,
                            DATE(apr.max_date) AS fecha,
                            am.date AS fecha_aplicación,
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
                        JOIN res_partner rp ON am.partner_id = rp.id
                        WHERE am.move_type IN ('entry')
                        AND apr.credit_move_id IN (
                                SELECT aml.id 
                                FROM account_move_line aml
                                JOIN account_move am ON am.id = aml.move_id 
                                JOIN account_account aa ON aa.id = aml.account_id 
                                WHERE aa.account_type = 'asset_receivable'
                            )
                        AND am.date BETWEEN %s AND %s
                        AND am.state in ('posted')
                        AND am2.partner_id NOT IN (11296, 11298, 11297, 11299, 8355)
                        GROUP BY 
                            am2."name", rp."name", rpu."name", am."name", apr.max_date, 
                            am.currency_id, am.date, am.move_type, 
                            am2.invoice_date, am2.invoice_date_due, am.id
                    ) AS qr 
                        ON am.id = qr.factura_id 
                    WHERE 
                        am."date" BETWEEN %s AND %s
                        AND am.state in ('posted')
                        AND am.partner_id NOT IN (11296, 11298, 11297, 11299, 8355)
                        AND am.journal_id IN (156, 160, 138)
                        AND ap.partner_type = 'customer'
            """
        # Ejecutar la consulta y crear el DataFrame
        self.env.cr.execute(query, ('%CONTADO%', año_inicio, año_fin, año_inicio, año_fin))
        result = self.env.cr.dictfetchall()
        df2 = pd.DataFrame(result)
        df2['fecha_límite'] = pd.to_datetime(df2['fecha_límite'])
        df2['fecha_aplicación'] = pd.to_datetime(df2['fecha_aplicación'])
        
        df2['dias de atraso'] = (df2['fecha_aplicación'] - df2['fecha_límite']).dt.days
        df2['cobrado'] = df2['cobrado'].fillna(0)
        df2['importe_total'] = df2['importe_total'].fillna(0)
        df2['divisa'] = df2['divisa'].apply(lambda x: int(x) if pd.notna(x) else None)

        # Convertimos la lista en un diccionario
        status_dict = dict(status_clientes)

        # Agregamos la columna 'Status'
        df2['Status'] = df2['cliente'].apply(lambda x: status_dict.get(x, 'COBRANZA'))
        
        df2['cobrado'] = df2.apply(
            lambda row: row['cobrado'] if pd.isna(row['divisa'])
            else self.convert_to_company_currency(
                int(row['divisa']),
                row['cobrado'],
                row['fecha_aplicación']
            ),
            axis=1
        )
        
        df2 = df2.drop(columns=['fecha'])
        
        df2 = df2[(df2['fecha_aplicación'] >= año_inicio) & (df2['fecha_aplicación'] <= año_fin)]
        
        df2['mes'] = (
            df2['fecha_aplicación'].dt.month_name().replace(meses_mapping) + " " +
            df2['fecha_aplicación'].dt.year.astype(str)
        )
        
        df2['mes_aux'] = df2['fecha_aplicación'].dt.to_period('M').dt.to_timestamp()
        
        df2['cobrado_total'] = (df2.groupby('id')['cobrado'].transform('sum'))
        df2['pendiente'] = df2['importe_total'] - df2['cobrado_total']
        

        lista.append(('pagos', df2))
        #-------------------------------------------------------------------------------------------------------------------------------------------------
        copy_pagos = df2.copy()
        
        copy_pagos = copy_pagos[(copy_pagos['fecha_aplicación'] >= mes_inicio) & (copy_pagos['fecha_aplicación'] <= mes_fin) & (copy_pagos['terminos_pago'] == 'Credito')]
        #-------------------------------------------------------------------------------------------------------------------------------------------------
        # df_grouped3 = df2.groupby(['mes', 'mes_aux'], as_index=False)['cobrado'].sum()

        # df_grouped3 = df_grouped3.sort_values('mes_aux').drop(columns='mes_aux')
        
        # df_grouped2 = df2[df2['terminos_pago'] == 'Inmediato']
        
        # df_grouped2 = df_grouped2.groupby(['mes', 'mes_aux'], as_index=False)['cobrado'].sum()

        # df_grouped2 = df_grouped2.sort_values('mes_aux').drop(columns='mes_aux')
        
        # df_grouped2 = df_grouped2.rename(columns={
        #     'cobrado': 'Inmediato'
        # })
        
        # df_grouped = pd.merge(df_grouped3, df_grouped2, on='mes', how='left')
        
        # -------------------------
        # df_grouped3
        # -------------------------
        df_cobrado_3 = df2.groupby(['mes', 'mes_aux'], as_index=False)['cobrado'].sum()
        
        df_importe_3 = (df2[df2['pendiente'] != 0].groupby(['mes', 'mes_aux'], as_index=False)['pendiente'].sum())

        df_grouped3 = df_cobrado_3.merge(df_importe_3, on=['mes', 'mes_aux'], how='outer')

        df_grouped3['cobrado'] = df_grouped3['cobrado'].fillna(0)
        df_grouped3['pendiente'] = df_grouped3['pendiente'].fillna(0)

        df_grouped3['cobrado'] = df_grouped3['cobrado'] + df_grouped3['pendiente']

        df_grouped3 = df_grouped3.sort_values('mes_aux').drop(columns=['mes_aux', 'pendiente'])
        # -------------------------
        # df_grouped2 (solo Inmediato)
        # -------------------------
        # df_grouped2 = df2[df2['terminos_pago'] == 'Inmediato']
        df_grouped2 = df2[df2['diario'] == 'Inmediato']

        df_cobrado_2 = df_grouped2.groupby(['mes', 'mes_aux'], as_index=False)['cobrado'].sum()

        df_importe_2 = (df_grouped2[df_grouped2['pendiente'] != 0].groupby(['mes', 'mes_aux'], as_index=False)['pendiente'].sum())

        df_grouped2 = df_cobrado_2.merge(df_importe_2, on=['mes', 'mes_aux'], how='outer')

        df_grouped2['cobrado'] = df_grouped2['cobrado'].fillna(0)
        df_grouped2['pendiente'] = df_grouped2['pendiente'].fillna(0)

        df_grouped2['Inmediato'] = df_grouped2['cobrado'] + df_grouped2['pendiente']

        df_grouped2 = df_grouped2.sort_values('mes_aux').drop(columns=['mes_aux', 'cobrado', 'pendiente'])
        # -------------------------
        # Merge final
        # -------------------------
        df_grouped = pd.merge(df_grouped3, df_grouped2, on='mes', how='left')

        #-------------------------------------------------------------------------------------------------------------------------------------------------
        #df3 = df.groupby('mes', as_index=False)['por vencer'].sum()
        df3 = df[(df['Status'].isin(['COBRANZA', 'SIN VENCER', 'VENCIDO']))]
        df3 = df3.groupby(['mes', 'mes_aux'], as_index=False)['importe adeudado'].sum().fillna(0)
        df3 = df3.sort_values('mes_aux').drop(columns='mes_aux')
        df3 = df3.rename(columns={'importe adeudado': 'por vencer'})
        
        df4 = df[(df['importe adeudado'] > 0)]
        
        # df4 = df4.groupby(['mes', 'mes_aux'], as_index=False)['importe adeudado'].sum()
        # df4 = df4.sort_values('mes_aux').drop(columns='mes_aux')
        # df4['adeudo_cascada'] = df4['importe adeudado'].cumsum()
        #####################################################################################################################################################
        df4 = df4.groupby(['mes', 'mes_aux'], as_index=False)['importe adeudado'].sum()

        rango_meses = pd.date_range(df4['mes_aux'].min(), df4['mes_aux'].max(), freq='MS')

        df4 = df4.set_index('mes_aux').reindex(rango_meses).reset_index()

        df4 = df4.rename(columns={'index': 'mes_aux'})
        df4['importe adeudado'] = df4['importe adeudado'].fillna(0)

        df4['mes'] = df4['mes_aux'].dt.month_name().replace(meses_mapping) + " " + df4['mes_aux'].dt.year.astype(str)

        df4 = df4.sort_values('mes_aux')
        df4['adeudo_cascada'] = df4['importe adeudado'].cumsum()
        
        #####################################################################################################################################################
        df6 = df[(df['por vencer'] > 0)]
        df6 = df6.groupby(['mes', 'mes_aux'], as_index=False)['por vencer'].sum()

        rango_meses = pd.date_range(df6['mes_aux'].min(), df6['mes_aux'].max(), freq='MS')

        df6 = df6.set_index('mes_aux').reindex(rango_meses).reset_index()

        df6 = df6.rename(columns={'index': 'mes_aux'})
        df6['por vencer'] = df6['por vencer'].fillna(0)

        df6['mes'] = df6['mes_aux'].dt.month_name().replace(meses_mapping) + " " + df6['mes_aux'].dt.year.astype(str)
        
        df6.drop(columns=['mes_aux'], inplace=True)
        
        df6 = df6.rename(columns={
            'por vencer': 'Historico'
        })
        
        #####################################################################################################################################################
        df7 = df[(df['NC aplicada'] > 0)]
        df7 = df7.groupby(['mes', 'mes_aux'], as_index=False)['NC aplicada'].sum()

        rango_meses = pd.date_range(df7['mes_aux'].min(), df7['mes_aux'].max(), freq='MS')

        df7 = df7.set_index('mes_aux').reindex(rango_meses).reset_index()

        df7 = df7.rename(columns={'index': 'mes_aux'})
        df7['NC aplicada'] = df7['NC aplicada'].fillna(0)

        df7['mes'] = df7['mes_aux'].dt.month_name().replace(meses_mapping) + " " + df7['mes_aux'].dt.year.astype(str)
        
        df7.drop(columns=['mes_aux'], inplace=True)

        #####################################################################################################################################################
        merged_df = pd.merge(df3, df4, on='mes', how='left')
        
        merged_df['cobranza'] = merged_df['por vencer'].fillna(0) #+ merged_df['adeudo_cascada'].fillna(0)
        
        merged_df2 = pd.merge(merged_df, df_grouped, on='mes', how='left')
        
        merged_df2 = merged_df2.rename(columns={'cobrado': 'Ingreso'})
        
        merged_df3 = pd.merge(merged_df2, df6, on='mes', how='left')
        
        merged_df4 = pd.merge(merged_df3, df7, on='mes', how='left')
        
        merged_df4 = merged_df4[merged_df4['mes'].str.endswith(str(anio))]
        
        merged_df4 = merged_df4.reset_index(drop=True)
        
        merged_df4.drop(columns=['por vencer', 'mes_aux', 'importe adeudado', 'adeudo_cascada'], inplace=True, errors='ignore')
        
        merged_df4['Cobrado real'] = merged_df4['Historico'].fillna(0) - merged_df4['NC aplicada'].fillna(0)
        
        lista.append(('Concentrado', merged_df4))
        #####################################################################################################################################################
        total_cobrado = copy_pagos.loc[(copy_pagos['dias de atraso'] <= 0) & (copy_pagos['Status'] == 'COBRANZA'), 'cobrado'].sum()
        
        sin_vencer = pd.DataFrame({
                                    'Status': ['SIN VENCER'],
                                    'EN TIEMPO': [total_cobrado]
                                })
        
        total_cobrado = copy_pagos.loc[(copy_pagos['dias de atraso'] >= 1) & (copy_pagos['dias de atraso'] <= 5) & (copy_pagos['Status'] == 'COBRANZA'), 'cobrado'].sum()
        
        menos_de_5 = pd.DataFrame({
                                    'Status': ['SIN VENCER'],
                                    'MÁS 5 DÍAS': [total_cobrado]
                                })
        
        total_cobrado = copy_pagos.loc[(copy_pagos['dias de atraso'] >= 6) & (copy_pagos['Status'] == 'COBRANZA'), 'cobrado'].sum()
        mas_de_6 = pd.DataFrame({
                                    'Status': ['VENCIDO'],
                                    'EN TIEMPO': [total_cobrado]
                                })
        
        total_cobrado = copy_pagos.loc[(copy_pagos['dias de atraso'] >= 6) & (copy_pagos['Status'] == 'EXTRAJUDICIAL'), 'cobrado'].sum()
        extrajudicial = pd.DataFrame({
                                    'Status': ['EXTRAJUDICIAL'],
                                    'EN TIEMPO': [total_cobrado]
                                })
        
        df_concat333 = pd.concat([sin_vencer, mas_de_6, extrajudicial], ignore_index=True)
        
        df_concat333 = pd.merge(df_concat333, menos_de_5, on='Status', how='outer')
        
        merged_df_copy3 = copy[(copy['Status'] == 'EXTRAJUDICIAL')]
        merged_df_copy3 = (merged_df_copy3.groupby(['factura', 'Status'], as_index=False)['importe adeudado'].mean().reset_index())
        merged_df_copy3 = merged_df_copy3.groupby('Status', as_index=False)['importe adeudado'].sum()
        merged_df_copy3.rename(columns={'importe adeudado': 'por vencer'}, inplace=True)
        
        merged_df_copy4 = copy[((copy['Fecha límite'] >= mes_inicio) & (copy['Fecha límite'] <= mes_fin))]
        merged_df_copy4 = (merged_df_copy4.groupby(['factura', 'Status'], as_index=False)['por vencer'].mean().reset_index())
        merged_df_copy4 = merged_df_copy4.groupby('Status', as_index=False)['por vencer'].sum()
        
        df_monto = copy[(((copy['Fecha límite'] >= mes_inicio) & (copy['Fecha límite'] <= mes_fin)) & ((copy['dias de atraso'] <= 0) | (copy['importe adeudado'] == 0)))]
        df_monto = (df_monto.groupby(['factura', 'Status'], as_index=False)['por vencer'].mean().reset_index())
        df_monto['Status'] = df_monto['Status'].replace({'COBRANZA': 'SIN VENCER'})
        df_monto = df_monto.groupby('Status', as_index=False)['por vencer'].sum()
        
        df_vencido= copy[(((copy['Fecha límite'] >= mes_inicio) & (copy['Fecha límite'] <= mes_fin)) & (copy['dias de atraso'] > 0) & (copy['importe adeudado'] > 0))]
        df_vencido = (df_vencido.groupby(['factura', 'Status'], as_index=False)['importe adeudado'].mean().reset_index())
        df_vencido['Status'] = df_vencido['Status'].replace({'COBRANZA': 'VENCIDO'})
        df_vencido = df_vencido.groupby('Status', as_index=False)['importe adeudado'].sum()
        df_vencido = df_vencido.rename(columns={'importe adeudado': 'por vencer'})
#--------------------------- CALCULAR LAS NOTAS DE CREDITO NO APLICADAS CON MAS DE 5 DIAS --------------------------------------------------------
        search_domain2 = [
            ('move_type', 'in', ['out_refund']),
            ('state', 'in', ['posted']),
            ('payment_state', 'in', ['not_paid', 'paid']),
            ('partner_id', 'not in', [11296, 11298, 11297, 11299, 8355])
        ]

        datos2 = []
        records2 = self.env['account.move'].search(search_domain2)
        # Extrae nombres de los registros relacionados
        for record2 in records2:
            vals2 = {
                'factura': record2.name,
                'Cliente': record2.partner_id.name,
                'Términos de pago del cliente': record2.partner_id.property_payment_term_id.name,
                'fecha factura': record2.invoice_date,
                'por vencer': record2.amount_total,
                'divisa': record2.currency_id.name,
                'payment_state': record2.payment_state
            }
            if pd.Timestamp(record2.invoice_date)  <= (hoy - pd.DateOffset(days=5)):
                vals2.update({'Status': 'NC PENDIENTES'})
            else:
                vals2.update({'Status': 'NC MENOS DE 5 DÍAS'})
                
            datos2.append(vals2)

        df5 = pd.DataFrame(datos2)
        
        df_nc = df5.copy()
        
        df_nc = df_nc[df_nc['payment_state'] == 'paid']
        df_nc['fecha factura'] = pd.to_datetime(df_nc['fecha factura'])
        df_nc['mes'] = (
            df_nc['fecha factura'].dt.month_name().replace(meses_mapping) + " " +
            df_nc['fecha factura'].dt.year.astype(str)
        )
        
        df5 = df5[df5['payment_state'] == 'not_paid']
        df5.drop(columns=['payment_state'], inplace=True)
        df5 = df5.groupby(['Status'], as_index=False)['por vencer'].sum()
        
        lista.append(('Notas de credito', df5))
#-------------------------------------------------------------------------------------------------------------------------------------------------
        df_concat = pd.concat([merged_df_copy4, df_monto, df_vencido ,merged_df_copy3, df5], ignore_index=True)
        
        merged_df20 = pd.merge(df_concat, df_concat333, on='Status', how='outer')
        
        total = merged_df20.loc[merged_df20['Status'].isin(['COBRANZA', 'EXTRAJUDICIAL']), 'por vencer'].sum()
        df_total4 = pd.DataFrame([{'Status': 'TOTAL', 'por vencer': total}])
        
        total2 = (merged_df20.loc[merged_df20['Status'].isin(['SIN VENCER', 'VENCIDO']), 'EN TIEMPO'].sum() + 
                  merged_df20.loc[merged_df20['Status'].isin(['SIN VENCER', 'VENCIDO']), 'MÁS 5 DÍAS'].sum())
                                 
        df_total2 = pd.DataFrame([{'Status': 'COBRANZA', 'EN TIEMPO': total2}])
        
        total3 = (merged_df20.loc[merged_df20['Status'].isin(['EXTRAJUDICIAL']), 'EN TIEMPO'].sum() + 
                  merged_df20.loc[merged_df20['Status'].isin(['EXTRAJUDICIAL']), 'MÁS 5 DÍAS'].sum())
                                 
        df_total3 = pd.DataFrame([{'Status': 'TOTAL', 'EN TIEMPO': total2 + total3}])
        
        df_total = pd.merge(df_total4, df_total3, on='Status', how='outer')
        
        df_final2 = pd.merge(merged_df20, df_total2, on='Status', how='outer')
        df_final2['EN TIEMPO'] = df_final2['EN TIEMPO_x'].fillna(df_final2['EN TIEMPO_y'])
        df_final2 = df_final2.drop(columns=['EN TIEMPO_x', 'EN TIEMPO_y'])
        
        df_final = pd.concat([df_final2, df_total], ignore_index=True)
        
        orden_status = ["TOTAL", "COBRANZA", "SIN VENCER", "VENCIDO", "EXTRAJUDICIAL", "NC PENDIENTES", "NC MENOS DE 5 DÍAS"]

        # Definir el tipo categórico con orden
        cat_type = CategoricalDtype(categories=orden_status, ordered=True)

        # Convertir la columna a categórica
        df_final['Status'] = df_final['Status'].astype(cat_type)

        orden_columns = ['Status', 'por vencer', 'EN TIEMPO', 'MÁS 5 DÍAS']
        df_final = df_final.reindex(columns=orden_columns)

        #Ordenar el DataFrame
        df_final = df_final.sort_values('Status')
        
        lista.append(('Saldos', df_final))
        #-------------------------------------------------------------------------------------------------------------------------------------------------
        df_vencidos = copy[(copy['dias de atraso'] >= 30) & (copy['importe adeudado'] > 0)]
        
        columnas_deseadas = ['Cliente', 'Términos de pago del cliente', 'factura', 'dias de atraso', 'por vencer', 'importe adeudado']
        
        df_vencidos = df_vencidos[columnas_deseadas]
        
        lista.append(('INDICADOR VENCIDOS', df_vencidos))
        
        #-------------------------------------------------------------------------------------------------------------------------------------------------
        vendedores1 = [
            'JOSE AARON FONSECA RADA',
            'CHRISTIAN GUADALUPE NORIEGA PALACIOS'
        ]
        
        df_cobranza = df2.copy()
        
        dict_status = dict(status_clientes)
        
        df_cobranza['Cobrador2'] = 'LUZ VERONICA TORRES DELGADO'
        df_cobranza.loc[(df_cobranza['vendedor'].isin(vendedores1)), 'Cobrador2'] = 'DIANA KARINA ROLDÁN MENDEZ'

        df_cobranza.loc[df_cobranza['cliente'].isin(dict_status.keys()), 'Cobrador2'] = df_cobranza['cliente'].map(dict_status)
        
        columnas_deseadas2 = ['Cobrador2', 'mes', 'diario', 'cobrado', 'pendiente']
        
        df_cobranza = df_cobranza[columnas_deseadas2]
        
        df_cobranza = df_cobranza.groupby(['Cobrador2', 'mes', 'diario'], as_index=False).agg({'cobrado': 'sum', 'pendiente': 'sum'})
        
        df_pivot = df_cobranza.pivot_table(
            index='Cobrador2',              # Filas
            columns=['mes', 'diario'],      # Columnas jerárquicas
            values='cobrado',
            aggfunc='sum',
            fill_value=0
        )
        lista.append(('DESGLOSE X Cobraor', df_pivot))
        
        return lista