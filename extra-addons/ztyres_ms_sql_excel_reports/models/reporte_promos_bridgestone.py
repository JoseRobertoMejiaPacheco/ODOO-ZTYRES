from odoo import api, fields, models
import math
import pandas as pd
from datetime import datetime, timedelta, date
import numpy as np
from dateutil.relativedelta import relativedelta
from functools import reduce
#from odoo.addons.inv_promo.wizard.models.lista_de_precios import codes, codes2, codes3

class MyModel(models.TransientModel):
    _name = 'reporte_promos_bridgestone'
    
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
    
    def get_all_products(self):
          
      codes_bridgestone = [
            22305, 22568, 22569, 22067, 22079, 22085, 22260, 49652, 22682, 49042, 22086, 62909, 22295, 50301, 22549, 22589, 22118, 
            22097, 22106, 22114, 22140, 22158, 22075, 22356, 22518, 51533, 58465, 22113, 22139, 22726, 22074, 22252, 62897, 63168, 
            51270, 22652, 22811, 22799, 22822, 22823, 22824, 22759, 59868, 62655, 22516, 22162, 22804, 22196, 59744, 22125, 22524, 
            22683, 51129, 22129, 22133, 50300, 22419, 22712, 22603, 22717, 61087, 22814, 48697, 22161, 51666, 22605, 22786, 57693, 
            51851, 22661, 49072, 59267, 49654, 49875, 63175, 57249, 22684, 22711, 51715, 62898, 22155, 48878, 22628, 58933, 49876, 
            58485, 61073, 63176, 61076, 61070, 48953, 22625, 22422, 22474, 62901, 22170, 22630, 62408, 58466, 22284, 59867, 22677, 
            61088, 60952, 59271, 59869, 62404, 59255, 61081, 22281, 22758, 22790, 59870, 22550, 22778, 62654, 62405, 22355, 61085, 
            22741, 58459, 22785, 48877, 22816, 22547, 61072, 48930, 48951, 51579, 59252, 48952, 62899, 22604, 62900, 59242, 59253, 
            62902, 62903, 22633, 51858, 48954, 61086, 59260, 22288, 22829, 51856, 57251, 59748, 62907, 62406, 59258, 22351, 62409, 
            62908, 61084, 59259, 59251, 59745, 62652, 22637, 59243, 22858, 51659, 61074, 59254, 22820, 61075, 22777, 51859, 59270, 
            22817, 62904, 59865, 62653, 62905, 61077, 62906, 58828, 61071, 59256, 59257, 51130, 59747, 22689, 58462, 22860, 22833, 
            59746, 22852, 22826, 49622, 58464, 22827, 61080, 57226, 62407, 62411, 51857, 59749, 22752, 62410, 59871
      ]
    
      codes_goodyear = [ 57246, 58473, 50147, 57522, 19580, 50202, 58488, 59098, 57684, 62649, 9810, 50389, 59245, 61007, 48980]
      
      codes_kumho = [62397, 59762, 51451, 51449, 62613]
      
      codes_prirelli = [
            61691, 48712, 51521, 51336, 49018, 29415, 48713, 49637, 53019, 60987, 60995, 48626, 60991, 28800, 48995, 29435, 62643, 
            62910, 29349, 29901, 61692, 60986, 60997, 49060, 60988
      ]
          
      lista = []
          
      desired_fields = [
            'id',
            'default_code',
            'segment_id',
            'tier_id',
            'manufacturer_id',
            'brand_id',
            'tire_measure_id'
        ]
      domain = [('detailed_type', 'in', ['product']), ('active', 'in', [True, False]), ('tire', '=', True)]
      records = self.env['product.template'].search_read(domain, fields=desired_fields)
        # Extraer solo los valores de las tuplas
      result = [{key: value[1] if isinstance(value, tuple) else value for key, value in record.items()} for record in records]
      df = pd.DataFrame(result)
      #---------------------------------------------------------------------------------------------------------------
      #fecha_actual = date.today()
      ## Obtén el primer día del mes actual
      #primer_dia_mes = fecha_actual.replace(day=1)
      #ultimo_dia_mes = primer_dia_mes.replace(day=28)  # Establece inicialmente el día 28
      #ultimo_dia_mes = ultimo_dia_mes + pd.offsets.MonthEnd(0)  # Ajusta al último día del mes
      
      primer_dia_mes = pd.to_datetime('2025-12-01')  # Primer día de abril de 2024
      ultimo_dia_mes = pd.to_datetime('2025-12-31')  # Último día de abril de 2024
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
                 END as piezas_facturadas,
                 am.currency_id as divisa
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

      df2['price_total'] = df2.apply(lambda row: self.convert_to_company_currency(row['divisa'], row['price_total'], row['fecha_factura']), axis=1)

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
      merged_df3['rin'] = (merged_df3['tire_measure_id'].str.extract(r'R(\d+)', expand=False).astype('Int64'))

      volumen_df = merged_df3.copy()
      
      merged_df_filtered3 = merged_df3[(merged_df3['id'].isin(codes_bridgestone)) & (merged_df3['rin'].isin([17,18,19,20,21,22,23,24]))]
      merged_df_filtered3['cantidadXfactura'] = merged_df_filtered3.groupby('cliente')['cantidad'].transform('sum')

      merged_df_filtered8 = merged_df3[(merged_df3['id'].isin(codes_bridgestone)) & (merged_df3['rin'].isin([13,14,15,16]))]
      merged_df_filtered8['cantidadXfactura'] = merged_df_filtered8.groupby('cliente')['cantidad'].transform('sum')
      
      merged_df_filtered5 = merged_df3[(merged_df3['id'].isin(codes_goodyear))]
      merged_df_filtered5['cantidadXfactura'] = merged_df_filtered5.groupby('cliente')['cantidad'].transform('sum')
      
      merged_df_filtered6 = merged_df3[(merged_df3['id'].isin(codes_kumho))]
      merged_df_filtered6['cantidadXfactura'] = merged_df_filtered6.groupby('cliente')['cantidad'].transform('sum')
      
      merged_df_filtered7 =merged_df3[(merged_df3['id'].isin(codes_prirelli))]
      merged_df_filtered7['cantidadXfactura'] = merged_df_filtered7.groupby('cliente')['cantidad'].transform('sum')
      
      merged_df_filtered9 =merged_df3[(merged_df3['manufacturer_id'].isin(['MILESTAR', 'VENOM']))]
      merged_df_filtered9['cantidadXfactura'] = merged_df_filtered9.groupby('cliente')['cantidad'].transform('sum')

      merged_df_filtered10 =merged_df3[(merged_df3['manufacturer_id'].isin(['ONYX']))]
      merged_df_filtered10['cantidadXfactura'] = merged_df_filtered10.groupby('cliente')['cantidad'].transform('sum')
      
      merged_df_filtered11 =merged_df3[(merged_df3['manufacturer_id'].isin(['FEDERAL']))]
      merged_df_filtered11['cantidadXfactura'] = merged_df_filtered11.groupby('cliente')['cantidad'].transform('sum')
      
      merged_df_filtered12 =merged_df3[(merged_df3['manufacturer_id'].isin(['DRC']))]
      merged_df_filtered12['cantidadXfactura'] = merged_df_filtered12.groupby('cliente')['cantidad'].transform('sum')
      
      merged_df_filtered13 =merged_df3[(merged_df3['manufacturer_id'].isin(['APTANY', 'SENTURY', 'DOUBLESTAR', 'SUNFULCESS']))]
      merged_df_filtered13['cantidadXfactura'] = merged_df_filtered13.groupby('cliente')['cantidad'].transform('sum')
