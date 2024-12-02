from odoo import api, fields, models
import math
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta


class Ultimocosto(models.TransientModel):
  _name = 'ztyres_reporte_ultimo_costo'
  
  def convert_to_company_currency(self, currency_id, amount, date):
        if currency_id is not None and not math.isnan(amount) and not pd.isna(date):
            currency_record = self.env['res.currency'].browse(int(currency_id))
            converted_amount = currency_record._convert(
                amount,
                currency_record.env.company.currency_id,
                currency_record.env.company,
                date
                )
        else: 
            return 0
        return converted_amount

  def get_report(self):
    
      desired_fields = [
            'id',
            'default_code',
            'manufacturer_id',
            'qty_available'
        ]
      records = self.env['product.template'].search_read([('detailed_type', 'in', ['product'])], fields=desired_fields)
      # Extraer solo los valores de las tuplas
      result2 = [{key: value[1] if isinstance(value, tuple) else value for key, value in record.items()} for record in records]
      df2 = pd.DataFrame(result2)
    
    
      ####Consulta Sql Probada
      query = """
            WITH ComprasEnumeradas AS (
              SELECT
                pt.id,
                pp.default_code,
                pol.name,
                pol.product_qty,
                pol.price_unit,
                po.currency_id,
                po.date_approve,
                pol.state,
                ROW_NUMBER() OVER (PARTITION BY pp.id ORDER BY pol.create_date DESC) as numero_orden
              FROM
                purchase_order_line pol
                JOIN purchase_order po ON pol.order_id = po.id
                JOIN product_product pp ON pol.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
              WHERE
                pol.state IN ('purchase')
              AND 
                pol.product_qty != 0
            )
            SELECT
              id,
              currency_id AS tipo_cambio,
              default_code,
              MAX(CASE WHEN numero_orden = 1 THEN name END) as Producto,
              MAX(CASE WHEN numero_orden = 1 THEN product_qty END) as cantidad_1,
              MAX(CASE WHEN numero_orden = 1 THEN price_unit END) as costo_1,
              MAX(CASE WHEN numero_orden = 1 THEN date_approve END) as fecha_1,
              MAX(CASE WHEN numero_orden = 2 THEN product_qty END) as cantidad_2,
              MAX(CASE WHEN numero_orden = 2 THEN price_unit END) as costo_2,
              MAX(CASE WHEN numero_orden = 2 THEN date_approve END) as fecha_2,
              MAX(CASE WHEN numero_orden = 3 THEN product_qty END) as cantidad_3,
              MAX(CASE WHEN numero_orden = 3 THEN price_unit END) as costo_3,
              MAX(CASE WHEN numero_orden = 3 THEN date_approve END) as fecha_3,
              MAX(CASE WHEN numero_orden = 4 THEN product_qty END) as cantidad_4,
              MAX(CASE WHEN numero_orden = 4 THEN price_unit END) as costo_4,
              MAX(CASE WHEN numero_orden = 4 THEN date_approve END) as fecha_4,
              MAX(CASE WHEN numero_orden = 5 THEN product_qty END) as cantidad_5,
              MAX(CASE WHEN numero_orden = 5 THEN price_unit END) as costo_5,
              MAX(CASE WHEN numero_orden = 5 THEN date_approve END) as fecha_5
            FROM
              ComprasEnumeradas
            WHERE
              numero_orden <= 5
            GROUP BY
              id, default_code, currency_id
          """
      ##Retornar la consulta sql
      self.env.cr.execute(query)
      result = self.env.cr.dictfetchall()        
      #Crear dataframe dla consulta
      df = pd.DataFrame(result)
      
      df['costo_de_compra_1'] = df.apply(lambda row: self.convert_to_company_currency(row['tipo_cambio'], row['costo_1'], row['fecha_1']), axis=1)
      df['costo_de_compra_2'] = df.apply(lambda row: self.convert_to_company_currency(row['tipo_cambio'], row['costo_2'], row['fecha_2']), axis=1)
      df['costo_de_compra_3'] = df.apply(lambda row: self.convert_to_company_currency(row['tipo_cambio'], row['costo_3'], row['fecha_3']), axis=1)
      df['costo_de_compra_4'] = df.apply(lambda row: self.convert_to_company_currency(row['tipo_cambio'], row['costo_4'], row['fecha_4']), axis=1)
      df['costo_de_compra_5'] = df.apply(lambda row: self.convert_to_company_currency(row['tipo_cambio'], row['costo_5'], row['fecha_5']), axis=1)
      res = df[['id','costo_de_compra_1', 'costo_de_compra_2', 'costo_de_compra_3', 'costo_de_compra_4', 'costo_de_compra_5']]
      
      columnas_seleccionadas = df[['id', 'default_code', 'producto', 'cantidad_1', 'costo_de_compra_1', 'cantidad_2', 'costo_de_compra_2', 'cantidad_3', 'costo_de_compra_3', 'cantidad_4', 'costo_de_compra_4', 'cantidad_5', 'costo_de_compra_5']]
      
      merged_df  = pd.merge(columnas_seleccionadas, df2, on='id', how='left', suffixes=('_x', '_y'))
 
      columnas_seleccionadas2 = merged_df[['id', 'manufacturer_id', 'default_code_x', 'producto', 'qty_available', 'cantidad_1', 'costo_de_compra_1', 'cantidad_2', 'costo_de_compra_2', 'cantidad_3', 'costo_de_compra_3', 'cantidad_4', 'costo_de_compra_4', 'cantidad_5', 'costo_de_compra_5']]
      

      ##Instanciar la clase ztyres_ms_sql_excel_core que tiene el metodo para insertar un dataframe en sql server
      reports_core = self.env['ztyres_ms_sql_excel_core']
      reports_core.action_insert_dataframe(columnas_seleccionadas2, 'reporte_ultimo_costo')
      return 