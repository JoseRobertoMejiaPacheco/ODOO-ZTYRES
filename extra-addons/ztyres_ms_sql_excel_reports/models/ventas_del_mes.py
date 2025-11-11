import pandas as pd
import io
from odoo.http import request, Response
from odoo import api, fields, models
import openpyxl
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import range_boundaries
from openpyxl.formatting.rule import DataBarRule
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment
from openpyxl.styles import Border, Side
from itertools import cycle
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import calendar
import pandas as pd


class VentasDelMes(models.TransientModel):
    _name = 'ventas_del_mes'

    def get_report(self):
        
        fecha_actual = date.today()
        # Obtén el primer día del mes actual
        primer_dia_mes = fecha_actual.replace(day=1)
        ultimo_dia_mes = primer_dia_mes.replace(day=28)  # Establece inicialmente el día 28
        ultimo_dia_mes = ultimo_dia_mes + pd.offsets.MonthEnd(0)  # Ajusta al último día del mes
        
        #primer_dia_mes = '2025-11-01'
        #ultimo_dia_mes = '2025-11-30'
        
        thick_border = Border(
                            left=Side(style='thick'),
                            right=Side(style='thick'),
                            top=Side(style='thick'),
                            bottom=Side(style='thick')
                        )
        
        thin_border = Border(
                            left=Side(style='thin'),
                            right=Side(style='thin'),
                            top=Side(style='thin'),
                            bottom=Side(style='thin')
                        )
        
        desired_fields = [
            'name',
            'user_id',
            'volume_profile',
            'state_id',
        ]
        search_domain = [
            ('type', 'in', ['contact']),  # Filtrar por contactos
            ('partner_share', 'in', True), # Solo aquellos que compartan como socio
            ('active', 'in', True),
            ('category_id', 'not in', [11, 2, 13])
        ]
        records = self.env['res.partner'].search_read(search_domain, fields=desired_fields)
        result3 = [{key: value[1] if isinstance(value, tuple) else value for key, value in record.items()} for record in records]
        df30 = pd.DataFrame(result3)
        
        id_vendedor = 0
        metas_vendedor = [(135, 1463), (16, 12540), (46, 1463), (133, 3300), (39, 1000)]
        meta = next((meta for vid, meta in metas_vendedor if vid == id_vendedor), None)
        
        # 1. Crear un nuevo archivo Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "RESULTADOS POR MARCAS"
        
        query = """
                SELECT rp."name" AS vendedor, 
                    zpt."name" AS tier,
                    zpb."name" AS marca, 
                    SUM(CASE
                    WHEN am.move_type IN ('out_refund') THEN -aml.quantity
                    ELSE aml.quantity
                    END) AS cantidad
                FROM account_move_line aml 
                LEFT JOIN account_move am ON aml.move_id = am.id 
                LEFT JOIN product_product pp ON aml.product_id = pp.id
                LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id 
                LEFT JOIN res_users ru ON am.invoice_user_id = ru.id
                LEFT JOIN res_partner rp ON ru.partner_id = rp.id
                LEFT JOIN ztyres_products_brand zpb ON pt.brand_id = zpb.id
                LEFT JOIN ztyres_products_tier zpt ON pt.tier_id = zpt.id
                WHERE am.invoice_date BETWEEN %s AND %s
                AND am.state IN ('posted')
                AND am.move_type IN ('out_invoice', 'out_refund')
                AND pt.detailed_type IN ('product')
                AND aml.display_type IN ('product')
                AND ru.id IN (16, 46, 133, 135, 39)
                GROUP BY rp."name", zpb."name", zpt."name"
                ORDER BY rp."name", zpb."name",zpt."name"
                """
            ##Retornar la consulta sql
        self.env.cr.execute(query, (primer_dia_mes, ultimo_dia_mes))
        result = self.env.cr.dictfetchall() 
        df = pd.DataFrame(result)
        
        pivoted_df = df.pivot_table(index=['marca'], 
                                    columns=['vendedor'],
                                    values='cantidad',
                                    aggfunc='sum',
                                    fill_value=0)
        pivoted_df = pivoted_df.reset_index()
        
        pivoted_df['TOTAL DE VENTAS '] = pivoted_df[pivoted_df.select_dtypes(include='number').columns].sum(axis=1)
        
        # 3. Insertar el DataFrame (empezando desde fila 5)
        for r_idx, row in enumerate(dataframe_to_rows(pivoted_df, index=False, header=True), 5):
            for c_idx, value in enumerate(row, 1):
                ws.cell(row=r_idx, column=c_idx, value=value)
                
        ref_range = f"A5:{ws.cell(row=ws.max_row, column=ws.max_column).column_letter}{ws.max_row}"
        tab = Table(displayName="TablaVentas", ref=ref_range)
        style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=True)
        tab.tableStyleInfo = style
        ws.add_table(tab)
        
        # Obtener número de filas de la tabla usando el rango
        min_col, min_row, max_col, max_row = range_boundaries(tab.ref)
        num_rows = max_row
        
        # Escribir datos básicos del vendedor (ejemplo)
        ws.merge_cells("A1:C2")
        ws["A1"] = "Acumulado Ventas"
        ws["A1"].alignment = Alignment(horizontal='center', vertical='center')
        ws["A1"].font = Font(bold=True, size=26)
        ws["A1"].fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
        
        ws["A3"] = "META DE VENTAS:"
        ws["A4"] = "VENTAS ACTUALES:"
        
        for row in ws["A3:A4"]:
            for cell in row:
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color="3F3F3F", end_color="3F3F3F", fill_type="solid")
        
        valor = df['cantidad'].sum()
        
        ws["B3"] = meta
        ws["B4"] = valor
        
        ws["C3"] = 100
        ws["C4"] = f"=TRUNC((B4*C3)/B3, 2)"
        
        ws["A27"] = "TOTAL POR ASESOR"
        ws["A28"] = "OBJETIVO DE VENTAS"
        ws["A29"] = "PORCENTAJE"
        
        ws["B28"] = metas_vendedor[0][1]
        ws["C28"] = metas_vendedor[1][1]
        ws["D28"] = metas_vendedor[2][1]
        ws["E28"] = metas_vendedor[3][1]
        ws["F28"] = metas_vendedor[4][1]
        ws["G28"] = f"=SUM(B28:F28)"
        
        rule = DataBarRule(start_type="num", start_value=0,
                   end_type="num", end_value=100,
                   color="0000FF00", showValue=True)

        for col in range(2, 8):
            col_letter = get_column_letter(col)
            ws[f"{col_letter}29"] = f"=TRUNC(({col_letter}27 * 100) / {col_letter}28, 2)"
            ws.conditional_formatting.add(f"{col_letter}29", rule)
            ws[f"{col_letter}27"] = f"=SUM({col_letter}6:{col_letter}{max_row})"
        
        #----------------------------------- HOJA NUMERO 2 -------------------------------------------------
        
        ws2 = wb.create_sheet(title="AVANCES POR CLINETE")
                
        ws2.merge_cells("A1:C2")
        ws2["A1"] = "Acumulado Ventas"
        ws2["A1"].alignment = Alignment(horizontal='center', vertical='center')
        ws2["A1"].font = Font(bold=True, size=26)
        ws2["A1"].fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
        
        ws2["A3"] = "META DE VENTAS:"
        ws2["A4"] = "VENTAS ACTUALES:"
        
        for row in ws2["A3:A4"]:
            for cell in row:
                cell.alignment = Alignment(horizontal='center', vertical='center')
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color="3F3F3F", end_color="3F3F3F", fill_type="solid")
        
        valor = df['cantidad'].sum()
        
        ws2["B3"] = meta
        ws2["B4"] = valor
        
        ws2["C3"] = 100
        ws2["C4"] = f"=TRUNC((B4*C3)/B3, 2)"
        
        df30 = df30.rename(columns={
            'name': 'cliente',
            'user_id': 'vendedor',
            'volume_profile': 'perfil',
            'state_id': 'zona'
        })
        
        df30['perfil'] = df30['perfil'].fillna('Sin Perfil')
        
        df30.loc[(df30['perfil'] == 'AAA'), 'meta'] = 1000
        df30.loc[(df30['perfil'] == 'AA'), 'meta'] = 600
        df30.loc[(df30['perfil'] == 'A'), 'meta'] = 300
        df30.loc[(df30['perfil'] == 'B'), 'meta'] = 100
        df30.loc[(df30['perfil'] == 'C'), 'meta'] = 30
        df30.loc[(df30['perfil'] == 'D'), 'meta'] = 0
        df30.loc[(df30['perfil'] == 'Sin Perfil'), 'meta'] = ''
        
        query10 = """
            SELECT DISTINCT ON (so."name")
                rp2."name" AS cliente,
                rp."name" AS vendedor,
                CASE 
			    WHEN so.state in ('sale') THEN 'Orden de venta'
			    ELSE 'Cotizaciones'
			    END as state,
                DATE(so.date_order) AS date_order,
                SUM(sol.product_uom_qty) AS "cantidad de llantas"
            FROM sale_order so
            LEFT JOIN sale_order_line sol ON so.id = sol.order_id  
            LEFT JOIN res_partner rp2 ON sol.order_partner_id = rp2.id 
            LEFT JOIN product_product pp ON sol.product_id = pp.id 
            LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id 
            LEFT JOIN res_users ru ON so.user_id = ru.id
            LEFT JOIN res_partner rp ON ru.partner_id = rp.id
            WHERE pt.detailed_type = 'product'
            AND so.date_order BETWEEN %s AND %s
            AND sol.qty_invoiced = 0
            AND so.state not IN ('cancel')
            AND so.user_id not IN (31, 25)
            GROUP BY rp2."name", so."name", so.date_order, so.state, rp."name"
        """
        ##Retornar la consulta sql
        self.env.cr.execute(query10, (primer_dia_mes, ultimo_dia_mes))
        result10 = self.env.cr.dictfetchall()        #Crear dataframe dla consulta
        df10 = pd.DataFrame(result10)
        #---------------------------------------------------------------------------------------------------------------
        # Campos deseados
        desired_fields20 = [
            'partner_id',
            'move_id',
            'move_type',
            'quantity',
            'invoice_date'
        ]

        # Dominio de búsqueda
        search_domain20 = [
            ('display_type', 'in', ['product']),
            ('product_type', 'in', ['product']),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('parent_state', 'in', ['posted']),
            ('move_id.invoice_date', '>=', primer_dia_mes),
            ('move_id.invoice_date', '<=', ultimo_dia_mes),
            ('move_id.partner_id.active', 'in', [True, False])
        ]

        # Buscar registros
        records20 = self.env['account.move.line'].search_read(search_domain20, fields=desired_fields20)

        # Agregar el vendedor basado en el perfil del cliente (partner)
        for record in records20:
            move_id = record.get('move_id')
            if move_id and isinstance(move_id, (list, tuple)):
                move = self.env['account.move'].browse(move_id[0])
                record['vendedor'] = move.partner_id.user_id.name if move.partner_id.user_id else None

        # Limpiar tuplas (por ejemplo: ('id', 'nombre')) en los valores
        result20 = [
            {key: value[1] if isinstance(value, tuple) else value for key, value in record.items()}
            for record in records20
        ]

        # Crear DataFrame
        df20 = pd.DataFrame(result20)

        # Convertir cantidades negativas para notas de crédito
        df20.loc[df20['move_type'] == 'out_refund', 'quantity'] *= -1

        # Renombrar columnas
        df20 = df20.rename(columns={
            'partner_id': 'cliente',
            'quantity': 'cantidad de llantas',
            'invoice_date': 'date_order',
            'move_type': 'state'
        })

        df20['state'] = 'Timbrado'
        
        #---------------------------------------------------------------------------------------------------------------
        df_concatenado = pd.concat([df20, df10], ignore_index=True)
        #---------------------------------------------------------------------------------------------------------------        
        df_concatenado['date_order'] = pd.to_datetime(df_concatenado['date_order'], errors='coerce')  # Convierte a datetime, trata errores
        df_concatenado['semana_del_año'] = df_concatenado['date_order'].dt.isocalendar().week  # Extrae la semana del año
        # Agregar "SEMANA" al inicio del número de semana
        df_concatenado['semana_del_año_str'] = "SEMANA " + df_concatenado['semana_del_año'].astype(str)  # Convertir a cadena y concatenar

        # Crear columnas separadas para día, mes y año
        df_concatenado['día'] = df_concatenado['date_order'].dt.day
        
        df_concatenado = df_concatenado.groupby(['cliente', 'vendedor', 'date_order', 'state', 'día', 'semana_del_año_str'])['cantidad de llantas'].sum().reset_index()  
     
        merged_df = pd.merge(df30, df_concatenado, on=['cliente', 'vendedor'], how='outer')
        merged_df['state'] = merged_df['state'].fillna('Sin Pedido')
        merged_df['cantidad de llantas'] = merged_df['cantidad de llantas'].fillna(0) 
        
        new_order = ['id', 'cliente', 'perfil', 'vendedor', 'meta', 'zona', 'date_order', 'state', 'día', 'semana_del_año_str', 'cantidad de llantas']
        merged_df = merged_df[new_order]
        pivot_df4 = merged_df.pivot_table(index=['cliente', 'perfil', 'vendedor', 'meta', 'zona'], columns='state', values='cantidad de llantas', aggfunc='sum', fill_value=0)
        pivot_df4.reset_index(inplace=True)
        
        if 'Sin Pedido' in pivot_df4.columns:
            pivot_df4 = pivot_df4.drop(columns=['Sin Pedido'])
            
        if 'Orden de venta' in pivot_df4.columns:
            pivot_df4['Orden de venta'] = pivot_df4['Orden de venta'].replace(0, '')
        else:
            pivot_df4['Orden de venta'] = ''
            
        if 'Timbrado' in pivot_df4.columns:
            pivot_df4['Timbrado'] = pivot_df4['Timbrado'].replace(0, '')
        else:
            pivot_df4['Timbrado'] = ''
            
        if 'Cotizaciones' in pivot_df4.columns:
            pivot_df4 = pivot_df4.drop(columns=['Cotizaciones'])
            
        nuevo_orden_columnas = ['cliente', 'perfil', 'vendedor', 'meta', 'zona', 'Orden de venta', 'Timbrado']

        pivot_df4 = pivot_df4[nuevo_orden_columnas]
            
        pivot_df4["meta"] = pd.to_numeric(pivot_df4["meta"], errors="coerce")
        pivot_df4["Timbrado"] = pd.to_numeric(pivot_df4["Timbrado"], errors="coerce")
        
        #------------------------- COLUMNAS 2 MESES ANTERIORES ------------------------------------------
        primer_dia_hace_2_meses = (fecha_actual.replace(day=1) - relativedelta(months=2))
        ultimo_dia_mes_anterior = (fecha_actual.replace(day=1) - relativedelta(days=1))
        
        meses_mapping = {
            "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
            "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
            "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
        }

        query20 = """
        SELECT 
            rp."name" AS cliente,
            am.invoice_date AS fecha,
            SUM(
                CASE 
                    WHEN am.move_type = 'out_invoice' THEN aml.quantity
                    ELSE aml.quantity * -1
                END
            ) AS cantidad
        FROM account_move_line aml
        JOIN account_move am ON aml.move_id = am.id
        JOIN res_partner rp ON am.partner_id = rp.id
        JOIN product_product pp ON aml.product_id =pp.id 
        JOIN product_template pt ON pp.product_tmpl_id = pt.id
        WHERE am.invoice_date BETWEEN %s AND %s
        AND am.state = 'posted'
        AND am.move_type IN ('out_invoice', 'out_refund')
        AND aml.display_type IN ('product')
        AND pt.detailed_type IN ('product')
        GROUP BY rp."name", am.invoice_date
        """
        ##Retornar la consulta sql
        self.env.cr.execute(query20, (primer_dia_hace_2_meses, ultimo_dia_mes_anterior))
        result20 = self.env.cr.dictfetchall()        #Crear dataframe dla consulta
        df20 = pd.DataFrame(result20)

        df20['fecha'] = pd.to_datetime(df20['fecha'])

        df20['mes'] = (
            df20['fecha'].dt.month_name().replace(meses_mapping) + " " +
            df20['fecha'].dt.year.astype(str)
        )

        pivot_df20 = df20.pivot_table(index=['cliente'], 
                                    columns='mes', 
                                    values='cantidad', 
                                    aggfunc='sum', 
                                    fill_value=0)
        #-----------------------------------------------------------------------------------------------------------
        merged_df = pd.merge(pivot_df4, pivot_df20, on=['cliente'], how='left')
        
        # Paso 1: Definir la posición donde quieres insertar las columnas de mes
        pos_base = merged_df.columns.get_loc('zona') + 1  # después de 'zona'

        # Paso 2: Identificar columnas de mes (por ejemplo, contienen nombres de meses)
        meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

        columnas_mes = [c for c in merged_df.columns if any(m in c for m in meses)]

        # Paso 3: Crear la nueva lista de columnas
        cols = [c for c in merged_df.columns if c not in columnas_mes]  # columnas restantes
        cols[pos_base:pos_base] = columnas_mes  # insertar columnas de mes en la posición deseada

        # Paso 4: Reordenar el DataFrame
        merged_df = merged_df[cols]
        
                # 3. Insertar el DataFrame (empezando desde fila 5)
        for r_idx, row in enumerate(dataframe_to_rows(merged_df, index=False, header=True), 5):
            for c_idx, value in enumerate(row, 1):
                ws2.cell(row=r_idx, column=c_idx, value=value)
                
        ref_range = f"A5:{ws2.cell(row=ws2.max_row, column=ws2.max_column).column_letter}{ws2.max_row}"
        tab = Table(displayName="TablaClientes", ref=ref_range)
        style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False, showLastColumn=False, showRowStripes=True, showColumnStripes=True)
        tab.tableStyleInfo = style
        ws2.add_table(tab)
        
        start_row = 5          # encabezados
        data_start_row = 6     # inicio de los datos

        # Lista de columnas a agregar
        # clave = nombre de la columna, valor = fórmula (en formato string con {row})
        new_cols = {
            "Faltan": "=D{row} - I{row}",
            "Progreso": "=TRUNC((I{row} / D{row}) * 100, 2)"
        }

        for i, (col_name, formula) in enumerate(new_cols.items(), start=1):
            new_col = ws2.max_column + 1  # siempre agrega en la última
            ws2.cell(row=start_row, column=new_col, value=col_name)  # encabezado
            
            # Rellenar fórmulas en las filas de datos
            for row in range(data_start_row, ws2.max_row + 1):
                ws2.cell(row=row, column=new_col, value=formula.format(row=row))

        # --- Expandir la tabla para incluir nuevas columnas ---
        last_col = get_column_letter(ws2.max_column)
        ref_range = f"A5:{last_col}{ws2.max_row}"
        tab.ref = ref_range   # expandimos tabla existente

        # --- Agregar DataBar en la columna "% Avance" ---
        max_row = ws2.max_row
        avance_col = get_column_letter(ws2.max_column)  # última columna es "% Avance"

        ws2.conditional_formatting.add(f"{avance_col}6:{avance_col}{max_row}", rule)
        
        #----------------------------------- HOJA NUMERO 3 -------------------------------------------------
        ws3 = wb.create_sheet(title="RESULTADOS DE PROMOCIONES")
        
        ws3.merge_cells("B2:E3")
        ws3["B2"] = "VENTAS POR TIER"
        ws3["B2"].alignment = Alignment(horizontal='center', vertical='center')
        ws3["B2"].font = Font(bold=True)
        ws3["B2"].fill = PatternFill(start_color="D0CECE", end_color="D0CECE", fill_type="solid")
        for row in ws3["B2:E3"]:
            for cell in row:
                cell.border = thick_border
        
        ws3.merge_cells("G2:L3")
        ws3["G2"] = "CHALLENGE Y SEGMENTO TIER 1 Y 3"
        ws3["G2"].alignment = Alignment(horizontal='center', vertical='center')
        ws3["G2"].font = Font(bold=True)
        ws3["G2"].fill = PatternFill(start_color="D0CECE", end_color="D0CECE", fill_type="solid")
        for row in ws3["G2:L3"]:
            for cell in row:
                cell.border = thick_border
        
        pivoted_df2 = df.pivot_table(index=['vendedor'], 
                                    columns=['tier'],
                                    values='cantidad',
                                    aggfunc='sum',
                                    fill_value=0)
        
        pivoted_df2 = pivoted_df2.reset_index()
        
        # Transformar pivoted_df2 para tener una fila por cada tier
        df_melted = pivoted_df2.melt(id_vars='vendedor', var_name='tier', value_name='cantidad')

        start_row = 5
        current_row = start_row
        colores_vendedores = ["203764", "FFC000", "7030A0", "BF8F00", "833C0C"]
        color_cycle = cycle(colores_vendedores)

        for vendedor, group in df_melted.groupby('vendedor'):
            fill_color = next(color_cycle)
            num_rows = len(group)
            # Combinar celdas verticalmente en la columna vendedor
            if num_rows > 1:
                ws3.merge_cells(
                    start_row=current_row,
                    start_column=1,
                    end_row=current_row + num_rows - 1,
                    end_column=1
                )
            ws3.cell(row=current_row, column=1, value=vendedor)
            ws3.cell(row=current_row, column=1).alignment = Alignment(vertical='center', horizontal='left')
            ws3.cell(row=current_row, column=1).font = Font(bold=True, color="FFFFFF")
            ws3.cell(row=current_row, column=1).fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
            
            for row in ws3.iter_rows(min_row=current_row, max_row=current_row + num_rows - 1, min_col=1, max_col=1):
                for cell in row:
                    cell.border = thick_border
            
            current_row += 2
            
            # Escribir tiers y cantidades
            for i, (_, row) in enumerate(group.iterrows()):
                ws3.cell(row=current_row - 2, column=i + 2, value=row['tier'])
                ws3.cell(row=current_row - 2 +1, column=i + 2, value=row['cantidad'])
                ws3.cell(row=current_row - 2 +2, column=i + 2, value="OBJETIVO")
                ws3.cell(row=current_row - 2 +3, column=i + 2, value="")
                
                for r in range(4):
                    cell = ws3.cell(row=current_row - 2 + r, column=i + 2)
                    cell.alignment = Alignment(horizontal='center')
                    cell.border = thin_border
                    # Solo tier y objetivo llevan fondo + fuente blanca
                    if r in [0, 2]:
                        cell.font = Font(bold=True, color="FFFFFF")
                        cell.fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
                    elif r == 1:  # cantidad
                        cell.font = Font(bold=False, color="000000")
            
            current_row += num_rows

        col_bloques = {
            ("G", "H"): ["SEGMENTO TIER 1 Y 3", "CHALLENGE", "", ""],
            ("I", "J"): ["VENDIDAS", "VENDIDAS", "=B{row}+D{row}", "TOTAL"],
            ("K", "L"): ["PORCENTAJE", "PORCENTAJE", "=TRUNC((I{row} * 100) / G{row}, 2)", "=TRUNC((I{row} * 100) / G{row}, 2)"],
        }

        filas_grupo1 = [5, 11, 17, 23, 29]
        filas_grupo2 = [7, 13, 19, 25, 31]
        filas_grupo3 = [6, 12, 18, 24, 30]
        filas_grupo4 = [8, 14, 20, 26, 32]

        for (col_start, col_end), titulos in col_bloques.items():
            for filas, texto in zip([filas_grupo1, filas_grupo2, filas_grupo3, filas_grupo4], titulos):
                for f in filas:
                    fill_color = next(color_cycle)
                    rango = f"{col_start}{f}:{col_end}{f}"
                    ws3.merge_cells(rango)
                    for row in ws3[rango]:
                        for cell in row:
                            cell.border = thin_border
                    min_col, min_row, _, _ = range_boundaries(rango)
                    
                    if f in filas_grupo1 + filas_grupo2:
                        ws3.cell(row=min_row, column=min_col).font = Font(bold=True, color="FFFFFF")
                        ws3.cell(row=min_row, column=min_col).fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")

                    # Calcular valor
                    if texto == "TOTAL" and col_start == "I":
                        vendedor_col = ws3[f"A{f-3}"].value
                        valor = pivoted_df.loc[pivoted_df['marca'].isin(['DRIVEFORCE', 'ONYX'])][vendedor_col].sum()
                    elif isinstance(texto, str) and "{row}" in texto:
                        valor = texto.format(row=f)
                        if col_start == "K":
                            ws3.conditional_formatting.add(f"{col_start}{f}", rule)
                            
                    else:
                        valor = texto

                    # Escribir en la celda superior izquierda del rango
                    ws3.cell(row=min_row, column=min_col, value=valor)
                    ws3.cell(row=min_row, column=min_col).alignment = Alignment(horizontal='center', vertical='center')
                    
        for sheet in [ws, ws2, ws3]:
            for col_idx, column in enumerate(sheet.columns, start=1):
                max_length = 0
                for cell in column:
                    try:
                        if cell.value and len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = max_length + 5
                col_letter = get_column_letter(col_idx)
                sheet.column_dimensions[col_letter].width = adjusted_width

        wb.move_sheet(ws2, offset=-wb.index(ws2))
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        # 4. Guardar archivo
        return output