from odoo import api, fields, models
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta

class MyModel(models.TransientModel):
    _name = 'ztyres_ms_sql_excel_reports_direccion'

    # Métodos útiles

    def convert_to_company_currency(self, currency_id, amount, date):
        currency_id = self.env['res.currency'].browse(currency_id)
        converted_amount = currency_id._convert(
            amount,
            currency_id.env.company.currency_id,
            currency_id.env.company,
            date
        )
        return converted_amount
    
    def execute_query(self, query, params):
        self.env.cr.execute(query, params)
        results = self.env.cr.dictfetchall()
        return results

    def dict_to_df(self, dict_data):
        return pd.DataFrame(dict_data)

    def add_month(self, dataframe, move_type, reverse_move_type, details):
        ids = dataframe['id'].tolist()
        dfs_to_merge = [pd.DataFrame(self.get_last_invoice_product_qty_by_period(item['month_name'], ids, item['start_date'], item['end_date'])) for item in details]
        for df in dfs_to_merge:
            try:
                if not df.empty:
                    dataframe = dataframe.merge(df, on='id', how='left')
            except:
                print('Hola')
        return dataframe

    # Métodos para obtener datos

    def get_transit_qty(self, product_tmpl_ids):
        query = """
        SELECT  
            pp.product_tmpl_id as id,
            SUM(sq.quantity) AS transito 
        FROM stock_quant sq
        JOIN product_product AS pp ON sq.product_id = pp.id
        WHERE location_id in (53, 24686, 24687) AND
        pp.product_tmpl_id IN %s 
        GROUP BY pp.product_tmpl_id
        """
        params = (tuple(product_tmpl_ids),)
        return self.execute_query(query, params)

    def get_purchase_backorder_qty(self, product_tmpl_ids):
        query = """
        SELECT 
            pp.product_tmpl_id as id,
            SUM(pol.product_qty - pol.qty_received) as purchase_backorder 
        FROM 
            purchase_order_line pol
        JOIN 
            product_product AS pp ON pol.product_id = pp.id
        JOIN 
            purchase_order po ON pol.order_id = po.id
        WHERE 
            po.state IN ('purchase') AND
            po.invoice_status NOT IN ('cancel') AND
            (pol.product_qty - pol.qty_received) > 0 AND
            pp.product_tmpl_id IN %s 
        GROUP BY pp.product_tmpl_id;
        """
        params = (tuple(product_tmpl_ids),)
        return self.execute_query(query, params)

    def get_origin_name(self, product_tmpl_ids):
        query = """
        SELECT pt.id ,rc."name"->>'es_ES' as country_of_origin from product_template pt
        JOIN res_country rc on pt.country_id = rc.id 
        where active = true
        and pt.id IN %s
        """
        params = (tuple(product_tmpl_ids),)
        return self.execute_query(query, params)

    def get_upf(self, product_tmpl_ids):
        query = """
        WITH RankedRecords AS (
            SELECT
                pp.product_tmpl_id AS id,
                aml."date" AS fecha_upf,
                aml.price_unit AS upf,
                ROW_NUMBER() OVER (PARTITION BY pp.product_tmpl_id
                                ORDER BY aml.create_date DESC, aml.price_unit DESC) AS rn
            FROM account_move_line AS aml
            JOIN product_product AS pp ON aml.product_id = pp.id
            JOIN account_move AS am ON aml.move_id = am.id
            JOIN product_template AS pt ON pp.product_tmpl_id = pt.id
            WHERE am.state = 'posted' 
                AND aml.display_type = 'product'
                AND am.move_type = 'out_invoice'
                AND pt.active = true
                AND pt."type" = 'product'
                AND pp.product_tmpl_id IN %s
        )
        SELECT id, fecha_upf, upf
        FROM RankedRecords
        WHERE rn = 1;
        """
        params = (tuple(product_tmpl_ids),)
        return self.execute_query(query, params)

    def get_avg_x_studio_costo_final(self, product_tmpl_ids):
        desired_fields = [
            'id',
            'default_code',
            'qty_available',
            'standard_price'
        ]
        records = self.env['product.template'].search_read([('detailed_type', 'in', ['product'])], fields=desired_fields)
        # Extraer solo los valores de las tuplas
        result = [{key: value[1] if isinstance(value, tuple) else value for key, value in record.items()} for record in records]
        df = pd.DataFrame(result)
        df = df.loc [df['qty_available'] != 0]
        
        query = """
            SELECT 
        	    am.currency_id AS moneda_pedido, 
                pp.product_tmpl_id AS id,
                pt.default_code AS codigo,
                aml.quantity as cantidad,
                aml.costo_final AS costo_final_promedio,
                am."date" AS fecha_pedido_compra
                FROM account_move am 
                JOIN account_move_line aml ON am.id = aml.move_id
                JOIN product_product pp ON aml.product_id = pp.id 
                JOIN product_template pt ON pp.product_tmpl_id = pt.id 
                WHERE am.state in ('posted')
                AND am.move_type in ('in_invoice') 
                AND aml.display_type in ('product')
                AND aml.costo_final is not null 
                AND aml.costo_final != 0
                AND pp.product_tmpl_id IN %s
                ORDER BY am."date" DESC
        """
        params = (tuple(product_tmpl_ids),)
        result2 = self.execute_query(query, params)
        df2 = pd.DataFrame(result2)
        
        # Nuevo DataFrame para almacenar los registros
        nuevo_df = pd.DataFrame(columns=['moneda_pedido', 'id', 'codigo', 'cantidad', 'costo_final_promedio', 'fecha_pedido_compra'])
        
        # Iterar sobre los registros del segundo DataFrame
        for index, row in df2.iterrows():
            codigo = row['id']
            cantidad_restante = row['cantidad']
            # Buscar el código en el primer DataFrame
            if codigo in df['id'].values:
                # Restar la cantidad del primer DataFrame hasta que sea menor o igual a 0
                while cantidad_restante > 0:
                    # Obtener la cantidad disponible en el primer DataFrame
                    cantidad_disponible = df.loc[df['id'] == codigo, 'qty_available'].values[0]
                    # Si la cantidad disponible es mayor que 0
                    if cantidad_disponible > 0:
                        # Calcular la cantidad a restar
                        cantidad_a_restar = min(cantidad_restante, cantidad_disponible)
                        # Restar la cantidad del primer DataFrame
                        df.loc[df['id'] == codigo, 'qty_available'] -= cantidad_a_restar
                        # Guardar el registro en el nuevo DataFrame
                        # nuevo_df = nuevo_df.append({'moneda_pedido': row['moneda_pedido'] ,'id': codigo, 'cantidad': cantidad_a_restar, 'costo_final_promedio': row['costo_final_promedio'], 'fecha_pedido_compra': row['fecha_pedido_compra']}, ignore_index=True)
                        nuevo_df = pd.concat([nuevo_df, pd.DataFrame([{'moneda_pedido': row['moneda_pedido'], 'id': codigo, 'cantidad': cantidad_a_restar, 'costo_final_promedio': row['costo_final_promedio'], 'fecha_pedido_compra': row['fecha_pedido_compra']}])], ignore_index=True)

                        # Actualizar la cantidad restante
                        cantidad_restante -= cantidad_a_restar
                    # Si la cantidad disponible es igual a 0, salir del bucle
                    if cantidad_disponible == 0:
                        break
                    
        reports_core = self.env['ztyres_ms_sql_excel_core']
                    
        nuevo_df['monto_en_moneda_empresa'] = nuevo_df.apply(lambda row: self.convert_to_company_currency(row['moneda_pedido'], row['costo_final_promedio'], row['fecha_pedido_compra']), axis=1)
        # Calcular la suma ponderada del costo por ID
        nuevo_df['Costo Ponderado'] = nuevo_df['cantidad'] * nuevo_df['monto_en_moneda_empresa']
        
        reports_core.action_insert_dataframe(nuevo_df, 'pmp2')
        # Agrupar por ID y calcular la suma ponderada del costo y la suma de la cantidad
        grupo = nuevo_df.groupby('id').agg({'Costo Ponderado': 'sum', 'cantidad': 'sum'})
        # Calcular el costo promedio por ID
        grupo['costo_final_promedio'] = grupo['Costo Ponderado'] / grupo['cantidad']
        new_df = grupo.rename(columns={'monto_en_moneda_empresa': 'costo_final_promedio'})
        return new_df

    def get_ucfinal(self, product_tmpl_ids):
        query = """
            SELECT DISTINCT ON (pp.product_tmpl_id)
        	    am.currency_id AS moneda_pedido, 
                pp.product_tmpl_id AS id,
                aml.costo_final AS ultimo_costo_final,
                am."date" AS fecha_pedido_compra
            FROM account_move am 
            JOIN account_move_line aml ON am.id = aml.move_id
            JOIN product_product pp ON aml.product_id = pp.id 
            JOIN product_template pt ON pp.product_tmpl_id = pt.id 
            WHERE am.state in ('posted')
            AND am.move_type in ('in_invoice') 
            AND aml.display_type in ('product')
            AND aml.costo_final is not null 
            AND aml.costo_final != 0
            AND pp.product_tmpl_id  IN %s
            ORDER BY pp.product_tmpl_id, am."date" DESC
        """
        params = (tuple(product_tmpl_ids),)
        result = self.execute_query(query, params)
        
        df = self.dict_to_df(result)
        df['monto_en_moneda_empresa'] = df.apply(lambda row: self.convert_to_company_currency(row['moneda_pedido'], row['ultimo_costo_final'], row['fecha_pedido_compra']), axis=1)
        new_df = df.rename(columns={'monto_en_moneda_empresa': 'ultimo_costo_final_'})
        new_df = new_df[['id','ultimo_costo_final_']]
        return new_df

    def get_qty_reserved(self, product_tmpl_ids):
        query = """
        SELECT 
            pp.product_tmpl_id AS id,
            COALESCE(SUM(sq.reserved_quantity), 0) AS total_reserved_qty 
        FROM 
            stock_quant sq
        JOIN product_product pp ON sq.product_id = pp.id
        JOIN stock_location sl ON sq.location_id = sl.id
        WHERE 
            pp.product_tmpl_id IN %s
            AND sl.usage = 'internal'
        GROUP BY 
            pp.product_tmpl_id;
        """
        params = (tuple(product_tmpl_ids), )
        result = self.execute_query(query, params)
        return self.dict_to_df(result)

    def get_price_list(self, product_tmpl_ids, price_list_id, name):
        query = """
        SELECT 
            product_tmpl_id AS id, 
            MAX(fixed_price) AS "%s" 
        FROM 
            product_pricelist_item ppi  
        WHERE 
            applied_on = '1_product'
            AND pricelist_id = %s 
            AND product_tmpl_id IN %s
        GROUP BY
            product_tmpl_id;
        """
        params = (name, price_list_id, tuple(product_tmpl_ids))
        return self.execute_query(query, params)

    def get_last_invoice_product_price(self, product_tmpl_id, move_type):
        domain = [
            ('product_id.product_tmpl_id', '=', product_tmpl_id),
            ('move_id.state', 'in', ['posted']),
            ('display_type','=','product'),
            ('move_id.move_type', 'in', [move_type])
        ]
        return self.env['account.move.line'].search(domain)

    def get_last_invoice_product_cost(self, product_tmpl_id):
        return self.get_last_invoice_product_price(product_tmpl_id,'in_invoice').x_studio_costo_final


    def get_last_price_unit(self,product_tmpl_ids):
        query = """
        SELECT
            COALESCE(product_tmpl, 0) AS id,
            COALESCE(promedio_price_unit, 0) AS last_price_unit
            --moneda as monto_en_moneda_empresa,
            --fecha_pedido_compra 
        FROM (
        SELECT
            product_tmpl,
            promedio_price_unit,
            moneda,
            fecha_pedido_compra
        FROM (
        SELECT
            pp.product_tmpl_id AS product_tmpl,
            pol.price_unit AS promedio_price_unit,
            po.currency_id AS moneda,
            po.date_order AS fecha_pedido_compra,
            ROW_NUMBER() OVER (PARTITION BY pp.product_tmpl_id ORDER BY po.date_order DESC) AS row_num
        FROM purchase_order_line AS pol
        LEFT JOIN purchase_order AS po ON pol.order_id = po.id
        JOIN product_product AS pp ON pol.product_id = pp.id
        WHERE po.state not in ('cancel') AND pp.product_tmpl_id IN %s
        AND pol.product_qty != 0
        ) AS subquery
        WHERE row_num = 1
        ) AS subquery;
        """
        params = (tuple(product_tmpl_ids),)
        result = self.execute_query(query, params)
        df = self.dict_to_df(result)
        return df
        
    
    def get_last_invoice_product_qty_by_period(self, month_name, product_tmpl_ids, date_from, date_to):
        query  =  """
        SELECT
            pp.product_tmpl_id as id,
            SUM(CASE
                WHEN am.move_type = 'out_invoice' THEN aml.quantity * 1
                WHEN am.move_type = 'out_refund' THEN aml.quantity * -1
                ELSE aml.quantity  -- Puedes manejar otros casos si es necesario
            END) AS "%s"
        FROM
            account_move_line AS aml
        JOIN
            product_product AS pp ON aml.product_id = pp.id
        JOIN
            account_move AS am ON aml.move_id = am.id 
        WHERE
            pp.product_tmpl_id IN (select id from product_template where "type" = 'product' ) and
            am.state IN ('posted') AND
            aml.display_type = 'product' AND
            am.move_type IN ('out_invoice', 'out_refund') AND
            am.invoice_date >= %s AND
            am.invoice_date <= %s
        GROUP BY pp.id;
        """
        params = (month_name, date_from, date_to)
        return self.execute_query(query, params)