#################################################################### PROMOS VOLUMEN ####################################################################
                                                     #Promos Volumen BRIDGESTONE

      # 2️⃣ Filtrar solo Bridgestone y rines válidos
      volumen_df3 = volumen_df[(volumen_df['id'].isin(codes_bridgestone)) & (volumen_df['rin'].isin([13, 14, 15, 16]))]
      
      
      
      volumen_df3 = volumen_df3.rename(columns={'price_total': 'price_total 13-16'})
      
      if volumen_df3.empty:
            pivot_13 = pd.DataFrame(
                  columns=['cliente', 'vendedor', 'price_total 13-16', 'BRIDGESTONE R13-16']
            )

      else:
            pivot_13 = volumen_df3.pivot_table(index=['cliente', 'vendedor'], values='price_total 13-16', aggfunc='sum', fill_value=0)
            pivot_13.reset_index(inplace=True)
            # 5️⃣ Reglas de promoción

            # 🔹 Rin 13–16
            pivot_13.loc[(pivot_13['price_total 13-16'] >= 580000),'BRIDGESTONE R13-16'] = 'Nc mensual 8%'
            pivot_13.loc[(pivot_13['price_total 13-16'] >= 46400) & (pivot_13['price_total 13-16'] < 580000),'BRIDGESTONE R13-16'] = 'Nc mensual 5%'


      volumen_df8 = volumen_df[(volumen_df['id'].isin(codes_bridgestone)) & (volumen_df['rin'].isin([17, 18, 19, 20, 21, 22, 23, 24]))]
      volumen_df8 = volumen_df8.rename(columns={'price_total': 'price_total 17+'})

      if volumen_df8.empty:
            pivot_17 = pd.DataFrame(
                  columns=['cliente', 'vendedor', 'price_total 17+', 'BRIDGESTONE R17+']
            )

      else:
            # 4️⃣ Pivot CONSERVANDO rin (agregado)
            pivot_17 = volumen_df8.pivot_table(index=['cliente', 'vendedor'], values='price_total 17+', aggfunc='sum',fill_value=0)
            pivot_17.reset_index(inplace=True)
            # 5️⃣ Reglas de promoción
            
            # 🔹 Rin 17–24
            pivot_17.loc[(pivot_17['price_total 17+'] >= 46400), 'BRIDGESTONE R17+'] = 'Nc mensual 8%'


            pivot_df2 = pivot_13.merge(pivot_17, on=['cliente', 'vendedor'], how='outer')
            pivot_df2 = pivot_df2.rename(columns={'price_total 13-16': 'Total Brid 13-16'})
            pivot_df2 = pivot_df2.rename(columns={'price_total 17+': 'Total Brid 17+'})
            colum_selec = pivot_df2[['cliente', 'vendedor', 'Total Brid 13-16', 'BRIDGESTONE R13-16', 'Total Brid 17+', 'BRIDGESTONE R17+']]

