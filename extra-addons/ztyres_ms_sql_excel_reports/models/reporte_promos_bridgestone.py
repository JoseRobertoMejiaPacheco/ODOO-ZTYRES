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
      
      primer_dia_mes = pd.to_datetime('2024-12-02')  # Primer día de abril de 2024
      ultimo_dia_mes = pd.to_datetime('2024-12-31')  # Último día de abril de 2024
      #---------------------------------------------------------------------------------------------------------------
      query = """
          SELECT aml.move_id, 
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
      
      volumen_df = merged_df.copy()
      
      merged_df_filtered3 = merged_df[(merged_df['id'].isin(codes))]
      merged_df_filtered3['cantidadXfactura'] = merged_df_filtered3.groupby('move_id')['cantidad'].transform('sum')
      
      merged_df_filtered4 = merged_df[(merged_df['id'].isin(codes2))]
      merged_df_filtered4['cantidadXfactura'] = merged_df_filtered4.groupby('move_id')['cantidad'].transform('sum')
      
      merged_df_filtered5 = merged_df[(merged_df['id'].isin(codes3))]
      merged_df_filtered5['cantidadXfactura'] = merged_df_filtered5.groupby('move_id')['cantidad'].transform('sum')
#################################################################### PROMOS PAQUETES COMBINADO ####################################################################
      # merged_df_filtered3.loc[(merged_df_filtered3['default_code'].isin(promo_paquetes_comb)) & (merged_df_filtered3['cantidadCombinada'] >= merged_df_filtered3['condicion2']), 'Sigue el vareno Paquetes'] = merged_df_filtered3['descripcion2']
      
      # merged_df_filtered3 = merged_df_filtered3.drop(['condicion2', 'descripcion2'], axis=1)
#################################################################### PROMOS VOLUMEN ####################################################################
                                                     #Promos Volumen BRIDGESTONE
      volumen_df3 = volumen_df[(volumen_df['id'].isin(codes))]
      
      if volumen_df3.empty:
            pivot_df2 = pd.DataFrame(columns=['cliente', 'vendedor', 'Total Onyx', 'Onyx'])  # Define las columnas esperadas
            colum_selec = pivot_df2[['cliente', 'vendedor', 'Total Brid', 'BRIDGESTONE', 'MONEDERO']]
      else:
            pivot_df2 = volumen_df3.pivot_table(index=['cliente', 'vendedor'], values='price_total', aggfunc='sum', fill_value=0)
            pivot_df2.reset_index(inplace=True)
            
            pivot_df2.loc[(pivot_df2['price_total'] >= 928000), 'BRIDGESTONE'] = 'Bono 12%'
            pivot_df2.loc[(pivot_df2['price_total'] >= 928000), 'MONEDERO'] = 'Bono 25K'
            pivot_df2.loc[(pivot_df2['price_total'] >= 348000) & (pivot_df2['price_total'] < 927999), 'BRIDGESTONE'] = 'Bono 10%'
            pivot_df2.loc[(pivot_df2['price_total'] >= 348000) & (pivot_df2['price_total'] < 927999), 'MONEDERO'] = 'Bono 14K'
            pivot_df2.loc[(pivot_df2['price_total'] >= 116000) & (pivot_df2['price_total'] < 347999), 'BRIDGESTONE'] = 'Bono 8%'
            pivot_df2.loc[(pivot_df2['price_total'] >= 116000) & (pivot_df2['price_total'] < 347999), 'MONEDERO'] = 'Bono 8K'
            pivot_df2.loc[(pivot_df2['price_total'] >= 46400) & (pivot_df2['price_total'] < 115999), 'BRIDGESTONE'] = 'Bono 6%'
            pivot_df2.loc[(pivot_df2['price_total'] >= 46400) & (pivot_df2['price_total'] < 115999), 'MONEDERO'] = 'Bono 3.5K'
            
            pivot_df2 = pivot_df2.rename(columns={'price_total': 'Total Brid'})
            colum_selec = pivot_df2[['cliente', 'vendedor', 'Total Brid', 'BRIDGESTONE', 'MONEDERO']]

#################################################################### PROMOS VOLUMEN ####################################################################
                                                     #Promos Volumen Buen Mix
      volumen_df4 = volumen_df[(volumen_df['id'].isin(codes2))]
      
      if volumen_df4.empty:
            pivot_df3 = pd.DataFrame(columns=['cliente', 'vendedor', 'Total Onyx', 'Onyx'])  # Define las columnas esperadas
            colum_selec2 = pivot_df3[['cliente', 'vendedor', 'Total Onyx', 'Onyx']]
      else:
            pivot_df3 = volumen_df4.pivot_table(index=['cliente', 'vendedor'], values='cantidad', aggfunc='sum', fill_value=0)
            pivot_df3.reset_index(inplace=True)
      
            pivot_df3.loc[(pivot_df3['cantidad'] >= 1000), 'Onyx'] = 'Bono 10%'
            pivot_df3.loc[(pivot_df3['cantidad'] >= 600) & (pivot_df3['cantidad'] < 1000), 'Onyx'] = 'Bono 8%'
            pivot_df3.loc[(pivot_df3['cantidad'] >= 300) & (pivot_df3['cantidad'] < 600), 'Onyx'] = 'Bono 4%'
      
            pivot_df3 = pivot_df3.rename(columns={'price_total': 'Total Onyx'})
            colum_selec2 = pivot_df3[['cliente', 'vendedor', 'Total Onyx', 'Onyx']]
      
#################################################################### PROMOS VOLUMEN ####################################################################
                                                     #Promos Volumen MERRY TTER 4
      volumen_df5 = volumen_df[(volumen_df['id'].isin(codes3))]
      
      if volumen_df5.empty:
            pivot_df4 = pd.DataFrame(columns=['cliente', 'vendedor', 'Total Merry_T4', 'Merry_T4'])  # Define las columnas esperadas
            colum_selec3 = pivot_df4[['cliente', 'vendedor', 'Total Merry_T4', 'Merry_T4']]
      else:
            pivot_df4 = volumen_df5.pivot_table(index=['cliente', 'vendedor'], values='cantidad', aggfunc='sum', fill_value=0)
            pivot_df4.reset_index(inplace=True)
            
            pivot_df4.loc[(pivot_df4['cantidad'] >= 350), 'Merry_T4'] = 'Bono 8%'
            pivot_df4.loc[(pivot_df4['cantidad'] >= 150) & (pivot_df4['cantidad'] < 350), 'Merry_T4'] = 'Bono 6%'
            pivot_df4.loc[(pivot_df4['cantidad'] >= 60) & (pivot_df4['cantidad'] < 150), 'Merry_T4'] = 'Bono 3%'
            
            pivot_df4 = pivot_df4.rename(columns={'cantidad': 'Total Merry_T4'})
            colum_selec3 = pivot_df4[['cliente', 'vendedor', 'Total Merry_T4', 'Merry_T4']]
###################################################################################################################################################################
      
      df_combined = colum_selec.merge(colum_selec2, on=['cliente', 'vendedor'], how='outer')
      df_combined2 = df_combined.merge(colum_selec3, on=['cliente', 'vendedor'], how='outer')

      reports_core = self.env['ztyres_ms_sql_excel_core']
      reports_core.action_insert_dataframe(merged_df_filtered3, 'promos_bridgestone')
      reports_core.action_insert_dataframe(merged_df_filtered4, 'promos_23')
      reports_core.action_insert_dataframe(merged_df_filtered5, 'T4_Plus')
      reports_core.action_insert_dataframe(df_combined2, 'promos_volumen')
      return 