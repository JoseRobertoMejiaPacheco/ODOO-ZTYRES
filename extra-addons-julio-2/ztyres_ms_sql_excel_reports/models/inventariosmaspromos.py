from odoo import api, fields, models
import math
import pandas as pd
import datetime
import numpy as np
from dateutil.relativedelta import relativedelta

class MyModel(models.TransientModel):
    _name = 'inventariosmaspromos'

    def get_qty(self,product_tmpl_id):
        domain = [('product_tmpl_id', 'in', [product_tmpl_id])]
        pp = self.env['product.product'].search(domain)
        free_qty = pp.free_qty
        return max(0, free_qty)

    def get_all_products(self):
        desired_fields = [
            'id',
            'default_code',
            'name',
            'tire_measure_id',
            'model_id',
            'brand_id',
            'manufacturer_id',
            'index_of_load_id',
            'segment_id',
            'tier_id'
        ]

        records = self.env['product.template'].search_read([('detailed_type', 'in', ['product'])], fields=desired_fields)
        # Extraer solo los valores de las tuplas
        result = [{key: value[1] if isinstance(value, tuple) else value for key, value in record.items()} for record in records]
        df = pd.DataFrame(result)
        df['free_qty'] = df['id'].apply(lambda x: self.get_qty(x))
        df = df.loc [df['free_qty'] != 0]

        query = """
                SELECT ppi.product_tmpl_id AS id, 
                       MAX(CASE WHEN ppi.pricelist_id = 1 THEN ppi.fixed_price END) AS mayoreo,
                       MAX(CASE WHEN ppi.pricelist_id = 113 THEN ppi.fixed_price END) AS promoción,
                       MAX(CASE WHEN ppi.pricelist_id = 108 THEN ppi.fixed_price END) AS outlet
                FROM product_pricelist_item ppi
                LEFT JOIN product_template pt ON ppi.product_tmpl_id = pt.id
                WHERE 
                    ppi.active = TRUE 
                AND pt.tire = TRUE
                GROUP BY ppi.product_tmpl_id, pt.default_code;
        """
        self.env.cr.execute(query)
        result2 = self.env.cr.dictfetchall()        #Crear dataframe de la consulta
        df2 = pd.DataFrame(result2)

        merged_df = pd.merge(df, df2, on='id', how='left')

        #Acumulado
        #merged_df.loc[merged_df['manufacturer_id'] == 'BRIDGESTONE', 'MinLlantasB'] = '50 / 100'
        #merged_df.loc[merged_df['manufacturer_id'] == 'BRIDGESTONE', 'GASOLINA'] = 'Gas 4k/8k'
        
        #merged_df.loc[merged_df['manufacturer_id'] == 'CONTINENTAL', 'MinLlantasC'] = '40 / 80'
        #merged_df.loc[merged_df['manufacturer_id'] == 'CONTINENTAL', 'APP/GAS'] = 'Gas 3k/Apple W'
        
        merged_df.loc[merged_df['manufacturer_id'] == 'GOODYEAR', 'MinLlantasC'] = '25 / 40'
        merged_df.loc[merged_df['manufacturer_id'] == 'GOODYEAR', 'APP/GAS'] = 'Gas 1k / 1.5k'

        #Factura  
        merged_df.loc[(merged_df['manufacturer_id'].isin(['APTANY', 'DELINTE', 'FIREMAX'])) & 
                     (merged_df['tier_id'].isin(['Tier 4'])), 'PROMO TIER 4'] = 'Llantas 150/250/650/1250' 
        
        merged_df.loc[(merged_df['manufacturer_id'].isin(['APTANY', 'DELINTE', 'FIREMAX'])) & 
                     (merged_df['tier_id'].isin(['Tier 4'])), 'Bono TIER 4'] = 'Bono 3K/5K/12K/25K'

        
        #---------------------------------------------------------------------------------------------------------------------------------
        paquetes20 = [(48419, 953.46, 'Kumho 20'),(48974, 654.54, 'Goodyear 24'),(51404, 704.03, 'Kumho 24'),(51006, 1051.66, 'Maxxis 12'),
                      (49747, 727.29, 'Goodyear 24'),(48390, 762.15, 'Kumho 24'),(48701, 788.96, 'Kumho 24'),(48369, 1307.08, 'Kumho 24'),
                      (50222, 1155.41, 'Continental 24'),(50207, 1882.5, 'Continental 8'),(49628, 1261.39, 'Kumho 20'),(47038, 1479.68, 'Kumho 20'),
                      (48360, 1764.99, 'Kumho 12'),(50156, 2189.08, 'Continental 12'),(51458, 1655.49, 'Kumho 20'),(19564, 1821.5, 'Goodyear 20'),
                      (49914, 1989.19, 'Kumho 12'),(51520, 2360.74, 'Kumho 12'),(49752, 2689.52, 'Kumho 12'),(29256, 2799.15, 'Pirelli 8'),
                      (48322, 1984.73, 'Kumho 12'),(19104, 2285.55, 'Goodyear 12'),(48323, 2171.45, 'Kumho 12'),(47561, 2095.24, 'Kumho 12'),
                      (51422, 1487.41, 'Kumho 20'),(51459, 1920.53, 'Kumho 12'),(49025, 2239.6, 'Pirelli 12'),(48292, 2479.84, 'Kumho 12'),
                      (48429, 3398.41, 'Kumho 8'),(51645, 1062.75, 'Maxxis 16'),(51614, 1395.9, 'Continental 12'),(51455, 2207.52, 'Continental 12'),
                      (50318, 1304.63, 'Continental 12'),(51264, 1447.54, 'Continental 12')
        ]

        df_promo20 = pd.DataFrame(paquetes20, columns=['id', 'paquetes', 'ESPECIAL'])
        
        merged_df = pd.merge(merged_df, df_promo20, on='id', how='left')

        #Acumulado
        #merged_df.loc[(merged_df['segment_id'].isin(['AT', 'MT', 'RT'])) & 
        #             (merged_df['tier_id'].isin(['Tier 1', 'Tier 2'])), 'MinLlantasF1'] = '85 / 110 / 180'

        #merged_df.loc[(merged_df['segment_id'].isin(['AT', 'MT', 'RT'])) & 
        #              (merged_df['tier_id'].isin(['Tier 1', 'Tier 2'])), 'F1'] = 'GorraF1 / PlayeraF1 / ChamarraF1'

        merged_dfIVA = merged_df.copy()

        merged_dfIVA['mayoreo'] *=  1.16
        merged_dfIVA['promoción'] *= 1.16
        merged_dfIVA['paquetes'] *= 1.16
        merged_dfIVA['outlet'] *= 1.16

        #Factura 
        promo_3x33 = [(22419,0.875, 'Bs22'),(22305,0.862, 'Bs22'),(22549,0.9055, 'Bs22'),(22086,0.8672, 'Bs22'),(22088,0.8691, 'Bs22'),
                      (22094,0.8668, 'Bs22'),(22106,0.8786, 'Bs22'),(22726,0.9367, 'Bs22'),(22113,0.8677, 'Bs22'),(22118,0.9054, 'Bs22'),
                      (22518,0.8677, 'Bs22'),(51129,0.8626, 'Bs22'),(22524,0.8836, 'Bs22'),(22711,0.8917, 'Bs22'),(22137,0.8728, 'Bs22'),
                      (51666,0.8832, 'Bs22'),(22822,0.8638, 'Bs22'),(22804,0.8624, 'Bs22'),(22605,0.8653, 'Bs22'),(22816,0.8988, 'Bs22'),
                      (22814,0.866, 'Bs22'),(22325,0.8667, 'Bs22'),(22547,0.9084, 'Bs22'),(22175,0.8601, 'Bs22'),(22422,0.9035, 'Bs22'),
                      (48954,0.8626, 'Bs22'),(22288,0.9093, 'Bs22'),(22295,0.8647, 'Bs22'),(22299,0.8665, 'Bs22'),(22516,0.8781, 'Bs22'),
                      (22355,0.8425, 'Bs22'),(22301,0.8658, 'Bs22'),(22827,0.8517, 'Bs22'),(22358,0.8716, 'Bs22'),(22808,0.9409, 'Bs22'),
                      (22318,0.8765, 'Bs22'),(22252,0.9634, 'Bs22')
                      ]

        # Convertir la lista de tuplas a un DataFrame temporal
        df_precios = pd.DataFrame(promo_3x33, columns=['id', 'Descuento', 'Nombre Promoción'])
        df_precios['Volumen'] = 'Paquetes Bs22 (x3, x5, x10, x15, x20)'
        df_precios['Promo'] = 'Bono (3k, 6k, 14k, 26k, 42k)'
        
        # Fusionar los DataFrames utilizando el ID como clave
        df_sin_iva = pd.merge(merged_df, df_precios, on='id', how='left')
        df_con_iva = pd.merge(merged_dfIVA, df_precios, on='id', how='left')
        

#-----------------------------------------------------------------------------------------------------
        # df_paquetes_sin_iva = pd.merge(df_sin_iva, df_promo20, on='id', how='left')
        
        # df_promo20['costo_promo'] *= 1.16
        # df_paquetes_con_iva = pd.merge(df_con_iva,df_promo20, on='id', how='left')
        df_sin_iva = df_sin_iva.drop(columns=['id'])
        df_con_iva = df_con_iva.drop(columns=['id'])

        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(df_sin_iva, 'inv_promos_sin_iva')
        reports_core.action_insert_dataframe(df_con_iva, 'inv_promos_con_iva')

        return 