#################################################################### PROMOS VOLUMEN ####################################################################
                                                     #Promos Volumen MILESTAR
      volumen_df5 = volumen_df[(volumen_df['id'].isin(codes_goodyear))]
      
      if volumen_df5.empty:
            pivot_df4 = pd.DataFrame(columns=['cliente', 'vendedor', 'Total Goodyear', 'Goodyear'])  # Define las columnas esperadas
            colum_selec3 = pivot_df4[['cliente', 'vendedor', 'Total Goodyear', 'Goodyear']]
      else:
            pivot_df4 = volumen_df5.pivot_table(index=['cliente', 'vendedor'], values='cantidad', aggfunc='sum', fill_value=0)
            pivot_df4.reset_index(inplace=True)
            
            pivot_df4.loc[(pivot_df4['cantidad'] >= 600), ['Goodyear']] = ['Nc mensual 7%']
            pivot_df4.loc[(pivot_df4['cantidad'] >= 350) & (pivot_df4['cantidad'] < 600), ['Goodyear']] = ['Nc mensual 6%']
            pivot_df4.loc[(pivot_df4['cantidad'] >= 150) & (pivot_df4['cantidad'] < 350), ['Goodyear']] = ['Nc mensual 4%']
            pivot_df4.loc[(pivot_df4['cantidad'] >= 1) & (pivot_df4['cantidad'] < 150), ['Goodyear']] = ['Nc mensual 2%']
            
            pivot_df4 = pivot_df4.rename(columns={'cantidad': 'Total Goodyear'})
            colum_selec3 = pivot_df4[['cliente', 'vendedor', 'Total Goodyear', 'Goodyear']]