##############
    def get_avg_ucfact(self, product_tmpl_ids):
        query = """
            SELECT 
                pp.product_tmpl_id AS id,
                am."date" AS fecha_pedido_compra,
                aml.price_unit AS price_unit,
                am.currency_id AS monto_en_moneda_empresa
            FROM 
                account_move_line AS aml
            JOIN 
                product_product AS pp ON aml.product_id = pp.id
            JOIN 
                account_move AS am ON aml.move_id = am.id
            WHERE 
                am.state IN ('posted') AND
                pp.product_tmpl_id IN %s AND 
                aml.display_type = 'product' AND
                am.move_type = 'in_invoice'
        """
        params = (tuple(product_tmpl_ids),)
        result = self.execute_query(query, params)
        df = self.dict_to_df(result)
        df['costo_factura_promedio'] = df.apply(lambda row: self.convert_to_company_currency(row['monto_en_moneda_empresa'], row['price_unit'], row['fecha_pedido_compra']), axis=1)
        res = df[['id','costo_factura_promedio']]
        res = res.groupby('id')['costo_factura_promedio'].mean()
        return res

    def get_ucfact(self, product_tmpl_ids):
        query = """
        WITH RankedRecords AS (
            SELECT 
                pp.product_tmpl_id AS id,
                am."date" AS fecha_pedido_compra,
                aml.price_unit AS ultimo_costo_factura_moneda_original,
                am.currency_id AS monto_en_moneda_empresa,
                ROW_NUMBER() OVER(PARTITION BY pp.product_tmpl_id ORDER BY aml."date" DESC) AS rn
            FROM 
                account_move_line AS aml
            JOIN 
                product_product AS pp ON aml.product_id = pp.id
            JOIN 
                account_move AS am ON aml.move_id = am.id
            WHERE 
                am.state IN ('posted') AND
                pp.product_tmpl_id IN %s AND
                aml.display_type = 'product' AND
                am.move_type = 'in_invoice'
        )

        SELECT
            id, fecha_pedido_compra, ultimo_costo_factura_moneda_original as ultimo_costo_factura, monto_en_moneda_empresa
        FROM 
            RankedRecords
        WHERE 
            rn = 1;
        """
        params = (tuple(product_tmpl_ids),)
        result = self.execute_query(query, params)
        df = self.dict_to_df(result)
        df['monto_en_moneda_empresa'] = df.apply(lambda row: self.convert_to_company_currency(row['monto_en_moneda_empresa'], row['ultimo_costo_factura'], row['fecha_pedido_compra']), axis=1)
        res = df[['id','monto_en_moneda_empresa','fecha_pedido_compra']]
        res = res.rename(columns={'monto_en_moneda_empresa': 'ultimo_costo_factura','fecha_pedido_compra':'fecha_ultimo_costo_factura'})
        return res
    
    def get_qty_free(self,product_tmpl_id):
        domain = [('product_tmpl_id', 'in', [product_tmpl_id])]
        pp = self.env['product.product'].search(domain)
        free_qty = pp.free_qty
        return max(0, free_qty)

    def get_all_products(self):
        desired_fields = [
            'default_code',
            'cui',
            'name',
            'tire_measure_id',
            'face_id',
            'layer_id',
            'speed_id',
            'index_of_load_id',
            'model_id',
            'brand_id',
            'manufacturer_id',
            'segment_id',
            'type_id',
            'tier_id',
            'qty_available',
            'standard_price',
            'active'
        ]
        
        domain = [('detailed_type', 'in', ['product']), ('active', 'in', [True, False])]

        records = self.env['product.template'].search_read(domain, fields=desired_fields)
        # Extraer solo los valores de las tuplas
        #result = [{key: value[1] if isinstance(value, tuple) else value for key, value in record.items()} for record in records]
        
            # Extraer solo los valores de las tuplas y agregar 'free_qty'
        result = [{
            **{key: value[1] if isinstance(value, tuple) else value for key, value in record.items()},
            'free_qty': self.get_qty_free(record['id']),
            'qty_reserved': record['qty_available'] - self.get_qty_free(record['id'])
        } for record in records]
        return result


    def add_qty_reserved(self, dataframe):
        ids = dataframe['id'].tolist()
        dfs_to_merge = self.dict_to_df(self.get_qty_reserved(ids))
        return dataframe.merge(dfs_to_merge, on='id', how='left')

    def add_transit(self, dataframe):
        ids = dataframe['id'].tolist()
        dfs_to_merge = self.dict_to_df(self.get_transit_qty(ids))
        return dataframe.merge(dfs_to_merge, on='id', how='left')

    def add_price_list(self, dataframe, pricelist_id, name):
        ids = dataframe['id'].tolist()
        dfs_to_merge = self.dict_to_df(self.get_price_list(ids, pricelist_id, name))
        return dataframe.merge(dfs_to_merge, on='id', how='left')

    def add_ucfact(self, dataframe):
        ids = dataframe['id'].tolist()
        dfs_to_merge = self.get_ucfact(ids)
        return dataframe.merge(dfs_to_merge, on='id', how='left')
    
    def add_avg_ucfact(self, dataframe):
        ids = dataframe['id'].tolist()
        dfs_to_merge = self.get_avg_ucfact(ids)
        return dataframe.merge(dfs_to_merge, on='id', how='left')

    def add_ucfinal(self, dataframe):
        ids = dataframe['id'].tolist()
        dfs_to_merge = self.get_ucfinal(ids)
        return dataframe.merge(dfs_to_merge, on='id', how='left')
    
    def add_last_price_unit(self, dataframe):
        ids = dataframe['id'].tolist()
        dfs_to_merge = self.get_last_price_unit(ids)
        return dataframe.merge(dfs_to_merge, on='id', how='left') 
       
    def add_origin(self, dataframe):
        ids = dataframe['id'].tolist()
        dfs_to_merge = self.dict_to_df(self.get_origin_name(ids))
        return dataframe.merge(dfs_to_merge, on='id', how='left')

    def add_upf(self, dataframe):
        ids = dataframe['id'].tolist()
        dfs_to_merge = self.dict_to_df(self.get_upf(ids))
        return dataframe.merge(dfs_to_merge, on='id', how='left')

    def add_backorder(self, dataframe):
        ids = dataframe['id'].tolist()
        dfs_to_merge = self.dict_to_df(self.get_purchase_backorder_qty(ids))
        ids = dfs_to_merge['id'].tolist()
        return dataframe.merge(dfs_to_merge, on='id', how='left')

    def add_avg_x_studio_costo_final(self, dataframe):
        ids = dataframe['id'].tolist()
        dfs_to_merge = self.dict_to_df(self.get_avg_x_studio_costo_final(ids))
        return dataframe.merge(dfs_to_merge, on='id', how='left')

    def last_six_months_details(self):
        MONTHS_IN_SPANISH = {
            1: 'ENERO',
            2: 'FEBRERO',
            3: 'MARZO',
            4: 'ABRIL',
            5: 'MAYO',
            6: 'JUNIO',
            7: 'JULIO',
            8: 'AGOSTO',
            9: 'SEPTIEMBRE',
            10: 'OCTUBRE',
            11: 'NOVIEMBRE',
            12: 'DICIEMBRE'
        }
        today = datetime.date.today()
        months_details = []
        for _ in range(6):
            first_day_of_month = datetime.date(today.year, today.month, 1)
            last_day_of_month = (first_day_of_month.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
            month_name = MONTHS_IN_SPANISH[today.month]
            months_details.append({
                'month_name': month_name,
                'start_date': first_day_of_month,
                'end_date': last_day_of_month
            })
            today -= relativedelta(months=1)
        months_details.reverse()
        print(months_details)
        return months_details