from odoo import api, fields, models
from dateutil.relativedelta import relativedelta
import pandas as pd
from datetime import date
from odoo.addons.inv_promo.wizard.models.lista_de_precios import codes2

class VentasPorMarca(models.TransientModel):
    _name = 'ventas_por_marca'

    def get_report(self):
        fecha_actual = date.today()
        # Obtén el primer día del mes actual
        primer_dia_mes = fecha_actual.replace(day=1)
        ultimo_dia_mes = primer_dia_mes.replace(day=28)  # Establece inicialmente el día 28
        ultimo_dia_mes = ultimo_dia_mes + pd.offsets.MonthEnd(0)  # Ajusta al último día del mes

        query = """
            SELECT rp."name" AS Vendedor, 
                zpb."name" AS Marca, 
                SUM(CASE
                WHEN am.move_type IN ('out_refund') THEN -aml.quantity
                ELSE aml.quantity
                END) AS Cantidad
            FROM account_move_line aml 
            LEFT JOIN account_move am ON aml.move_id = am.id 
            LEFT JOIN product_product pp ON aml.product_id = pp.id
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id 
            LEFT JOIN res_users ru ON am.invoice_user_id = ru.id
            LEFT JOIN res_partner rp ON ru.partner_id = rp.id
            LEFT JOIN ztyres_products_brand zpb ON pt.brand_id = zpb.id
            WHERE am.invoice_date BETWEEN %s AND %s
            AND am.state IN ('posted')
            AND am.move_type IN ('out_invoice', 'out_refund')
            AND pt.detailed_type IN ('product')
            AND aml.display_type IN ('product')
            AND ru.id NOT IN (31, 78, 54, 89)
            GROUP BY rp."name", zpb."name"
            ORDER BY rp."name", zpb."name"
            """
        ##Retornar la consulta sql
        self.env.cr.execute(query, (primer_dia_mes, ultimo_dia_mes))
        result = self.env.cr.dictfetchall() 
        df = pd.DataFrame(result)

        pivot_df = df.pivot_table(index='marca', columns='vendedor', values='cantidad', aggfunc='sum', fill_value=0)
        pivot_df.reset_index(inplace=True)
        
        query2 = """
            SELECT rp."name" AS vendedor, 
                zpt."name" AS tier, 
                SUM(CASE
                WHEN am.move_type IN ('out_refund') THEN -aml.quantity
                ELSE aml.quantity
                END) AS Cantidad
            FROM account_move_line aml 
            LEFT JOIN account_move am ON aml.move_id = am.id 
            LEFT JOIN product_product pp ON aml.product_id = pp.id
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id 
            LEFT JOIN res_users ru ON am.invoice_user_id = ru.id
            LEFT JOIN res_partner rp ON ru.partner_id = rp.id
            LEFT JOIN ztyres_products_tier zpt ON pt.tier_id = zpt.id
            WHERE am.invoice_date BETWEEN %s AND %s
            AND am.state IN ('posted')
            AND am.move_type IN ('out_invoice', 'out_refund')
            AND pt.detailed_type IN ('product')
            AND aml.display_type IN ('product')
            AND ru.id NOT IN (31, 78, 54, 89)
            GROUP BY rp."name", zpt."name"
            ORDER BY rp."name", zpt."name"
            """
        ##Retornar la consulta sql
        self.env.cr.execute(query2, (primer_dia_mes, ultimo_dia_mes))
        result2 = self.env.cr.dictfetchall() 
        df2 = pd.DataFrame(result2)
        
        pivot_df2 = df2.pivot_table(index='tier', columns='vendedor', values='cantidad', aggfunc='sum', fill_value=0)
        pivot_df2.reset_index(inplace=True)
        
        codes_tuple = tuple(codes2)
        
        query3 = """
            select
            	aml."name" AS producto,
            	rp."name" AS vendedor, 
                SUM(CASE
                WHEN am.move_type IN ('out_refund') THEN -aml.quantity
                ELSE aml.quantity
                END) AS Cantidad
            FROM account_move_line aml 
            LEFT JOIN account_move am ON aml.move_id = am.id 
            LEFT JOIN product_product pp ON aml.product_id = pp.id
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id 
            LEFT JOIN res_users ru ON am.invoice_user_id = ru.id
            LEFT JOIN res_partner rp ON ru.partner_id = rp.id
            WHERE am.invoice_date BETWEEN %s AND %s
            AND am.state IN ('posted')
            AND am.move_type IN ('out_invoice', 'out_refund')
            AND pt.detailed_type IN ('product')
            AND aml.display_type IN ('product')
            AND ru.id NOT IN (31, 78, 54, 89)
            AND pt.id IN %s
            GROUP BY rp."name", aml."name"
            ORDER BY rp."name"
            """
        ##Retornar la consulta sql
        self.env.cr.execute(query3, (primer_dia_mes, ultimo_dia_mes, codes_tuple))
        result3 = self.env.cr.dictfetchall() 
        df3 = pd.DataFrame(result3)
        
        pivot_df3 = df3.pivot_table(index='producto', columns='vendedor', values='cantidad', aggfunc='sum', fill_value=0)
        pivot_df3.reset_index(inplace=True)
        
        ##Instanciar la clase ztyres_ms_sql_excel_core que tiene el metodo para insertar un dataframe en sql server
        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(pivot_df, 'ventas_por_marca')
        reports_core.action_insert_dataframe(pivot_df3, 'ventas_promo23')
        return