#################################################################### PROMOS VOLUMEN ####################################################################
                                                     #Promos Volumen  TIER 4
      volumen_df6 = volumen_df[(volumen_df['id'].isin(codes_kumho))]
      
      if volumen_df6.empty:
            pivot_df4 = pd.DataFrame(columns=['cliente', 'vendedor', 'Total Kumho', 'Kumho'])  # Define las columnas esperadas
            colum_selec4 = pivot_df4[['cliente', 'vendedor', 'Total Kumho', 'Kumho']]
      else:
            pivot_df4 = volumen_df6.pivot_table(index=['cliente', 'vendedor'], values='cantidad', aggfunc='sum', fill_value=0)
            pivot_df4.reset_index(inplace=True)
            
            pivot_df4.loc[(pivot_df4['cantidad'] >= 600), ['Kumho']] = ['Nc mensual 8%']
            pivot_df4.loc[(pivot_df4['cantidad'] >= 350) & (pivot_df4['cantidad'] < 600), ['Kumho']] = ['Nc mensual 8%']
            pivot_df4.loc[(pivot_df4['cantidad'] >= 150) & (pivot_df4['cantidad'] < 350), ['Kumho']] = ['Nc mensual 6%']
            
            pivot_df4 = pivot_df4.rename(columns={'cantidad': 'Total Kumho'})
            colum_selec4 = pivot_df4[['cliente', 'vendedor', 'Total Kumho', 'Kumho']]
#################################################################### PROMOS VOLUMEN ####################################################################
                                                     #Promos Volumen  VENOM
      volumen_df7 = volumen_df[(volumen_df['id'].isin(codes_prirelli))]
      
      if volumen_df7.empty:
            pivot_df4 = pd.DataFrame(columns=['cliente', 'vendedor', 'Total Pirelli', 'Pirelli'])  # Define las columnas esperadas
            colum_selec5 = pivot_df4[['cliente', 'vendedor', 'Total Pirelli', 'Pirelli']]
      else:
            pivot_df4 = volumen_df7.pivot_table(index=['cliente', 'vendedor'], values='cantidad', aggfunc='sum', fill_value=0)
            pivot_df4.reset_index(inplace=True)
            
            pivot_df4.loc[(pivot_df4['cantidad'] >= 600), ['Pirelli']] = ['Nc mensual 5%']
            pivot_df4.loc[(pivot_df4['cantidad'] >= 350) & (pivot_df4['cantidad'] < 600), ['Pirelli']] = ['Nc mensual 5%']
            pivot_df4.loc[(pivot_df4['cantidad'] >= 150) & (pivot_df4['cantidad'] < 350), ['Pirelli']] = ['Nc mensual 5%']
            pivot_df4.loc[(pivot_df4['cantidad'] >= 1) & (pivot_df4['cantidad'] < 150), ['Pirelli']] = ['Nc mensual 5%']
            
            pivot_df4 = pivot_df4.rename(columns={'cantidad': 'Total Pirelli'})
            colum_selec5 = pivot_df4[['cliente', 'vendedor', 'Total Pirelli', 'Pirelli']]
###################################################################################################################################################################
      volumen_df9 = volumen_df[(volumen_df['manufacturer_id'].isin(['MILESTAR', 'VENOM']))]
      
      if volumen_df9.empty:
            pivot_df5 = pd.DataFrame(columns=['cliente', 'vendedor', 'Total mil_ven', 'mil_ven'])  # Define las columnas esperadas
            colum_selec6 = pivot_df5[['cliente', 'vendedor', 'Total mil_ven', 'mil_ven']]
      else:
            pivot_df5 = volumen_df9.pivot_table(index=['cliente', 'vendedor'], values='cantidad', aggfunc='sum', fill_value=0)
            pivot_df5.reset_index(inplace=True)
            
            pivot_df5.loc[(pivot_df5['cantidad'] >= 600), ['mil_ven']] = ['Nc mensual 5%']
            pivot_df5.loc[(pivot_df5['cantidad'] >= 350) & (pivot_df5['cantidad'] < 600), ['mil_ven']] = ['Nc mensual 5%']
            pivot_df5.loc[(pivot_df5['cantidad'] >= 150) & (pivot_df5['cantidad'] < 350), ['mil_ven']] = ['Nc mensual 3%']
            pivot_df5.loc[(pivot_df5['cantidad'] >= 1) & (pivot_df5['cantidad'] < 150), ['mil_ven']] = ['Nc mensual 1%']
            
            pivot_df5 = pivot_df5.rename(columns={'cantidad': 'Total mil_ven'})
            colum_selec6 = pivot_df5[['cliente', 'vendedor', 'Total mil_ven', 'mil_ven']]
            
