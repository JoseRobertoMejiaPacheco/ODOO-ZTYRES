from odoo import api, fields, models
import math
import pandas as pd
from datetime import datetime, timedelta, date
import numpy as np
from dateutil.relativedelta import relativedelta
from functools import reduce
from odoo.addons.inv_promo.wizard.models.lista_de_precios import codes, codes2, codes3

class MyModel(models.TransientModel):
    _name = 'reporte_promos_bridgestone'

    def get_all_products(self):
          
      lista = []
          
      desired_fields = [
            'id',
            'default_code',
            'segment_id',
            'tier_id',
            'manufacturer_id',
            'brand_id'
        ]
      records = self.env['product.template'].search_read([('detailed_type', 'in', ['product'])], fields=desired_fields)
        # Extraer solo los valores de las tuplas
      result = [{key: value[1] if isinstance(value, tuple) else value for key, value in record.items()} for record in records]
      df = pd.DataFrame(result)
      #---------------------------------------------------------------------------------------------------------------
      #fecha_actual = date.today()
      ## Obtén el primer día del mes actual
      #primer_dia_mes = fecha_actual.replace(day=1)
      #ultimo_dia_mes = primer_dia_mes.replace(day=28)  # Establece inicialmente el día 28
      #ultimo_dia_mes = ultimo_dia_mes + pd.offsets.MonthEnd(0)  # Ajusta al último día del mes
      
      primer_dia_mes = pd.to_datetime('2025-03-01')  # Primer día de abril de 2024
      ultimo_dia_mes = pd.to_datetime('2025-03-31')  # Último día de abril de 2024
      #---------------------------------------------------------------------------------------------------------------
      query = """
          SELECT aml.id as amlid,
                 aml.move_id as move_id, 
                 aml.move_name, 
                 am.invoice_date AS fecha_factura,
                 rp."name" AS cliente,
                 rp2."name" AS vendedor,
                 pp.default_code,
                 CASE 
                    WHEN am.move_type in ('out_refund') THEN -aml.quantity
                    ELSE aml.quantity
                 END as cantidad,
                 aml.price_unit AS precio_unitario,
                 aml.price_subtotal,
                 CASE 
                    WHEN am.move_type in ('out_refund') THEN -aml.price_total
                    ELSE aml.price_total
                 END as price_total,
                 CASE 
                    WHEN am.move_type in ('out_refund') THEN -am.x_studio_piezas_facturadas 
                    ELSE am.x_studio_piezas_facturadas 
                 END as piezas_facturadas
              FROM account_move_line aml 
              LEFT JOIN product_product pp ON aml.product_id = pp.id
              LEFT JOIN account_move am ON aml.move_id = am.id
              LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id 
              LEFT JOIN res_partner rp ON am.partner_id = rp.id 
              LEFT JOIN res_users ru ON am.invoice_user_id = ru.id 
              LEFT JOIN res_partner rp2 ON ru.partner_id = rp2.id 
              WHERE aml.display_type = 'product'
              AND pt.detailed_type = 'product'
              AND am.move_type IN ('out_invoice', 'out_refund')
              AND am.state = 'posted'       
      """
      self.env.cr.execute(query)
      result2 = self.env.cr.dictfetchall()        #Crear dataframe de la consulta
      df2 = pd.DataFrame(result2)
      df2['fecha_factura'] = pd.to_datetime(df2['fecha_factura'], errors='coerce')
      df2 = df2.loc[(df2['fecha_factura'] >= primer_dia_mes) & (df2['fecha_factura'] <= ultimo_dia_mes)]
      #---------------------------------------------------------------------------------------------------------------
      merged_df = pd.merge(df2, df, on='default_code', how='left')

      desired_fields = ['id',
                        'single_dot'
                        ]

      domain = [
                  ('move_id.invoice_date', '>=', primer_dia_mes),
                  ('move_id.invoice_date', '<=', ultimo_dia_mes),
                  ('move_id.move_type', 'in', ['out_invoice']),
                  ('move_id.state', 'in', ['posted']),
                  ('display_type', 'in', ['product']),
                  ('single_dot', '!=', False)
            ]

      am = self.env['account.move.line'].search_read(domain, fields=desired_fields)

      ids = [record['id'] for record in am]  
      single_dots = [record['single_dot'] for record in am]  

      data = {
      'amlid': ids,
      'single_dot': single_dots
      }

      df4 = pd.DataFrame(data)

      merged_df3 = pd.merge(merged_df, df4, on='amlid', how='left')

      volumen_df = merged_df3.copy()
      
      merged_df_filtered3 = merged_df3[(merged_df3['id'].isin(codes))]
      merged_df_filtered3['cantidadXfactura'] = merged_df_filtered3.groupby('move_id')['cantidad'].transform('sum')
      
      merged_df_filtered5 = merged_df3[(merged_df3['manufacturer_id'].isin(['MILESTAR']))]
      merged_df_filtered5['cantidadXfactura'] = merged_df_filtered5.groupby('move_id')['cantidad'].transform('sum')
      
      merged_df_filtered6 = merged_df3[(merged_df3['tier_id'].isin(['Tier 4']))]
      merged_df_filtered6['cantidadXfactura'] = merged_df_filtered6.groupby('move_id')['cantidad'].transform('sum')
      
      merged_df_filtered7 = merged_df3[(merged_df3['manufacturer_id'].isin(['VENOM']))]
      merged_df_filtered7['cantidadXfactura'] = merged_df_filtered7.groupby('move_id')['cantidad'].transform('sum')
