#pip install pyodbc sqlalchemy
#apt-get install unixodbc
from odoo import api, fields, models
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta

class MyModel(models.TransientModel):
    _name = 'reports_ventas'

    def generate_report(self, vendedor_id):
        reports_direccion = self.env['reports_direccion_ventas']
        meses = [] 
        meses_map = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]

        # Obtener todos los productos y crear un DataFrame
        product_data = reports_direccion.get_all_products()
        product_df = reports_direccion.dict_to_df(product_data)
        
        # Obtener detalles de los últimos seis meses
        last_six_months = reports_direccion.last_six_months_details()
        
        # Aplicar transformaciones y agregar datos al DataFrame
        transformed_df = self.transform_data(product_df, last_six_months, vendedor_id=vendedor_id)

        # Renombrar columnas
        transformed_df = self.rename_columns(transformed_df)
        
        for col in transformed_df.columns:
            if col in meses_map:
                meses.append(col)
                
        transformed_df['Trans'].fillna(0, inplace=True)
        transformed_df['BO'].fillna(0, inplace=True)
        
        columnas = [c for c in transformed_df.columns if c in meses_map]
        columnas += ['Inv', 'Res', 'Disp', 'Trans', 'BO']

        transformed_df = transformed_df[ ~(transformed_df[columnas] == 0).all(axis=1)]
                
        reports_core = self.env['ztyres_ms_sql_excel_core']
        
        table_name = (f"reporte_direccion_ventas_{vendedor_id}"
                        if vendedor_id
                        else "reporte_direccion_ventas")

        reports_core.action_insert_dataframe(transformed_df, table_name)

    def transform_data(self, product_df, last_six_months, vendedor_id):
        reports_direccion = self.env['reports_direccion_ventas']
        transformed_df = product_df.copy()

        transformed_df = reports_direccion.add_month(
            transformed_df,
            'out_invoice',
            'out_refund',
            last_six_months,
            vendedor_id=vendedor_id
        )

        transformed_df = reports_direccion.add_transit(transformed_df)
        transformed_df = self.add_price_lists(transformed_df)
        transformed_df = reports_direccion.add_origin(transformed_df)
        transformed_df = reports_direccion.add_upf(transformed_df)
        transformed_df = reports_direccion.add_backorder(transformed_df)

        return transformed_df

    def add_price_lists(self, dataframe):
        reports_direccion = self.env['reports_direccion_ventas']
        # Agregar datos de la lista de precios 'MAYOREO'
        dataframe = reports_direccion.add_price_list(dataframe, 1, 'mayoreo')
        #Agregar datos de la lista de precios 'OUTLET'
        dataframe = reports_direccion.add_price_list(dataframe, 108, 'outlet')
        
        return dataframe

    def rename_columns(self, dataframe):
        meses = {} 
        
        meses_map = {
            "'ENERO'": "ENE",
            "'FEBRERO'": "FEB",
            "'MARZO'": "MAR",
            "'ABRIL'": "ABR",
            "'MAYO'": "MAY",
            "'JUNIO'": "JUN",
            "'JULIO'": "JUL",
            "'AGOSTO'": "AGO",
            "'SEPTIEMBRE'": "SEP",
            "'OCTUBRE'": "OCT",
            "'NOVIEMBRE'": "NOV",
            "'DICIEMBRE'": "DIC",
        }

        for col in dataframe.columns:
            if col in meses_map.keys():
                meses[col] = meses_map[col]

        new_names = {
            "id": "Id",
            "default_code": "Codigo",
            "cui": "CIU",
            "name": "Nombre",
            "tire_measure_id": "Medida",
            "face_id": "Cara",
            "layer_id": "C",
            "speed_id": "V",
            "index_of_load_id": "L",
            "model_id": "Modelo",
            "brand_id": "Marca",
            "manufacturer_id": "Fabricante",
            "segment_id": "Seg",
            "type_id": "Tipo",
            "tier_id": "Tier",
            "product_dot_range": "DOT",
            "country_of_origin": "Origen",
        }
        
        new_names.update(meses)
            
        new_names.update({
            "qty_available": "Inv",
            "qty_reserved": "Res",
            "free_qty": "Disp",
            "transito": "Trans",
            "purchase_backorder": "BO",
            "'mayoreo'": "Mayoreo",
            "'outlet'" : "Outlet",
            "upf": "UPF",
            "fecha_upf": "FUPF",
        })
        
        # Crear un nuevo DataFrame con las columnas en el orden deseado
        ordered_dataframe = dataframe[list(new_names.keys())]
        
        # Renombrar las columnas
        ordered_dataframe = ordered_dataframe.rename(columns=new_names)
        
        return ordered_dataframe