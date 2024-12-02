#pip install pyodbc sqlalchemy
#apt-get install unixodbc
from odoo import api, fields, models
import pandas as pd
import numpy as np

class MyModel(models.TransientModel):
    _name = 'ztyres_ms_sql_excel_reports'

    def generate_report(self):
        reports_direccion = self.env['ztyres_ms_sql_excel_reports_direccion']
        
        # Obtener todos los productos y crear un DataFrame
        product_data = reports_direccion.get_all_products()
        product_df = reports_direccion.dict_to_df(product_data)
        
        # Obtener detalles de los últimos seis meses
        last_six_months = reports_direccion.last_six_months_details()
        
        # Aplicar transformaciones y agregar datos al DataFrame
        transformed_df = self.transform_data(product_df, last_six_months)

        # Renombrar columnas
        transformed_df = self.rename_columns(transformed_df)
        
        transformed_df.loc[transformed_df['Trans'] < 0, 'Trans'] = 0
        transformed_df.loc[transformed_df['BO'].isnull(), 'CBO'] = np.nan
        
        archivados_df = transformed_df.copy()
        transformed_df = transformed_df.loc[transformed_df['active'] == 1]
        transformed_df = transformed_df.drop(columns=['active'])
        
        fob_cif = transformed_df.copy()
        
        columnas_deseadas = ['Id', 'Codigo', 'Medida', 'Cara', 'Capas', 'Vel', 'Carga', 'Modelo', 'Marca', 'Fabricante', 'Seg', 'Tipo', 
                             'Tier', 'Origen', 'Inv', 'Trans', 'Outlet', 'UCF', 'UCFinal', 'FUCF', 'CPF', 'CFinalP', 'BO', 'CBO']
        
        fob_cif = fob_cif[columnas_deseadas]
        # Filtrar por valores específicos en la columna 'Fabricante'
        fob_cif = fob_cif.loc[fob_cif['Fabricante'].isin(['CONTINENTAL', 'GOODYEAR', 'PIRELLI', 'BRIDGESTONE'])]
        # Filtrar por valores específicos en la columna 'Marca'
        fob_cif = fob_cif.loc[~fob_cif['Marca'].isin(['G-MAX', 'ROADMASTER'])]
       
        fob_cif = fob_cif.sort_values(by=['Medida', 'Tier', 'Seg', 'Tipo'])
        
        transformed_df = transformed_df.sort_values(by=['Medida', 'Tier', 'Seg', 'Tipo', 'Mayoreo'])
        
        # Exportar el DataFrame a un archivo Excel
        # self.export_to_excel(transformed_df)
        # Insertar el DataFrame en la base de datos
        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(transformed_df, 'reporte_direccion')
        reports_core.action_insert_dataframe(archivados_df, 'reporte_direccion_archivados')
        reports_core.action_insert_dataframe(fob_cif, 'reporte_fob_cif')

    def transform_data(self, product_df, last_six_months):
        reports_direccion = self.env['ztyres_ms_sql_excel_reports_direccion']
        transformed_df = product_df.copy()
        transformed_df = reports_direccion.add_month(transformed_df, 'out_invoice', 'out_refund', last_six_months)
        transformed_df = reports_direccion.add_transit(transformed_df)
        # Agregar datos de la lista de precios
        transformed_df = self.add_price_lists(transformed_df)
        transformed_df = reports_direccion.add_last_price_unit(transformed_df)
        transformed_df = reports_direccion.add_origin(transformed_df)
        transformed_df = reports_direccion.add_ucfact(transformed_df)
        transformed_df = reports_direccion.add_avg_ucfact(transformed_df)
        transformed_df = reports_direccion.add_backorder(transformed_df)
        transformed_df = reports_direccion.add_ucfinal(transformed_df)
        transformed_df = reports_direccion.add_avg_x_studio_costo_final(transformed_df)
        transformed_df = reports_direccion.add_upf(transformed_df)
        
        return transformed_df

    def add_price_lists(self, dataframe):
        reports_direccion = self.env['ztyres_ms_sql_excel_reports_direccion']
        # Agregar datos de la lista de precios 'MAYOREO'
        dataframe = reports_direccion.add_price_list(dataframe, 1, 'mayoreo')
        #Agregar datos de la lista de precios 'OUTLET'
        dataframe = reports_direccion.add_price_list(dataframe, 108, 'outlet')
        # Agregar datos de la lista de precios 'PROMOCIÓN'
        dataframe = reports_direccion.add_price_list(dataframe, 113, 'promoción')
        
        return dataframe

    def rename_columns(self, dataframe):

        new_names = {
            "id": "Id",
            "default_code": "Codigo",
            "cui": "CIU",
            "name": "Nombre",
            "tire_measure_id": "Medida",
            "face_id": "Cara",
            "layer_id": "Capas",
            "speed_id": "Vel",
            "index_of_load_id": "Carga",
            "model_id": "Modelo",
            "brand_id": "Marca",
            "manufacturer_id": "Fabricante",
            "segment_id": "Seg",
            "type_id": "Tipo",
            "tier_id": "Tier",
            "country_of_origin": "Origen",
            "'JULIO'": 'JUL',
            "'AGOSTO'": 'AGO',
            "'SEPTIEMBRE'": 'SEP',
            "'OCTUBRE'": 'OCT',
            "'NOVIEMBRE'": 'NOV',
            "'DICIEMBRE'": 'DIC',
            "qty_available": "Inv",
            "qty_reserved": "Res",
            "free_qty": "Disp",
            "transito": "Trans",
            "'mayoreo'": "Mayoreo",
            "'promoción'": "prom",
            "'outlet'" : "Outlet",
            "upf": "UPF",
            "fecha_upf": "FUPF",
            "ultimo_costo_factura" : "UCF",
            "ultimo_costo_final_": "UCFinal",
            "fecha_ultimo_costo_factura" : "FUCF",
            "standard_price" : "CPF", #Costo_Promdio_Odoo
            #"costo_factura_promedio" : "CFP",
            "costo_final_promedio" : "CFinalP",
            "purchase_backorder": "BO",
            "last_price_unit": "CBO", 
            'active': 'active'
        }
        
        # Crear un nuevo DataFrame con las columnas en el orden deseado
        ordered_dataframe = dataframe[list(new_names.keys())]
        
        # Renombrar las columnas
        ordered_dataframe = ordered_dataframe.rename(columns=new_names)
        
        return ordered_dataframe

    def export_to_excel(self, dataframe):
        dataframe.to_excel('/mnt/extra-addons/TEstttt.xlsx')


# Uso de la función para generar el informe
# self.generate_report()