#################################################################### PROMOS VOLUMEN ####################################################################
                                                     #Promos Volumen BRIDGESTONE
      volumen_df3 = volumen_df[(volumen_df['id'].isin(codes))]
      
      if volumen_df3.empty:
            pivot_df2 = pd.DataFrame(columns=['cliente', 'vendedor', 'Total Brid', 'BRIDGESTONE', 'ADICIONAL'])  # Define las columnas esperadas
            colum_selec = pivot_df2[['cliente', 'vendedor', 'Total Brid', 'BRIDGESTONE', 'ADICIONAL']]
      else:
            pivot_df2 = volumen_df3.pivot_table(index=['cliente', 'vendedor'], values='price_total', aggfunc='sum', fill_value=0)
            pivot_df2.reset_index(inplace=True)
            
            pivot_df2.loc[(pivot_df2['price_total'] >= 696000), ['BRIDGESTONE', 'ADICIONAL']] = ['Bono 10%', 'Por confirmar']
            pivot_df2.loc[(pivot_df2['price_total'] >= 348000) & (pivot_df2['price_total'] < 696000), ['BRIDGESTONE', 'ADICIONAL']] = ['Bono 8%', 'Por confirmar']
            pivot_df2.loc[(pivot_df2['price_total'] >= 116000) & (pivot_df2['price_total'] < 348000), ['BRIDGESTONE', 'ADICIONAL']] = ['Bono 6%', 'Por confirmar']
            pivot_df2.loc[(pivot_df2['price_total'] >= 46400) & (pivot_df2['price_total'] < 116000), ['BRIDGESTONE', 'ADICIONAL']] = ['Bono 4%', 'Por confirmar']
            
            pivot_df2 = pivot_df2.rename(columns={'price_total': 'Total Brid'})
            colum_selec = pivot_df2[['cliente', 'vendedor', 'Total Brid', 'BRIDGESTONE', 'ADICIONAL']]

#################################################################### PROMOS VOLUMEN ####################################################################
                                                     #Promos Volumen MILESTAR
      volumen_df5 = volumen_df[(volumen_df['manufacturer_id'].isin(['MILESTAR']))]
      
      if volumen_df5.empty:
            pivot_df4 = pd.DataFrame(columns=['cliente', 'vendedor', 'Total Milestar', 'Milestar', 'AdicionalM'])  # Define las columnas esperadas
            colum_selec3 = pivot_df4[['cliente', 'vendedor', 'Total Milestar', 'Milestar', 'AdicionalM']]
      else:
            pivot_df4 = volumen_df5.pivot_table(index=['cliente', 'vendedor'], values='cantidad', aggfunc='sum', fill_value=0)
            pivot_df4.reset_index(inplace=True)
            
            pivot_df4.loc[(pivot_df4['cantidad'] >= 300), ['Milestar', 'AdicionalM']] = ['Bono 5%', 'Nintendo Switch Oled ó Apple Watch SE']
            pivot_df4.loc[(pivot_df4['cantidad'] >= 150) & (pivot_df4['cantidad'] < 300), ['Milestar', 'AdicionalM']] = ['Bono 3%', 'Iphone 14 Ó Galaxy S24 FE']
            
            pivot_df4 = pivot_df4.rename(columns={'cantidad': 'Total Milestar'})
            colum_selec3 = pivot_df4[['cliente', 'vendedor', 'Total Milestar', 'Milestar', 'AdicionalM']]
