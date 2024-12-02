from odoo import models, fields
import pandas as pd


class Comisiones(models.TransientModel):
    _name = 'reporte.comisiones'  # Reemplaza 'your.class.name' por el nombre que desees para tu clase
    _description = 'Descripción de tu clase'

    def get_df_promo_kumho(self):
        product_ids = [51645]
        start_date = '2024-02-01'
        end_date = '2024-02-29'

        domain = [
            ('move_id.invoice_date', '>=', start_date),
            ('move_id.invoice_date', '<=', end_date),
            ('product_id.product_tmpl_id', 'in', product_ids),
            ('move_id.move_type', 'in', ['out_invoice']),
            ('move_id.state', 'in', ['posted']),
            ('display_type', 'in', ['product']),
        ]

        am = self.env['account.move.line'].search(domain)
        data = []

        for line in am:
            data.append({
                'Vendedor': line.move_id.invoice_user_id.name,
                'Producto': line.product_id.name,
                'Cantidad': line.quantity,
                'Factura': line.move_id.name,
                'Line Id': line.id
            })

        df = pd.DataFrame(data)
        df_grouped = df.groupby(['Vendedor', 'Factura', 'Producto'])['Cantidad'].sum().reset_index()
        df_grouped = df_grouped[df_grouped['Cantidad'] >= 24]
        df_grouped = df_grouped.drop_duplicates(subset=['Factura'])

        comision_por_paquete = 1200

        df_grouped['Numero_Paquetes'] = df_grouped['Cantidad'] // 24  # Número entero de paquetes
        df_grouped['Comision_Total'] = (df_grouped['Numero_Paquetes'] // 5) * comision_por_paquete

        df_grouped = df_grouped.groupby(['Vendedor', 'Producto'])['Numero_Paquetes', 'Comision_Total'].sum().reset_index()
        df_grouped = df_grouped.sort_values(by='Numero_Paquetes', ascending=False)
        
        return df_grouped.to_html(classes='table table-striped', index=False)
