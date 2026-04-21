from odoo import api, fields, models
import pandas as pd
import math
from datetime import datetime, date,timedelta
from dateutil.relativedelta import relativedelta
from openpyxl import Workbook
import io
from openpyxl.styles import Font, PatternFill
from pandas.api.types import CategoricalDtype

class PlanComercial(models.TransientModel):
    _name = 'reporte_plan_comercial'

    def get_report(self):
        
        meses_mapping = {
            "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
            "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
            "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
        }

        orden_meses = list(meses_mapping.values())

        primer_dia_mes_actual = '2026-01-01'
        ultimo_dia_intervalo = '2026-12-31'

        query = """
                select 
                am."ref" as factura,
                zpr."number" as rin,
                rp."name" as proveedor,
                zpm."name" as fabricante,
                sum(aml.quantity) as cantidad,
                sum(aml.price_subtotal) as subtotal,
                am."date" as fecha_contable,
                am.x_studio_fecha_a_pagar as fecha_vencimiento,
                am.move_type as tipo_movimiento
                from account_move_line aml
                join account_move am on aml.move_id = am.id
                join product_product pp on aml.product_id = pp.id
                join product_template pt on pp.product_tmpl_id = pt.id
                join ztyres_products_manufacturer zpm on pt.manufacturer_id = zpm.id
                join ztyres_products_tire_measure zptm on pt.tire_measure_id  = zptm.id
                join ztyres_products_rim zpr on zptm.rim_id = zpr.id
                join res_partner rp on am.partner_id = rp.id
                where am.move_type in ('in_refund', 'in_invoice')
                and am.state in ('posted')
                and pt.manufacturer_id in (2, 6, 9)
                and am."date" between %s and %s
                group by zpr."number", rp."name", zpm."name", am.partner_id, am."date", am."ref", am.x_studio_fecha_a_pagar, am.move_type
        """
        # Ejecutar la consulta y crear el DataFrame
        self.env.cr.execute(query, (primer_dia_mes_actual, ultimo_dia_intervalo))
        result = self.env.cr.dictfetchall()
        df2 = pd.DataFrame(result)

        df2['rin'] = df2['rin'].astype(int)

        df2['fecha'] = df2['fecha_contable']
        df2['fecha_contable'] = pd.to_datetime(df2['fecha_contable'])
        df2['fecha_contable'] = df2['fecha_contable'].dt.month_name().replace(meses_mapping)

        df2['fecha_contable'] = pd.Categorical(
            df2['fecha_contable'],
            categories=orden_meses,
            ordered=True
        )

        prefijos = {
            'cantidad': 'cant',
            'subtotal': 'sub'
        }
        
        reports_core = self.env['ztyres_ms_sql_excel_core']

        df = df2[(df2['fabricante'] == 'BRIDGESTONE')]
        reports_core.action_insert_dataframe(df, 'desgloce_bridgestone')
        df = df[df['tipo_movimiento'] == 'in_invoice']

        grupos = {
            'LRD 13,14,15,16': [13, 14, 15, 16],
            'HRD 17-18': [17, 18],
            'UHRD 19': [19, 20, 21, 22, 23, 24],
        }

        df['grupo_rin'] = 'Otros'

        for grupo, valores in grupos.items():
            df.loc[df['rin'].isin(valores), 'grupo_rin'] = grupo

        df.drop(columns=['rin', 'proveedor'], inplace=True)

        pivot_table = pd.pivot_table(df, values=['cantidad', 'subtotal'], index='grupo_rin', columns='fecha_contable', aggfunc='sum', fill_value=0)

        pivot_table = pivot_table.swaplevel(0, 1, axis=1)
        pivot_table = pivot_table.sort_index(axis=1, level=0)

        pivot_table.columns = [f"{prefijos[col[1]]}_{col[0]}" for col in pivot_table.columns.to_flat_index()]
        pivot_table = pivot_table.reset_index()

        orden_status = ["LRD 13,14,15,16", "HRD 17-18", "UHRD 19"]
        cat_type = CategoricalDtype(categories=orden_status, ordered=True)
        pivot_table['grupo_rin'] = pivot_table['grupo_rin'].astype(cat_type)
        pivot_table = pivot_table.sort_values('grupo_rin')

        df3 = df2[(df2['fabricante'] == 'GOODYEAR')]
        reports_core.action_insert_dataframe(df3, 'desgloce_goodyear')
        df3 = df3[df3['tipo_movimiento'] == 'in_invoice']

        grupos = {
            'Market A (Rin 16+)': [16, 17, 18, 19, 20, 21, 22, 23, 24],
            'Market B (Rin 13,14,15)': [13, 14, 15],
        }

        df3['grupo_rin'] = 'Otros'

        for grupo, valores in grupos.items():
            df3.loc[df3['rin'].isin(valores), 'grupo_rin'] = grupo

        df3.drop(columns=['rin', 'proveedor'], inplace=True)

        pivot_table2 = pd.pivot_table(df3, values=['cantidad', 'subtotal'], index='grupo_rin', columns='fecha_contable', aggfunc='sum', fill_value=0)

        pivot_table2 = pivot_table2.swaplevel(0, 1, axis=1)
        pivot_table2 = pivot_table2.sort_index(axis=1, level=0)

        # 🔥 APLANAR definitivamente
        pivot_table2.columns = [f"{prefijos[col[1]]}_{col[0]}" for col in pivot_table2.columns.to_flat_index()]
        pivot_table2 = pivot_table2.reset_index()

        orden_status = ["Market A (Rin 16+)", "Market B (Rin 13,14,15)"]
        cat_type = CategoricalDtype(categories=orden_status, ordered=True)
        pivot_table2['grupo_rin'] = pivot_table2['grupo_rin'].astype(cat_type)
        pivot_table2 = pivot_table2.sort_values('grupo_rin')

        df4 = df2[(df2['fabricante'] == 'PIRELLI')]
        reports_core.action_insert_dataframe(df4, 'desgloce_pirelli')
        df4 = df4[df4['tipo_movimiento'] == 'in_invoice']

        grupos = {
            'STANDARD': [13, 14, 15, 16],
            'PREMIUM (=17)': [17],
            'SP (=>18)': [18, 19, 20, 21, 22, 23, 24],
        }

        df4['grupo_rin'] = 'Otros'

        for grupo, valores in grupos.items():
            df4.loc[df4['rin'].isin(valores), 'grupo_rin'] = grupo

        df4.drop(columns=['rin', 'proveedor'], inplace=True)

        pivot_table3 = pd.pivot_table(df4, values=['cantidad', 'subtotal'], index='grupo_rin', columns='fecha_contable', aggfunc='sum', fill_value=0)

        pivot_table3 = pivot_table3.swaplevel(0, 1, axis=1)
        pivot_table3 = pivot_table3.sort_index(axis=1, level=0)

        # 🔥 APLANAR definitivamente
        pivot_table3.columns = [f"{prefijos[col[1]]}_{col[0]}" for col in pivot_table3.columns.to_flat_index()]
        pivot_table3 = pivot_table3.reset_index()

        orden_status = ["STANDARD", "PREMIUM (=17)", "SP (=>18)"]
        cat_type = CategoricalDtype(categories=orden_status, ordered=True)
        pivot_table3['grupo_rin'] = pivot_table3['grupo_rin'].astype(cat_type)
        pivot_table3 = pivot_table3.sort_values('grupo_rin')

        reports_core.action_insert_dataframe(pivot_table, 'compras_bridgestone')
        reports_core.action_insert_dataframe(pivot_table2, 'compras_goodyear')
        reports_core.action_insert_dataframe(pivot_table3, 'compras_pirelli')
        return