#################################################################### PROMOS VOLUMEN ####################################################################
                                                     #Promos Volumen  TIER 4
      volumen_df6 = volumen_df[(volumen_df['tier_id'].isin(['Tier 4']))]
      
      if volumen_df6.empty:
            pivot_df5 = pd.DataFrame(columns=['cliente', 'vendedor', 'Total TIER 4', 'TIER 4'])  # Define las columnas esperadas
            colum_selec4 = pivot_df5[['cliente', 'vendedor', 'Total TIER 4', 'TIER 4']]
      else:
            pivot_df5 = volumen_df6.pivot_table(index=['cliente', 'vendedor'], values='cantidad', aggfunc='sum', fill_value=0)
            pivot_df5.reset_index(inplace=True)
            
            pivot_df5.loc[(pivot_df5['cantidad'] >= 150), 'TIER 4'] = 'Bono 6%'
            pivot_df5.loc[(pivot_df5['cantidad'] >= 100) & (pivot_df5['cantidad'] < 150), 'TIER 4'] = 'Bono 4%'
            pivot_df5.loc[(pivot_df5['cantidad'] >= 50) & (pivot_df5['cantidad'] < 100), 'TIER 4'] = 'Bono 2%'
            
            pivot_df5 = pivot_df5.rename(columns={'cantidad': 'Total TIER 4'})
            colum_selec4 = pivot_df5[['cliente', 'vendedor', 'Total TIER 4', 'TIER 4']]
#################################################################### PROMOS VOLUMEN ####################################################################
                                                     #Promos Volumen  VENOM
      volumen_df7 = volumen_df[(volumen_df['manufacturer_id'].isin(['VENOM']))]
      
      if volumen_df7.empty:
            pivot_df6 = pd.DataFrame(columns=['cliente', 'vendedor', 'Total VENOM', 'VENOM'])  # Define las columnas esperadas
            colum_selec5 = pivot_df6[['cliente', 'vendedor', 'Total VENOM', 'VENOM']]
      else:
            pivot_df6 = volumen_df7.pivot_table(index=['cliente', 'vendedor'], values='cantidad', aggfunc='sum', fill_value=0)
            pivot_df6.reset_index(inplace=True)
            
            pivot_df6.loc[(pivot_df6['cantidad'] >= 200), 'VENOM'] = 'Bono 5%'
            pivot_df6.loc[(pivot_df6['cantidad'] >= 100) & (pivot_df6['cantidad'] < 200), 'VENOM'] = 'Bono 3%'
            
            pivot_df6 = pivot_df6.rename(columns={'cantidad': 'Total VENOM'})
            colum_selec5 = pivot_df6[['cliente', 'vendedor', 'Total VENOM', 'VENOM']]
###################################################################################################################################################################
      df_combined = colum_selec.merge(colum_selec3, on=['cliente', 'vendedor'], how='outer')
      df_combined3 = df_combined.merge(colum_selec4, on=['cliente', 'vendedor'], how='outer')
      df_combined4 = df_combined3.merge(colum_selec5, on=['cliente', 'vendedor'], how='outer')
      #df_combined3 = df_combined2.merge(colum_selec4, on=['cliente', 'vendedor'], how='outer')
      
      lista.append(('bridgestone', merged_df_filtered3))
      lista.append(('Milestar', merged_df_filtered5))
      lista.append(('Tier4', merged_df_filtered6))
      lista.append(('Venom', merged_df_filtered7))
      lista.append(('promos_volumen', df_combined4))
      
      return lista