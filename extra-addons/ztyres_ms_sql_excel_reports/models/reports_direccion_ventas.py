from odoo import api, fields, models
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta

class MyModel(models.TransientModel):
    _name = 'reports_direccion_ventas'

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

    def add_month(self, dataframe, move_type, reverse_move_type, details, vendedor_id):
        ids = dataframe['id'].tolist()
        dfs_to_merge = []

        for item in details:
            month_name = item['month_name']

            df = pd.DataFrame(
                self.get_last_invoice_product_qty_by_period(
                    month_name,
                    ids,
                    item['start_date'],
                    item['end_date'],
                    vendedor_id=vendedor_id
                )
            )

            if df.empty:
                month_name_col = f"'{month_name}'"
                df = pd.DataFrame({
                    'id': ids,
                    month_name_col: 0
                })

            dfs_to_merge.append(df)

        for df in dfs_to_merge:
            dataframe = dataframe.merge(df, on='id', how='left')

        dataframe.fillna(0, inplace=True)

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
        
    def get_last_invoice_product_qty_by_period(self, month_name, product_tmpl_ids, date_from, date_to, vendedor_id):
        query = """
            SELECT 
                pp.product_tmpl_id AS id,
                SUM(
                    CASE 
                        WHEN am.move_type = 'out_invoice' THEN aml.quantity
                        WHEN am.move_type = 'out_refund' THEN -aml.quantity
                    END
                ) AS "%s"
            FROM account_move_line aml
            JOIN product_product pp ON aml.product_id = pp.id
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            JOIN account_move am ON aml.move_id = am.id
            WHERE pt.type = 'product'
            AND am.state = 'posted'
            AND aml.display_type = 'product'
            AND am.move_type IN ('out_invoice', 'out_refund')
            AND am.invoice_date BETWEEN %s AND %s
        """
        params = [month_name, date_from, date_to]
        
        if vendedor_id == 139:
            query += """AND am.invoice_user_id NOT IN (55, 31)"""
        else:
            query += """AND am.invoice_user_id = %s"""
            params.append(vendedor_id)
            
        query += """GROUP BY pp.product_tmpl_id"""
        
        return self.execute_query(query, params)

    
    def get_qty_free(self,product_tmpl_id):
        domain = [('product_tmpl_id', 'in', [product_tmpl_id])]
        pp = self.env['product.product'].search(domain)
        free_qty = pp.free_qty
        return max(0, free_qty)
    
    def get_qty_reserved(self,product_tmpl_id):
        MoveLine = self.env['stock.move.line']
        move_lines = MoveLine.search([
        ('reserved_uom_qty', '>', 0),
        ('move_id.sale_line_id', '!=', False),
        ('move_id.state', 'in', ['confirmed', 'assigned', 'partially_available']),
        ('product_id.product_tmpl_id', '=', product_tmpl_id),
            ])
        
        reserved_qty = sum(move_lines.mapped('reserved_uom_qty'))
        return max(0, reserved_qty)

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
            'product_nationality',
            'segment_id',
            'type_id',
            'tier_id',
            'product_dot_range',
            'qty_available',
            'standard_price',
            'active',
            'outgoing_qty'
        ]
        
        domain = [('detailed_type', 'in', ['product']), ('active', 'in', [True, False]), ('tire', '=', True)]

        records = self.env['product.template'].search_read(domain, fields=desired_fields)
        # Extraer solo los valores de las tuplas
        #result = [{key: value[1] if isinstance(value, tuple) else value for key, value in record.items()} for record in records]
        
            # Extraer solo los valores de las tuplas y agregar 'free_qty'
        result = [{
            **{key: value[1] if isinstance(value, tuple) else value for key, value in record.items()},
            #'free_qty': self.get_qty_free(record['id']),
            'free_qty': record['qty_available'] - self.get_qty_reserved(record['id']),
            'qty_reserved': self.get_qty_reserved(record['id']),
            'qty_reserved2': record['qty_available'] - self.get_qty_free(record['id'])
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
        return months_details