###################################################################################################################################################################
      volumen_df10 = volumen_df[(volumen_df['manufacturer_id'].isin(['ONYX']))]
      
      if volumen_df10.empty:
            pivot_df6 = pd.DataFrame(columns=['cliente', 'vendedor', 'Total Onyx', 'Onyx'])  # Define las columnas esperadas
            colum_selec7 = pivot_df6[['cliente', 'vendedor', 'Total Onyx', 'Onyx']]
      else:
            pivot_df6 = volumen_df10.pivot_table(index=['cliente', 'vendedor'], values='cantidad', aggfunc='sum', fill_value=0)
            pivot_df6.reset_index(inplace=True)
            
            pivot_df6.loc[(pivot_df6['cantidad'] >= 600), ['Onyx']] = ['Nc mensual 12%']
            pivot_df6.loc[(pivot_df6['cantidad'] >= 350) & (pivot_df6['cantidad'] < 600), ['Onyx']] = ['Nc mensual 12%']
            pivot_df6.loc[(pivot_df6['cantidad'] >= 150) & (pivot_df6['cantidad'] < 350), ['Onyx']] = ['Nc mensual 12%']
            pivot_df6.loc[(pivot_df6['cantidad'] >= 1) & (pivot_df6['cantidad'] < 150), ['Onyx']] = ['Nc mensual 12%']

            pivot_df6 = pivot_df6.rename(columns={'cantidad': 'Total Onyx'})
            colum_selec7 = pivot_df6[['cliente', 'vendedor', 'Total Onyx', 'Onyx']]
            
###################################################################################################################################################################
      volumen_df11 = volumen_df[(volumen_df['manufacturer_id'].isin(['FEDERAL']))]
      
      if volumen_df11.empty:
            pivot_df7 = pd.DataFrame(columns=['cliente', 'vendedor', 'Total Federal', 'Federal'])  # Define las columnas esperadas
            colum_selec8 = pivot_df7[['cliente', 'vendedor', 'Total Federal', 'Federal']]
      else:
            pivot_df7 = volumen_df11.pivot_table(index=['cliente', 'vendedor'], values='cantidad', aggfunc='sum', fill_value=0)
            pivot_df7.reset_index(inplace=True)
            
            pivot_df7.loc[(pivot_df7['cantidad'] >= 600), ['Federal']] = ['Nc mensual 5%']
            pivot_df7.loc[(pivot_df7['cantidad'] >= 350) & (pivot_df7['cantidad'] < 600), ['Federal']] = ['Nc mensual 5%']
            pivot_df7.loc[(pivot_df7['cantidad'] >= 150) & (pivot_df7['cantidad'] < 350), ['Federal']] = ['Nc mensual 3%']
            pivot_df7.loc[(pivot_df7['cantidad'] >= 1) & (pivot_df7['cantidad'] < 150), ['Federal']] = ['Nc mensual 1%']

            pivot_df7 = pivot_df7.rename(columns={'cantidad': 'Total Federal'})
            colum_selec8 = pivot_df7[['cliente', 'vendedor', 'Total Federal', 'Federal']]
