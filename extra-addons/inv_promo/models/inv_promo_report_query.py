from odoo import models, fields, api
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
import pandas as pd

class InvPromo(models.TransientModel):
    _inherit = 'inv_promo.report'
    _description = 'inv_promo.inv_promo'

    def insert_data(self):
        cr = self.env.cr  # Obtén el cursor de la base de datos
        query = self._table_query()  # Construye la consulta SQL
        df = self.create_dot_dataframe(query)
        vals = df.to_dict(orient='records')
        return self.create(vals)
    
    def get_pricelist_items_promo_dot(self):
        return self.env['product.pricelist.item'].search([('pricelist_id', '=', 122)])
    
    def get_promo_dot_df(self,df):
        
        pricelist_items_promo_dot = self.get_pricelist_items_promo_dot()
        #Revisar si hay un mas de un dot
        #O cuendo un dot esta en la lista y el otro en mayoreo
        promo_dots = pricelist_items_promo_dot.mapped('product_tmpl_id').ids
        df_promo = df[df['product_id'].isin(promo_dots)]
        df_no_promo = df[~df['product_id'].isin(promo_dots)]
        df_promo.to_excel('/mnt/extra-addons/df_promo.xlsx', index=False)      
        df_no_promo.to_excel('/mnt/extra-addons/df_no_promo.xlsx', index=False)      
        return df_promo,df_no_promo

    def process_no_promo_df(self, df_no_promo):
        # Agrupar por 'product_id' y sumar 'available', y mantener el primer valor de las demás columnas
        df_no_promo_grouped = df_no_promo.groupby('product_id').agg(
            available=('available', 'sum'),
            default_code=('default_code', 'first'),
            tire_measure_id=('tire_measure_id', 'first'),
            layer_id=('layer_id', 'first'),
            speed_id=('speed_id', 'first'),
            index_of_load_id=('index_of_load_id', 'first'),
            model_id=('model_id', 'first'),
            brand_id=('brand_id', 'first'),
            tier_id=('tier_id', 'first'),
            lot_name=('lot_name', lambda x: f"{min(x)}-{max(x)}" if len(x.unique()) > 1 else x.iloc[0])
        ).reset_index()

        # Mostrar el DataFrame resultante
        print("DataFrame no promocional agrupado con todos los datos y rango de lot_name:")
        print(df_no_promo_grouped)

        return df_no_promo_grouped
    
    
    def get_df_promo_by_dot(self):
        productos_promocion = []
        pricelist_items_promo_dot = self.get_pricelist_items_promo_dot()   
        for item in pricelist_items_promo_dot:
            product_tmpl_id = item.product_tmpl_id.id
            fixed_price = item.fixed_price
            lot_name = item.lot_name
            productos_promocion.append({
                'product_tmpl_id': product_tmpl_id,
                'promo_dot': fixed_price,
                'lot_name': lot_name or 'N/A'
            })
        print(productos_promocion)
        return productos_promocion            
            
        
    
        
    def create_dot_dataframe(self, query):
        # Ejecutar la consulta SQL
        self.env.cr.execute(query)
        
        # Obtener los resultados de la consulta
        resultados = self.env.cr.fetchall()
        
        # Obtener los nombres de las columnas
        columnas = [desc[0] for desc in self.env.cr.description]
        
        # Crear el DataFrame usando los resultados y las columnas
        df = pd.DataFrame(resultados, columns=columnas)
        
        # Llamar a la función que separa el DataFrame en dos: df_promo y df_no_promo
        df_promo, df_no_promo = self.get_promo_dot_df(df)
        
        # Mostrar df_promo para ver su contenido
         
        
        # Obtener el mapeo de 'promo_dot' con get_df_promo_by_dot
        promo_data = self.get_df_promo_by_dot()  # Lista de diccionarios
        
        # Convertir promo_data en un DataFrame para facilitar el acceso
        df_promo_mapping = pd.DataFrame(promo_data)
        
        # Crear un diccionario de mapeo clave -> (product_id, lot_name) -> promo_dot
        promo_dict = {(row['product_tmpl_id'], row['lot_name']): row['promo_dot'] for _, row in df_promo_mapping.iterrows()}
        
        # Ahora, agregar la columna 'promo_dot' a df usando el mapeo
        df_promo['promo_dot'] = df.apply(
            lambda row: promo_dict.get((row['product_id'], row['lot_name']), 0), axis=1
        )
        
        # Mostrar el DataFrame final
        df_no_promo = self.process_no_promo_df(df_no_promo)
        df_no_promo['promo_dot'] = 0
        df_combined = pd.concat([df_promo, df_no_promo], ignore_index=True)
        df_combined = df_combined.applymap(lambda x: False if pd.isnull(x) or x == '' else x)
        df_combined.to_excel('/mnt/extra-addons/combined.xlsx', index=False)
        return df_combined  # Si necesitas devolver el DataFrame modificado
        
    # Definir la función _table_query
    def _table_query(self):
        query = '%s %s %s %s' % (self._select(), 
                                        #_get_active_pricelist(),
                                        self._from(),
                                        self._join(),
                                        self._group_by())
        print(query)  
        return query


    def _get_active_pricelist(self):
        query = ''
        PPIDS = [(1, 'mayoreo'), (113, 'promocion')]        
        for id, name in PPIDS:
            query += self._get_price_sql(id, name)
        # Eliminar la última coma si está presente en la cadena
        if ',' in query:
            query = query[:query.rfind(',')]
        return query
            
        
    def _select(self):
        return '''
    SELECT 
        pt.id AS product_id,
        pt.default_code,
        pt.tire_measure_id, 
        pt.layer_id, 
        pt.speed_id, 
        pt.index_of_load_id,
        pt.model_id, 
        pt.brand_id,
        pt.tier_id,
        lot.name AS lot_name, -- Obtener el nombre del lote desde stock_lot
        SUM(sq.available) AS available -- Mantener la suma total de disponible por lot_name
    '''
        
        
    def _get_price_sql(self,id,name):
        return '''(
        SELECT fixed_price
        FROM product_pricelist_item ppi
        WHERE ppi.product_tmpl_id = pp.product_tmpl_id
        AND ppi.pricelist_id = %s 
        LIMIT 1
    ) AS %s,
        '''%(id,name)
 
    def _from(self):
        return '''FROM product_product pp'''

        
    def _join(self):
        return '''
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                LEFT JOIN (
                    SELECT 
                        sq.product_id, 
                        sq.lot_id, -- Incluir lot_id
                        SUM(sq.quantity - sq.reserved_quantity) AS available
                    FROM 
                        stock_quant sq
                    JOIN 
                        stock_location sl ON sq.location_id = sl.id
                    WHERE 
                        sl.usage = 'internal'
                    GROUP BY 
                        sq.product_id, sq.lot_id -- Agrupar por lot_id para las cantidades por lote
                ) sq ON sq.product_id = pp.id
                LEFT JOIN stock_lot lot ON sq.lot_id = lot.id -- Realizar el JOIN con stock_lot para obtener el nombre del lote'''

        
    def _group_by(self):
        return '''
            GROUP BY 
                pp.id,
                pt.id, 
                pt.default_code,
                pt.tire_measure_id,
                pt.layer_id,
                pt.speed_id,
                pt.index_of_load_id,
                pt.model_id,
                pt.brand_id,
                pt.tier_id,
                lot.name -- Agrupar por lot_name
            HAVING 
                SUM(sq.available) > 0 -- Solo mostrar productos con cantidad disponible positiva
            ORDER BY 
                pt.tire_measure_id ASC;'''