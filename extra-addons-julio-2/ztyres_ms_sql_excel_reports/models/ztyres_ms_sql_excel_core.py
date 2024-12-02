from odoo import api, fields, models
from ..scripts.insert_df import df_to_postgres
import pyodbc
from sqlalchemy import create_engine

class MyModel(models.TransientModel):
    _name = 'ztyres_ms_sql_excel_core'

    def action_insert_dataframe_postgres_sql(self, df, report_name):
        df_to_postgres(df, report_name)

    def action_insert_dataframe(self,df,report_name):
            # Establece la conexión con SQL Server
            conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};'
                                'SERVER=192.168.1.3;'
                                'DATABASE=reportes_ztyres;'
                                'UID=sa;'
                                'PWD=a750105530A12345;')
            cursor = conn.cursor()
            # Borrar la tabla temporal si existe
            cursor.execute("IF OBJECT_ID('%s', 'U') IS NOT NULL DROP TABLE %s;"%(report_name,report_name))
            conn.commit()
            # Usar SQLAlchemy como intermediario para insertar el DataFrame 
            # (esto es más eficiente que insertar fila por fila)
            from sqlalchemy import create_engine
            engine = create_engine('mssql+pyodbc://sa:a750105530A12345@192.168.1.3/reportes_ztyres?driver=ODBC+Driver+17+for+SQL+Server')
            df.to_sql('%s'%(report_name), engine, if_exists='replace',
            index=False
            )
            cursor.close()
            conn.close()
            return
        

