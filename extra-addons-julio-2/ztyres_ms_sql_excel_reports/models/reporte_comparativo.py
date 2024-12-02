from locale import currency
from odoo import api, fields, models
import pandas as pd
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from collections import defaultdict
import math


class Reportecomparativo(models.TransientModel):
    _name = 'ztyres_reporte_comparativo'
    
    def convert_to_company_currency(self, currency_id, amount, date):
        if currency_id is not None and not math.isnan(amount) and not pd.isna(date):
            currency_record = self.env['res.currency'].browse(int(currency_id))
            converted_amount = currency_record._convert(
                amount,
                currency_record.env.company.currency_id,
                currency_record.env.company,
                date
            )
            return converted_amount
        else: 
            return 0
    
    def get_report(self):
        # Inicializamos un defaultdict para acumular los datos
        aggregated_data = defaultdict(lambda: {'TotalSinIVA': 0})

        primer_dia_mes = '2023-01-01'  # Primer día del período
        ultimo_dia_mes = '2024-12-31'  # Último día del período

        # Dominio de búsqueda, con coma entre las condiciones
        search_domain20 = [
            ('display_type', '=', 'product'),
            ('product_type', '=', 'product'),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            # ('parent_state', '=', 'posted'),
            ('move_id.invoice_date', '>=', primer_dia_mes),
            ('move_id.invoice_date', '<=', ultimo_dia_mes),
        ]
        datos = []
        records20 = self.env['account.move.line'].search(search_domain20)
        for line in records20:
            vals = {}
            
            if line.move_type == 'out_invoice':
                vals.update({
                    'Tipo_Movimiento': 'Factura',
                    'Total sin IVA': line.credit
                })
            elif line.move_type == 'out_refund':
                vals.update({
                    'Tipo_Movimiento': 'Nota de Crédito',
                    'Total sin IVA': -1 * line.debit
                })
            else:
                continue 
            
            vals.update({
                'Fecha': line.move_id.invoice_date,
                'Vendedor': line.partner_id.user_id.name,
                'Fabricante': line.product_id.manufacturer_id.name,
                'Divisa': line.move_id.currency_id.id
            })
            datos.append(vals)

        # Convertimos el defaultdict a una lista
        for dato in datos:
            key = (dato['Vendedor'], dato['Fecha'], dato['Tipo_Movimiento'], dato['Fabricante'], dato['Divisa'])
            total_sin_iva = dato['Total sin IVA']
            aggregated_data[key]['TotalSinIVA'] += total_sin_iva
            aggregated_data[key].update({
                'Vendedor': dato['Vendedor'],
                'Fecha': dato['Fecha'],
                'Tipo_Movimiento': dato['Tipo_Movimiento'],
                'Fabricante': dato['Fabricante']
            })

        datos_agrupados = list(aggregated_data.values())

        df20 = pd.DataFrame(datos_agrupados)
        column_order = ['Tipo_Movimiento', 'Fecha', 'Vendedor', 'Fabricante', 'TotalSinIVA']
        df20 = df20[column_order]
        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(df20, 'reporte_comparativo')
        return