###################################################################################################################################################################
      volumen_df12 = volumen_df[(volumen_df['manufacturer_id'].isin(['DRC']))]
      
      if volumen_df12.empty:
            pivot_df8 = pd.DataFrame(columns=['cliente', 'vendedor', 'Total Driverforce', 'Driverforce'])  # Define las columnas esperadas
            colum_selec9 = pivot_df8[['cliente', 'vendedor', 'Total Driverforce', 'Driverforce']]
      else:
            pivot_df8 = volumen_df12.pivot_table(index=['cliente', 'vendedor'], values='cantidad', aggfunc='sum', fill_value=0)
            pivot_df8.reset_index(inplace=True)
            
            pivot_df8.loc[(pivot_df8['cantidad'] >= 600), ['Driverforce']] = ['Nc mensual 12%']
            pivot_df8.loc[(pivot_df8['cantidad'] >= 350) & (pivot_df8['cantidad'] < 600), ['Driverforce']] = ['Nc mensual 12%']
            pivot_df8.loc[(pivot_df8['cantidad'] >= 150) & (pivot_df8['cantidad'] < 350), ['Driverforce']] = ['Nc mensual 8%']
            pivot_df8.loc[(pivot_df8['cantidad'] >= 1) & (pivot_df8['cantidad'] < 150), ['Driverforce']] = ['Nc mensual 6%']

            pivot_df8 = pivot_df8.rename(columns={'cantidad': 'Total Driverforce'})
            colum_selec9 = pivot_df8[['cliente', 'vendedor', 'Total Driverforce', 'Driverforce']]
###################################################################################################################################################################
      volumen_df13 = volumen_df[(volumen_df['manufacturer_id'].isin(['APTANY', 'SENTURY', 'DOUBLESTAR', 'SUNFULCESS']))]
      
      if volumen_df13.empty:
            pivot_df9 = pd.DataFrame(columns=['cliente', 'vendedor', 'Total ADDF', 'ADDF'])  # Define las columnas esperadas
            colum_selec10 = pivot_df9[['cliente', 'vendedor', 'Total ADDF', 'ADDF']]
      else:
            pivot_df9 = volumen_df13.pivot_table(index=['cliente', 'vendedor'], values='cantidad', aggfunc='sum', fill_value=0)
            pivot_df9.reset_index(inplace=True)
            
            pivot_df9.loc[(pivot_df9['cantidad'] >= 600), ['ADDF']] = ['Nc mensual 3%']
            pivot_df9.loc[(pivot_df9['cantidad'] >= 350) & (pivot_df9['cantidad'] < 600), ['ADDF']] = ['Nc mensual 3%']
            pivot_df9.loc[(pivot_df9['cantidad'] >= 150) & (pivot_df9['cantidad'] < 350), ['ADDF']] = ['Nc mensual 2%']

            pivot_df9 = pivot_df9.rename(columns={'cantidad': 'Total ADDF'})
            colum_selec10 = pivot_df9[['cliente', 'vendedor', 'Total ADDF', 'ADDF']]

      df_combined = colum_selec.merge(colum_selec3, on=['cliente', 'vendedor'], how='outer')
      df_combined3 = df_combined.merge(colum_selec4, on=['cliente', 'vendedor'], how='outer')
      df_combined4 = df_combined3.merge(colum_selec5, on=['cliente', 'vendedor'], how='outer')
      df_combined5 = df_combined4.merge(colum_selec6, on=['cliente', 'vendedor'], how='outer')
      df_combined6 = df_combined5.merge(colum_selec7, on=['cliente', 'vendedor'], how='outer')
      df_combined7 = df_combined6.merge(colum_selec8, on=['cliente', 'vendedor'], how='outer')
      df_combined8 = df_combined7.merge(colum_selec9, on=['cliente', 'vendedor'], how='outer')
      df_combined9 = df_combined8.merge(colum_selec10, on=['cliente', 'vendedor'], how='outer')


      lista.append(('promos_volumen', df_combined9))
      lista.append(('bridgestone_17+', merged_df_filtered3))
      lista.append(('bridgestone_13_16', merged_df_filtered8))
      lista.append(('Goodyear', merged_df_filtered5))
      lista.append(('Kumho', merged_df_filtered6))
      lista.append(('Pirelli', merged_df_filtered7))
      lista.append(('Milestar_Venom', merged_df_filtered9))
      lista.append(('Onyx', merged_df_filtered10))
      lista.append(('Federal', merged_df_filtered11))
      lista.append(('Driverforce', merged_df_filtered12))
      lista.append(('APT_DEL_DOUBL_FIRe', merged_df_filtered13))
      
      return lista