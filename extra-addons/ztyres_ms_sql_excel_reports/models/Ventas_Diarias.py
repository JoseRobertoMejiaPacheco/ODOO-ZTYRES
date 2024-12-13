from email.policy import default
from odoo import api, fields, models
import pandas as pd
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

class ReservaVentas(models.TransientModel):
    _name = 'ztyres_reporte_ventas_diarias'
    
    def get_report(self):
        # fecha_actual = date.today()
        # # Obtén el primer día del mes actual
        # primer_dia_mes = fecha_actual.replace(day=1)
        # ultimo_dia_mes = primer_dia_mes.replace(day=28)  # Establece inicialmente el día 28
        # ultimo_dia_mes = ultimo_dia_mes + pd.offsets.MonthEnd(0)  # Ajusta al último día del mes

        primer_dia_mes = date(2024, 1, 1)  # Primer día de enero de 2000
        ultimo_dia_mes = date(2024, 12, 31)  # Último día de diciembre de 2024
        
        primer_dia_mes_ts = pd.Timestamp(primer_dia_mes)
        ultimo_dia_mes_ts = pd.Timestamp(ultimo_dia_mes)

        # Dominio de búsqueda, con coma entre las condiciones
        search_domain20 = [
            ('display_type', 'in', ['product']),
            ('product_type', 'in', ['product']),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('parent_state', 'in', ['posted']),
            ('move_id.date', '>=', primer_dia_mes_ts),
            ('move_id.date', '<=', ultimo_dia_mes_ts),
        ]
        datos = []
        records20 = self.env['account.move.line'].search(search_domain20)
        for line in records20:
            vals = {}
            list_ids = [1]
            res = self.env['product.pricelist.item'].search([
                      ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id),
                      ('pricelist_id', 'in', list_ids)
                       ])
            if res.fixed_price == 0:
                list_ids = [113]
                res = self.env['product.pricelist.item'].search([
                              ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id),
                              ('pricelist_id', 'in', list_ids)
                               ])
                if res.fixed_price == 0:
                    list_ids = [108]
                    res = self.env['product.pricelist.item'].search([
                                  ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id),
                                  ('pricelist_id', 'in', list_ids)
                                   ])
            
            
            if line.move_type in ['out_invoice']:
                vals.update({
                'Tipo_Movimiento': 'Factura',
                'Cantidad': line.quantity,
                'Total sin IVA': line.price_subtotal,
                'Precio Lista': res.fixed_price
                })
            if line.move_type in ['out_refund']:
                vals.update({
                'Tipo_Movimiento': 'Nota de Crédito',
                'Cantidad': -1 * line.quantity,
                'Total sin IVA': -1 * line.price_subtotal
                }) 
            if line.partner_id.volume_profile.name in ['AAA']:
                vals.update({
                    'Meta': 1000
                })
            elif line.partner_id.volume_profile.name in ['AA']:
                vals.update({
                    'Meta': 600
                })
            elif line.partner_id.volume_profile.name in ['A']:
                vals.update({
                    'Meta': 300
                })
            elif line.partner_id.volume_profile.name in ['B']:
                vals.update({
                    'Meta': 100
                })
            elif line.partner_id.volume_profile.name in ['C']:
                vals.update({
                    'Meta': 30
                })
            elif line.partner_id.volume_profile.name in ['D']:
                vals.update({
                    'Meta': 0
                })
            vals.update({
                'Fecha': line.move_id.date,
                'Cliente': line.partner_id.name,
                'Dias Credito': line.partner_id.property_payment_term_id.name,
                'Estado': line.partner_id.state_id.name,
                'Ciudad': line.partner_id.city_id.name,
                'Vendedor': line.partner_id.user_id.name,
                'Movimiento': line.move_id.name,
                'Código': line.product_id.default_code,
                'CIU': line.product_id.cui,
                'Fabricante':line.product_id.manufacturer_id.name,
                'Marca': line.product_id.brand_id.name,
                'Medida':line.product_id.tire_measure_id.name,
                'Modelo':line.product_id.model_id.name,  
                'Tier': line.product_id.tier_id.name,
                'Total': line.move_id.amount_total,
                'Importe adeudado': line.move_id.amount_residual
            })
            
            if line.move_id.amount_total == line.move_id.amount_residual:
                vals.update({
                    'Status': "Sin Pagar"
                })
            elif line.move_id.amount_residual < line.move_id.amount_total and line.move_id.amount_residual != 0:
                vals.update({
                    'Status': "Pagado Parcialmente"
                })
            elif line.move_id.amount_residual == 0:
                vals.update({
                    'Status': "Pagado"
                })
            
            datos.append(vals)
        df20 = pd.DataFrame(datos)
        column_order = ['Movimiento','Tipo_Movimiento', 'Fecha', 'Cliente', 'Meta', 'Dias Credito', 'Ciudad', 'Estado', 'Vendedor', 'Código', 'CIU', 'Fabricante', 
                        'Marca', 'Medida', 'Modelo', 'Tier','Cantidad', 'Precio Lista', 'Total sin IVA', 'Total', 'Importe adeudado', 'Status']
        df20 = df20[column_order]
        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(df20, 'reporte_ventas_diarias')
        return