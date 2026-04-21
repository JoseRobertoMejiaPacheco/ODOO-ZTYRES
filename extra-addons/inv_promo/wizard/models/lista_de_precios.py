from odoo import _, api, fields, models
from odoo import models, fields, api
from openpyxl import Workbook
from openpyxl.drawing.image import Image
from odoo.exceptions import UserError,ValidationError
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter, column_index_from_string
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.drawing.image import Image
from openpyxl.comments import Comment
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Protection
from pytz import timezone
import openpyxl
import base64
import io
from datetime import date

codes_pirelli = [
#(51521, "3%"), (48712, "3%"), (28800, "2%"), (48713, "3%"), (61691, "2%"), (49637, "2%")
]

codes_goodyear = [
    
]

codes_kumho = [
#    (62397, "3%")
]

#(ID, PMS, APLICA_CUPON (5%), APLICA_BONO_TARJETA(4%, 5%, 6%))
codes_bridgestone_promo = [
    (22569, 1217.77, "NO", "SI"), (22075, 1390.76, "SI", "SI"), (22419, 1397.26, "SI", "SI"), (59744, 1463.8, "NO", "SI"), 
    (22079, 1159.99, "NO", "SI"), (22356, 1314.64, "SI", "SI"), (51533, 1636.1, "NO", "SI"), (22305, 1285, "NO", "SI"), 
    (22085, 1143.87, "NO", "SI"), (22086, 1405.43, "SI", "SI"), (22549, 1372.41, "NO", "SI"), (66200, 1418.9, "NO", "SI"), 
    (49042, 1418.9, "NO", "SI"), (22106, 1418.67, "SI", "SI"), (22589, 1557.48, "NO", "SI"), (22118, 1449.06, "SI", "SI"), 
    (22114, 1302.49, "NO", "SI"), (22518, 2082.02, "NO", "SI"), (63175, 3766.88, "NO", "SI"), (57249, 1569.69, "NO", "SI"), 
    (22133, 1394.7, "NO", "SI"), (22524, 1427.21, "NO", "SI"), (22717, 1468.24, "NO", "SI"), (51129, 1394.7, "NO", "SI"), 
    (48697, 1468.24, "NO", "SI"), (62897, 1255.23, "NO", "SI"), (22711, 1553.16, "NO", "SI"), (51715, 1596.79, "NO", "SI"), 
    (62898, 2995.03, "NO", "SI"), (22140, 1533.19, "NO", "SI"), (22683, 1584.92, "SI", "SI"), (51666, 1584.92, "NO", "SI"), 
    (63168, 1347.18, "NO", "SI"), (49072, 1776.63, "SI", "SI"), (22822, 2318.68, "NO", "SI"), (22804, 2447.43, "NO", "SI"), 
    (22605, 2257.06, "NO", "SI"), (22785, 2215.69, "NO", "SI"), (48877, 4234.03, "NO", "SI"), (22155, 1844.18, "NO", "SI"), 
    (66046, 1738.85, "NO", "SI"), (48878, 1781.48, "NO", "SI"), (22161, 1905.71, "NO", "SI"), (22628, 1777.85, "NO", "SI"), 
    (58933, 1784.6, "NO", "SI"), (22162, 1967.47, "NO", "SI"), (22823, 1739.18, "NO", "SI"), (22814, 1664.95, "NO", "SI"), 
    (49876, 1674.2, "NO", "SI"), (50301, 3321.05, "NO", "SI"), (22260, 2098.8, "NO", "SI"), (57693, 3722.66, "NO", "SI"), 
    (22547, 2009.51, "NO", "SI"), (59745, 4375.17, "NO", "SI"), (58485, 1593.32, "NO", "SI"), (61073, 2758.36, "NO", "SI"), 
    (48930, 3336.83, "NO", "SI"), (48951, 3985.49, "NO", "SI"), (62652, 2957.85, "NO", "SI"), (22637, 5176.36, "NO", "SI"), 
    (63176, 3131.41, "NO", "SI"), (61076, 3541.98, "NO", "SI"), (59252, 3804.33, "NO", "SI"), (48952, 3316.86, "NO", "SI"), 
    (62899, 3814.39, "NO", "SI"), (22604, 2351.85, "NO", "SI"), (22625, 1744.74, "NO", "SI"), (22422, 1860.2, "NO", "SI"), 
    (59253, 2143.13, "NO", "SI"), (59242, 2196.94, "NO", "SI"), (62900, 1697.8, "NO", "SI"), (22170, 1883.56, "NO", "SI"), 
    (62901, 1517.13, "NO", "SI"), (61074, 3165.59, "NO", "SI"), (59254, 4493.46, "NO", "SI"), (22633, 2286.37, "NO", "SI"), 
    (62903, 2640.76, "NO", "SI"), (62902, 1766.91, "NO", "SI"), (61075, 3323.87, "NO", "SI"), (22777, 2980.47, "NO", "SI"), 
    (48954, 1788.18, "NO", "SI"), (22817, 3350.79, "NO", "SI"), (22630, 2519.33, "NO", "SI"), (61086, 3076.4, "NO", "SI"), 
    (22288, 2790.38, "NO", "SI"), (62408, 3106.81, "NO", "SI"), (22284, 2756.76, "NO", "SI"), (58466, 1691.61, "NO", "SI"), 
    (22295, 2582.07, "SI", "SI"), (59867, 3105.05, "NO", "SI"), (22677, 3251.78, "NO", "SI"), (61088, 2970.08, "NO", "SI"), 
    (62653, 3412.9, "NO", "SI"), (61077, 3461.04, "NO", "SI"), (58828, 3488.91, "NO", "SI"), (61071, 5346.78, "NO", "SI"), 
    (60952, 3436.44, "NO", "SI"), (59271, 2850.04, "NO", "SI"), (59868, 2583.64, "SI", "SI"), (61087, 2618.03, "NO", "SI"), 
    (59869, 3587.71, "NO", "SI"), (62404, 4154.2, "NO", "SI"), (66236, 4097.85, "NO", "SI"), (57251, 3798.26, "NO", "SI"), 
    (62407, 4436.62, "NO", "SI"), (59256, 4397.32, "NO", "SI"), (59746, 3548.43, "NO", "SI"), (59257, 5282.04, "NO", "SI"), 
    (59747, 4154.84, "NO", "SI"), (59748, 3687.78, "NO", "SI"), (22516, 2320.62, "SI", "SI"), (22281, 2628.64, "NO", "SI"), 
    (62907, 3985.16, "NO", "SI"), (62406, 4366.88, "NO", "SI"), (22758, 5371.88, "NO", "SI"), (65016, 5907.72, "NO", "SI"), 
    (22826, 2971.52, "NO", "SI"), (59870, 3063.24, "NO", "SI"), (59258, 3419.96, "NO", "SI"), (62654, 3160.61, "NO", "SI"), 
    (62405, 3604.85, "NO", "SI"), (22778, 2999.98, "NO", "SI"), (66045, 3332.29, "NO", "SI"), (62409, 4494.49, "NO", "SI"), 
    (62908, 4085.25, "NO", "SI"), (62655, 2731.48, "NO", "SI"), (51857, 5782.62, "NO", "SI"), (22827, 2613.16, "NO", "SI"), 
    (61080, 3718.46, "NO", "SI"), (57226, 3234.69, "NO", "SI"), (61084, 3983.4, "NO", "SI"), (59871, 6732.55, "NO", "SI"), 
    (22752, 4268.42, "NO", "SI"), (61085, 4173.34, "NO", "SI"), (62410, 7018.3, "NO", "SI"), (62909, 2466, "NO", "SI"), 
    (61070, 2595.42, "NO", "SI"), (62905, 3333.33, "NO", "SI"), (59255, 3473.17, "NO", "SI"), (61081, 3318.41, "NO", "SI"), 
    (51856, 4178.08, "NO", "SI"), (22355, 2547.86, "NO", "SI"), (22726, 1379.03, "NO", "SI"), (22301, 2731.48, "NO", "SI")
    
]

WHITE = 'FFFFFF'
BLACK = '1A1818'
YELLOW = 'FFFF00'
YELLOW_2 = 'FFC000'
DARK_GREEN = '19B050'
LIGTH_GREEN = '92D050'
RED = 'FF0000'
LIGTH_GRAY = 'F2F2F2'
DARK_GRAY = '404040'
BLUE = '95B3D7'

class ListaDePrecios(models.TransientModel):
    _name = 'inv_promo.lista_precios_wizard'
    _description = 'Lista de Precios'
    
    partner_id = fields.Many2one('res.partner', string='Cliente')
    volume_profile= fields.Many2one('discount_profiles.volume.discount', string='Volumen')
    financial_profile = fields.Many2one('discount_profiles.financial.discount', string='Financiero')
    logistic_profile = fields.Many2one('discount_profiles.logistic.discount', string='Logístico')
    file_data = fields.Binary('File')

    def get_profile_data(self,partner_id=False):
        if partner_id:
            #FIXME update variable name financial = partner_id.get_row_values_volumen() to financial = partner_id.get_row_values_volumen()
            financial = partner_id.get_row_values_volumen()
            logistic = partner_id.get_row_values_logistico()
            vendedor = partner_id.user_id.name
        else:
            financial = self.partner_id.get_row_values_volumen(self.volume_profile)
            logistic = self.partner_id.get_row_values_logistico(self.logistic_profile)   
            vendedor = self.partner_id.user_id.name
        
        # Convertir valores numéricos a cadenas de porcentaje y agregar '0%'
        
        # Verificar si los elementos de financial son tuplas
        financial_percentages = ['0%'] + [
            f"{tupla[1]}%" if isinstance(tupla, (list, tuple)) and len(tupla) > 1 else f"{tupla}%" 
            for tupla in financial
        ]        
        logistic_percentages = ['0%'] + [f"{tupla[1]}%" for tupla in logistic]
        
        # Ordenar las listas de porcentajes
        financial_percentages.sort()
        logistic_percentages.sort()

        #return financial_percentages, logistic_percentages
        return vendedor
########################################################################## Efervecente #########################################################################################################################################################################################
    def _get_metadata(self,res_partner):
        data = ''
        tz = timezone('America/Mexico_City')  # Definir la zona horaria de México
        if res_partner:
            # Convertir la fecha de creación a la zona horaria de México
            created_date = fields.Datetime.to_string(fields.Datetime.context_timestamp(self, fields.Datetime.from_string(self.create_date or fields.Datetime.now())).astimezone(tz))
            data = f'Creado por: {self.env.user.name}, Fecha de creación: {created_date}, Cliente: {res_partner.name}, Volumen: {res_partner.volume_profile.name}, Crédito: {res_partner.financial_profile .name}, Logístico: {res_partner.logistic_profile .name}'
        else:
            created_date = fields.Datetime.to_string(fields.Datetime.context_timestamp(self, fields.Datetime.from_string(self.create_date)).astimezone(tz))
            data = f'Creado por: {self.env.user.name}, Fecha de creación: {created_date}, Volumen: {self.volume_profile.name}, Crédito: {self.financial_profile .name}, Logístico: {self.logistic_profile .name}'            
        return data
        
    def download_report(self):
        if self.partner_id:
            return self.get_xlsx_report(self.partner_id)
        elif not self.partner_id and self.volume_profile and self.financial_profile  and self.logistic_profile :
            return self.get_xlsx_report(self.partner_id)

    def calcular_porcentaje(self,monto_original, porcentaje, operacion):
        if operacion == "suma":
            resultado = monto_original + (monto_original * porcentaje / 100)
        elif operacion == "resta":
            resultado = monto_original - (monto_original * porcentaje / 100)
        else:
            raise ValueError("La operación debe ser 'suma' o 'resta'")
        return resultado

    def insert_table_sheet1(self, sheet, table_data, table_name):
        headers = list(table_data[0].keys()) if table_data else []
        num_rows = len(table_data)
        if num_rows == 0 or not headers:
            return  # No hay datos o encabezados, salir sin crear la tabla

        for col_idx, header in enumerate(headers, start=1):
            cell = sheet.cell(row=13, column=col_idx)
            cell.value = header
            cell.font = Font(bold=True)

        for row_idx, row_data in enumerate(table_data, start=14):
            for col_idx, header in enumerate(headers, start=1):
                if header == "Precio Regular":
                    sheet.cell(row=row_idx, column=col_idx).value = f'=MIN(P{row_idx}:R{row_idx})'     
                    #=IF(IF(MIN(Q{row_idx}:T{row_idx}) > 0, MIN(Q{row_idx}:T{row_idx}), "") = S{row_idx}, S{row_idx}, IF(MIN(Q{row_idx}:T{row_idx}) > 0, MIN(Q{row_idx}:T{row_idx}), "") * (1-IF(ISNUMBER($U$13), $U$13, 0)))
                elif header == "PRECIO CON DESCUENTOS":
                    sheet.cell(row=row_idx, column=col_idx).value = f'''=S{row_idx} - 
                                                                        (IF(OR($A$8=1,$A$8=150,$A$8=350,$A$8=600), ((S{row_idx}*$D$8) + (S{row_idx}*$E$8) + (S{row_idx}*$F$8)), 0)) - 
                                                                        (S{row_idx} * IF(ISNUMBER(IFERROR(FIND(F{row_idx}, UPPER($N$7)), "")), $S$7, 0)) - 
                                                                        (S{row_idx} * IF(ISNUMBER(IFERROR(FIND(F{row_idx}, UPPER($N$9)), "")), $S$9, 0))
                                                                        '''
                                                                        
                # f'''=S{row_idx} - 
                #     (IF(OR($A$8=1,$A$8=150,$A$8=350,$A$8=600), ((S{row_idx}*$D$8) + (S{row_idx}*$E$8) + (S{row_idx}*$F$8)), 0)) - 
                #     IF(Q{row_idx} = S{row_idx}, S{row_idx}*$L$9, 0) -
                #     IF(AND(V{row_idx} <> "", $A$8 >= 150), (S{row_idx}*V{row_idx}), 0) -
                #     (S{row_idx} * IF(ISNUMBER(IFERROR(FIND(F{row_idx}, UPPER($N$7)), "")), $S$7, 0)) - 
                #     (S{row_idx} * IF(ISNUMBER(IFERROR(FIND(F{row_idx}, UPPER($N$9)), "")), $S$9, 0)) '''                                                        
                                                                                                    
                # f'''=S{row_idx} - 
                #     (IF(OR($A$13=1,$A$13=150,$A$13=350,$A$13=600), ((S{row_idx}*$D$13) + (S{row_idx}*$E$13) + (S{row_idx}*$F$13)), 0)) - 
                #     (S{row_idx} * IF(ISNUMBER(IFERROR(FIND(F{row_idx}, UPPER($I$12)), "")), $I$14, 0)) - 
                #     (S{row_idx} * IF(ISNUMBER(IFERROR(FIND(F{row_idx}, UPPER($J$12)), "")), $J$14, 0)) - 
                #     (S{row_idx} * IF(ISNUMBER(IFERROR(FIND(F{row_idx}, UPPER($K$12)), "")), $K$14, 0)) - 
                #     (S{row_idx} * IF(ISNUMBER(IFERROR(FIND(F{row_idx}, UPPER($L$12)), "")), $L$14, 0)) - 
                #     IF(V{row_idx} <> "", (S{row_idx}*V{row_idx}), 0)'''                                                        
                                                                    
                else:
                     sheet.cell(row=row_idx, column=col_idx).value = row_data.get(header, "")

        end_col_letter = get_column_letter(len(headers))
        table_ref = f"A13:{end_col_letter}{num_rows + 13}"
        table = Table(displayName=table_name, ref=table_ref)
        style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False,
                               showLastColumn=False, showRowStripes=True, showColumnStripes=True)
        table.tableStyleInfo = style
        sheet.add_table(table)
        return num_rows + 13, len(headers)  # Retorna el número de filas y columnas
####################################################################################################
    def insert_table_sheet3(self, sheet, table_data, table_name):
        headers = list(table_data[0].keys()) if table_data else []
        num_rows = len(table_data)
        if num_rows == 0 or not headers:
            return  # No hay datos o encabezados, salir sin crear la tabla

        for col_idx, header in enumerate(headers, start=1):
            cell = sheet.cell(row=13, column=col_idx)
            cell.value = header
            cell.font = Font(bold=True)

        for row_idx, row_data in enumerate(table_data, start=14):
            for col_idx, header in enumerate(headers, start=1):
                if header == "Precio Regular":
                    sheet.cell(row=row_idx, column=col_idx).value = f'=IF(N{row_idx} = "", O{row_idx}, MIN((N{row_idx}*0.9), O{row_idx}))'
                elif header == "PRECIO CON DESCUENTOS":
                    sheet.cell(row=row_idx, column=col_idx).value = f'''=P{row_idx} - (IF(OR($A$8=1,$A$8=150,$A$8=350,$A$8=600), (IF(N{row_idx} <> "", ((N{row_idx}*$D$8) + (N{row_idx}*$E$8) + (N{row_idx}*$F$8)), ((O{row_idx}*$D$8) + (O{row_idx}*$E$8) + (O{row_idx}*$F$8)))), 0)) - Q{row_idx}'''
                elif header == "Precio Potencial":
                    sheet.cell(row=row_idx, column=col_idx).value = f'''=R{row_idx} - S{row_idx}'''
                elif header == "Bono Tarjeta":
                    sheet.cell(row=row_idx, column=col_idx).value = f'''=IF(V{row_idx} <> "", IF($K$8 = "Sin bono", 0, IF($K$8 = "Por cada 50 mil pesos por mes", V{row_idx}, IF($K$8 = "Por cada 100 mil pesos por mes", W{row_idx}, IF($K$8 = "Por cada 200 mil pesos por mes", X{row_idx}, 0)))), 0)'''
                elif header == "FACTURACIÓN":
                    sheet.cell(row=row_idx, column=col_idx).value = f'=IF(Z{row_idx} = "", "", Z{row_idx}*U{row_idx})'   
                else:
                     sheet.cell(row=row_idx, column=col_idx).value = row_data.get(header, "")

        end_col_letter = get_column_letter(len(headers))
        table_ref = f"A13:{end_col_letter}{num_rows + 13}"
        table = Table(displayName=table_name, ref=table_ref)
        style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False,
                               showLastColumn=False, showRowStripes=True, showColumnStripes=True)
        table.tableStyleInfo = style
        sheet.add_table(table)
        return num_rows + 13, len(headers)  # Retorna el número de filas y columnas
####################################################################################################
    def insert_table_sheet5(self, sheet, table_data, table_name):
        headers = list(table_data[0].keys()) if table_data else []
        num_rows = len(table_data)
        
        if num_rows == 0 or not headers:
            return  # No hay datos o encabezados, salir sin crear la tabla

        for col_idx, header in enumerate(headers, start=1):
            cell = sheet.cell(row=2, column=col_idx)
            cell.value = header
            cell.font = Font(bold=True)
            
        for row_idx, row_data in enumerate(table_data, start=3):
            for col_idx, header in enumerate(headers, start=1):
                sheet.cell(row=row_idx, column=col_idx).value = row_data.get(header, "")

        end_col_letter = get_column_letter(len(headers))
        table_ref = f"A2:{end_col_letter}{num_rows + 2}"
        table = Table(displayName=table_name, ref=table_ref)
        style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False,
                               showLastColumn=False, showRowStripes=True, showColumnStripes=True)
        table.tableStyleInfo = style
        sheet.add_table(table)
        return num_rows + 2, len(headers)  # Retorna el número de filas y columnas
####################################################################################################
    def set_combos(self,sheet, combo_data):
        combo_cells = []
        for data in combo_data:
            cell_ref = data['cell_ref']
            values = data['values']
            combo_cells.append(self._set_combo(sheet, cell_ref, values))
        return combo_cells

    def _set_combo(self,sheet, cell_ref, values):
        dv = DataValidation(type="list", formula1='"' + ','.join(values) + '"', allow_blank=True)
        dv.error = "Solo puedes seleccionar valores de la lista."
        dv.errorTitle = "Entrada no válida"
        dv.showErrorMessage = True
        sheet.add_data_validation(dv)
        
        celdas = sheet[cell_ref]
        if not isinstance(celdas, tuple):  # si es una sola celda (Cell)
            celdas = ((celdas,),)  # lo convertimos en tupla de tuplas

        for row in celdas:
            for cell in row:
                cell.protection = Protection(locked=False)
        
        dv.add(sheet[cell_ref])
        sheet[cell_ref].font = Font(bold=False)
        return cell_ref

    def apply_styles(self, sheet, cell_range, font_style, align_style, fill_style, border_style, num_format):
        for row in cell_range:
            for cell in row:
                cell.font = font_style
                cell.alignment = align_style
                cell.fill = fill_style
                cell.border = border_style
                if num_format:
                    cell.number_format = num_format

    def format_column(self, sheet, column_name, data_type):
        col_idx = column_index_from_string(column_name)
        num_format = None        
        if data_type == 'date':
            num_format = 'DD/MM/YYYY'
        elif data_type == 'currency':
            num_format = '$#,##0.00'
        elif data_type == 'number':
            num_format = '#,##0'
        elif data_type == 'string':
            num_format = None  # No specific format
        for row in sheet.iter_rows(min_col=col_idx, max_col=col_idx, min_row=14):
            for cell in row:
                if cell.value == 0:
                    cell.value = None  # Set cell value to None to leave it empty
                elif num_format:
                    cell.number_format = num_format

    def set_white_fill(self, sheet, start_cell, num_rows, num_cols):
        start_col_letter = ''.join(filter(str.isalpha, start_cell))
        start_row_number = ''.join(filter(str.isdigit, start_cell))
        
        start_col_idx = column_index_from_string(start_col_letter)
        end_col_idx = start_col_idx + num_cols -1
        end_row_number = int(start_row_number) + num_rows

        end_col_letter = get_column_letter(end_col_idx)
        cell_range = f'{start_col_letter}{start_row_number}:{end_col_letter}{end_row_number}'

        fill_style = PatternFill(start_color=WHITE, end_color=WHITE, fill_type="solid")
        alignment_style = Alignment(horizontal='center', vertical='center')
        for row in sheet[cell_range]:
            for cell in row:
                cell.fill = fill_style
                cell.alignment = alignment_style

    def format_cell(self,sheet, cell_ref, font_name, font_size, font_color, bold, fill_color, border, align, top_align, wrap_text=False, num_format=None, value=None, data_type='string'):
        # Parse the cell reference or range
        if ':' in cell_ref:
            start_ref, end_ref = cell_ref.split(':')
            cell_range = sheet[start_ref:end_ref]
            merged_cells = True
        else:
            start_ref = cell_ref
            cell_range = [[sheet[start_ref]]]
            merged_cells = False

        # Define styles
        font_style = Font(name=font_name, size=font_size, color=font_color, bold=bold)
        align_style = Alignment(horizontal=align, vertical=top_align, wrap_text=wrap_text)
        fill_style = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
        border_style = Border(left=Side(border_style=border),
                            right=Side(border_style=border),
                            top=Side(border_style=border),
                            bottom=Side(border_style=border))

        # Set number format if applicable
        if data_type == 'date':
            num_format = 'yyyy-mm-dd'
        elif data_type == 'currency':
            num_format = '$#,##0.00'
        elif num_format is None:
            num_format = '#,##0.00' if data_type == 'number' else None
            
        # Apply styles
        self.apply_styles(sheet, cell_range, font_style, align_style, fill_style, border_style, num_format)

        # Set value to the first cell
        if value is not None:
            sheet[start_ref].value = value

        # Adjust column width based on content length
        start_col, start_row = start_ref[0], int(start_ref[1:])
        end_col = end_ref[0] if merged_cells else start_col
        end_row = int(end_ref[1:]) if merged_cells else start_row

        for col in range(ord(start_col), ord(end_col) + 1):
            col_letter = get_column_letter(col)
            max_len = 0
            for row in range(start_row, end_row + 1):
                cell = sheet[col_letter + str(row)]
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            adjusted_width = (max_len + 5) * 1.4
            sheet.column_dimensions[col_letter].width = adjusted_width

        # Merge cells if needed
        if merged_cells:
            sheet.merge_cells(start_row=start_row, start_column=ord(start_col) - 64,
                            end_row=end_row, end_column=ord(end_col) - 64)

    def create_attachment(self,res_id,partner_id):
        encoded_data = self.get_xlsx_report(partner_id,return_base_64=True)
        attachment = self.env['ir.attachment'].create({
            'name': f'{partner_id.name or "Lista de Precios"}.xlsx',
            'type': 'binary',
            'public' : True,
            'datas': encoded_data,
            'store_fname': f'{partner_id.name or "Lista de Precios"}.xlsx',
            'mimetype': 'application/vnd.ms-excel',
            'res_model': self._name,
            'res_id': res_id or partner_id.id,
        })
        return attachment 

    def color_cells_based_on_condition(self, sheet):
        outlet_col_idx = column_index_from_string('Q')  # Replace 'A' with actual column letter for 'Outlet'
        ids_in_codes_brig = column_index_from_string('H')
        # Define el rango de celdas que deseas pintar
        outlet_start_column = 'S'
        outlet_end_column = 'U'
        
        t4_col_idx = column_index_from_string('B')
        tier4_col_idx = column_index_from_string('H')
        
        # milestar_col_idx = column_index_from_string('H')
        # measure_col_idx = column_index_from_string('C')
        # segment_col_idx = column_index_from_string('K')
        # model_col_idx = column_index_from_string('G')
        
        id_col_idx = 'A'
        
        start_column = 'A'
        end_column = 'S'
        
        # start_column2 = 'G'
        # end_column2 = 'G'
        
        # start_column3 = 'A'
        # end_column3 = 'B'
        
        for row in sheet.iter_rows(min_row=14):  # Start from row 2 to skip header
            outlet_cell = row[outlet_col_idx - 1]  # Adjust index to zero-based
            t4_cell = row[t4_col_idx - 1]
            tier4_cell = row[tier4_col_idx - 1]
            # Example condition: Color 'Outlet' column yellow if cell value is not empty
            if isinstance(outlet_cell.value, (int, float)) and outlet_cell.value > 0:
                for col_idx in range(column_index_from_string(outlet_start_column) - 1, column_index_from_string(outlet_end_column)):
                    cell = row[col_idx]
                    cell.fill = PatternFill(start_color='EBEBEB', end_color='EBEBEB', fill_type='solid')
                outlet_cell.fill = PatternFill(start_color='EBEBEB', end_color='EBEBEB', fill_type='solid')
                    
        for row in sheet.iter_rows(min_row=14):
            cupon_cell = row[column_index_from_string(id_col_idx) - 1]
            desc_pirelli = {t[0]: t[1] for t in codes_pirelli}
            desc_kumho = {t[0]: t[1] for t in codes_kumho}
            desc_goodyear = {t[0]: t[1] for t in codes_goodyear}
            
            if cupon_cell.value in desc_pirelli:
                for col_idx in range(column_index_from_string(start_column) - 1, column_index_from_string(end_column)):
                    cell = row[col_idx]
                    cell.fill = PatternFill(start_color=YELLOW, end_color=YELLOW, fill_type='solid')
            elif cupon_cell.value in desc_goodyear:
                for col_idx in range(column_index_from_string(start_column) - 1, column_index_from_string(end_column)):
                    cell = row[col_idx]
                    cell.fill = PatternFill(start_color='DCE6F1', end_color='DCE6F1', fill_type='solid')
            elif cupon_cell.value in desc_kumho:
                for col_idx in range(column_index_from_string(start_column) - 1, column_index_from_string(end_column)):
                    cell = row[col_idx]
                    cell.fill = PatternFill(start_color='FDE9D9', end_color='FDE9D9', fill_type='solid')

        #for row in sheet.iter_rows(min_row=15):
        #    milestar_cell = row[milestar_col_idx - 1]
            #measure_cell = row[measure_col_idx - 1]
            #segment_cell = row[segment_col_idx - 1]
            # for col in range(ord(start_column), ord(end_column) + 1):
            #     if milestar_cell.value in ['KUMHO'] and any(r in measure_cell.value for r in ['R13', 'R14', 'R15', 'R16']) and segment_cell.value in ['AT', 'MT']:
            #         cell = row[col - ord(start_column)]
            #         cell.fill = PatternFill(start_color='C5D9F1', end_color='C5D9F1', fill_type='solid')
            #     elif milestar_cell.value in ['KUMHO'] and any(r in measure_cell.value for r in ['R17', 'R18', 'R19', 'R20', 'R21', 'R22']) and segment_cell.value in ['AT', 'MT']:
            #         cell = row[col - ord(start_column)]
            #         cell.fill = PatternFill(start_color='8DB4E2', end_color='8DB4E2', fill_type='solid')
                
        # for row in sheet.iter_rows(min_row=15):
        #     model_cell = row[model_col_idx - 1]
        #     for col in range(ord(start_column2), ord(end_column2) + 1):
        #         if model_cell.value in ['MS932 SPORT', 'WEATHERGUARD AW365', 'COVERT GRIP CV']:
        #             cell = row[col - ord(start_column)]
        #             cell.fill = PatternFill(start_color='D9D9D9', end_color='D9D9D9', fill_type='solid')
                    
        # for row in sheet.iter_rows(min_row=15):
        #     tier4_cell = row[tier4_col_idx - 1]
        #     for col in range(ord(start_column3), ord(end_column3) + 1):
        #         if tier4_cell.value in ['MILESTAR', 'VENOM']:
        #             cell = row[col - ord(start_column)]
        #             cell.fill = PatternFill(start_color='BFBFBF', end_color='BFBFBF', fill_type='solid')  
                    
    def color_cells_based_on_condition_sheet3(self, sheet):
        ids_in_codes_brig = 'A'
        codes_brige = 'B'
        start_column = 'P'
        end_column = 'Q'
        outlet_col_idx = column_index_from_string('O')
        outlet_start_column = 'O'
        outlet_end_column = 'P'
        column_bonus_cards = 'S'
        column_end_bonus_cards = 'T'
        cupones = 'R'
        
        
        for row in sheet.iter_rows(min_row=14):
            cupon_cell = row[column_index_from_string(ids_in_codes_brig) - 1]
            bonus_cards = {t[0]: t[3] for t in codes_bridgestone_promo if t[3] == "SI"}
            
            if cupon_cell.value in bonus_cards:
                for col_idx in range(column_index_from_string(column_bonus_cards) - 1, column_index_from_string(column_end_bonus_cards)):
                    cell = row[col_idx]
                    cell.fill = PatternFill(start_color='F2DCDB', end_color='F2DCDB', fill_type='solid')
        
        for row in sheet.iter_rows(min_row=14):  # Start from row 2 to skip header
            outlet_cell = row[outlet_col_idx - 1]  # Adjust index to zero-based
            # Example condition: Color 'Outlet' column yellow if cell value is not empty
            if isinstance(outlet_cell.value, (int, float)) and outlet_cell.value > 0:
                for col_idx in range(column_index_from_string(outlet_start_column) - 1, column_index_from_string(outlet_end_column)):
                    cell = row[col_idx]
                    cell.fill = PatternFill(start_color='EBEBEB', end_color='EBEBEB', fill_type='solid')
                outlet_cell.fill = PatternFill(start_color='EBEBEB', end_color='EBEBEB', fill_type='solid')
                
        for row in sheet.iter_rows(min_row=14):
            cupon_cell = row[column_index_from_string(ids_in_codes_brig) - 1]
            cupon_codes = {t[0]: t[2] for t in codes_bridgestone_promo if t[2] == "SI"}
            if cupon_cell.value in cupon_codes:
                for col_idx in range(column_index_from_string(start_column) - 1, column_index_from_string(end_column)):
                    cell = row[col_idx]
                    cell.fill = PatternFill(start_color='FDE9D9', end_color='FDE9D9', fill_type='solid')
                for col_idx in range(column_index_from_string(ids_in_codes_brig) - 1, column_index_from_string(codes_brige)):
                    cell = row[col_idx]
                    cell.fill = PatternFill(start_color='FDE9D9', end_color='FDE9D9', fill_type='solid')
                    
        for row in sheet.iter_rows(min_row=14):
            id_cell = row[column_index_from_string(cupones) - 1]
            if id_cell.value not in ["", None]:
                id_cell.fill = PatternFill(start_color='D9D9D9', end_color='D9D9D9', fill_type='solid')
                id_cell.font = Font(color="C00000", bold=True)
                
    def insert_formula(self,sheet, column, start_row, template):
        current_row = start_row
        while current_row <= sheet.max_row:
            cell = f"{column}{current_row}"
            formula = template.replace('{column}', column).replace('{row}', str(current_row))
            sheet[cell].value = formula
            current_row += 1

    def get_dict_data(self, objects, sheet_name,partner_id=False):
        if sheet_name == 'Precios Con Iva':
            checo_ids = objects.filtered(lambda obj: obj.volumen > 0 or obj.promocion > 0 or obj.promo_dot > 0 or obj.outlet).ids
            #Eliminar todo lo de additional_discounts
            c = checo_ids
            ids_tuple = tuple(c)
            
            # Construir la consulta SQL con los IDs en la cláusula IN
            query = """
                SELECT id 
                FROM inv_promo_report 
                WHERE id IN %s     
                AND brand_id NOT IN (3, 11)
            """
            # Ejecutar la consulta con la tupla de IDs
            self.env.cr.execute(query, (ids_tuple,))
            result = self.env.cr.fetchall()
            
            ids = [row[0] for row in result]
        if sheet_name == 'Transitos':
            # Obtener los IDs de los objetos y convertirlos en una tupla para SQL
            ids_tuple = tuple(objects.ids)
            
            # Construir la consulta SQ
            query = """
                SELECT id 
                FROM inv_promo_report 
                WHERE id IN %s
                AND transit <> 0
            """
            
            self.env.cr.execute(query, (ids_tuple,))
            result = self.env.cr.fetchall()
            
            ids = [row[0] for row in result]
            objects = objects.browse(ids)
            data_list = []     
            for obj in objects:
                data_dict = {                
                    'id': obj.product_id.id,            
                    'Código': obj.default_code,
                    'Medida': obj.tire_measure_id.name if obj.tire_measure_id else None,
                    'Capas': obj.layer_id.name if obj.layer_id else None,
                    'Vel': obj.speed_id.name if obj.speed_id else None,
                    'Carga': obj.index_of_load_id.name if obj.index_of_load_id else None,
                    'Modelo': obj.model_id.name if obj.model_id else None,
                    'Marca': obj.brand_id.name if obj.brand_id else None,
                    #'Equipo Original': obj.original_equipment_id.name if obj.original_equipment_id else None,
                    'Tipo': obj.product_id.type_id.name or None,
                    'Seg': obj.product_id.segment_id.name or None,
                    'Tier': obj.tier_id.name if obj.tier_id else None,
                    'DOT': obj.lot_name or '' or None,
                    #'Inv.': obj.inventario_str,
                    #'Cantidad Disponible': obj.available,
                    'Trans.': (obj.transito_str + obj.backorder_str) or None,
                    'Arribo': obj.fecha_str or None,
                    }
                data_list.append(data_dict)
            return data_list
        if sheet_name == 'P. BRIDGESTONE':
            # Obtener los IDs de los objetos y convertirlos en una tupla para SQL
            ids_tuple = tuple(objects.ids)
            
            # Construir la consulta SQL con los códigos en la cláusula NOT IN y los IDs en la cláusula IN
            query = """
                SELECT id 
                FROM inv_promo_report 
                WHERE id IN %s
                AND brand_id IN (3, 11)
            """
            
            self.env.cr.execute(query, (ids_tuple,))
            result = self.env.cr.fetchall()
            
            ids = [row[0] for row in result]
            objects = objects.browse(ids)
            data_list = []     
            for obj in objects:
                data_dict = {                
                    'id': obj.product_id.id,            
                    'Código': obj.default_code,
                    #'Tier': obj.tier_id.name if obj.tier_id else None,
                    'Medida': obj.tire_measure_id.name if obj.tire_measure_id else None,
                    'Modelo': obj.model_id.name if obj.model_id else None,
                    'Marca': obj.brand_id.name if obj.brand_id else None,
                }
                
                # resultado = None
                # if obj.tire_measure_id.name and "R" in obj.tire_measure_id.name:
                #     resultado = obj.tire_measure_id.name.split("R", 1)[1].strip()
                #     data_dict.update({'Rin': float(resultado)})
                      
                data_dict.update({  
                    'Equipo Original': obj.original_equipment_id.name if obj.original_equipment_id else None,
                    'Tipo': obj.product_id.type_id.name or None,
                    'Seg': obj.product_id.segment_id.name or None,
                    'Capas': obj.layer_id.name if obj.layer_id else None,
                    'Vel': obj.speed_id.name if obj.speed_id else None,
                    'Carga': obj.index_of_load_id.name if obj.index_of_load_id else None,
                    'DOT': obj.lot_name or '' or None,
                    'Inv.': obj.inventario_str or None,
                    #'Cantidad Disponible': obj.available,
                    #'Trans.': (obj.transito_str + obj.backorder_str) or None,
                    #'Arribo': obj.fecha_aprox or None,
                    })  
                
                data_list.append(data_dict)            
                data_dict.update({
                    'Mayoreo': (obj.volumen * 1.16),
                    'Outlet': obj.outlet * 1.16,
                    #'Promo Dot': obj.promo_dot * 1.16,
                    #'PROMO BS': ""
                    })
                
                # if self.partner_id:
                #     promo_mayoreo = {t[0]: t[1] for t in codes2}
                #     if obj.product_id.id in promo_mayoreo:
                #         data_dict.update({'PROMO BS': promo_mayoreo[obj.product_id.id] * 1.16})
                #     else:
                #         data_dict.update({'PROMO BS': ''})
                        
                data_dict.update({
                    'Precio Regular': "",
                })
                
                if self.partner_id:
                    cupones_dict5 = {t[0]: t[1] for t in codes_bridgestone_promo if t[2] == "SI"}
                    if obj.product_id.id in cupones_dict5:
                        data_dict.update({'Cupones': ((cupones_dict5[obj.product_id.id] * .05) * 1.16).__round__(2)})
                    else:
                        data_dict.update({'Cupones': ''})

                data_dict.update({
                    'PRECIO CON DESCUENTOS': "",
                })
                        
                data_dict.update({  
                    'Bono Tarjeta': "",
                    'Precio Potencial': "",
                    'PIEZAS': "",
                    #'FACTURACIÓN': ""
                    })
                if self.partner_id:
                    bonus_cards = {t[0]: t[1] for t in codes_bridgestone_promo if t[3] == "SI"}
                    if obj.product_id.id in bonus_cards:
                        data_dict.update({'4%': ((bonus_cards[obj.product_id.id] * .04) * 1.16).__round__(2)})
                        data_dict.update({'5%': ((bonus_cards[obj.product_id.id] * .05) * 1.16).__round__(2)})
                        data_dict.update({'6%': ((bonus_cards[obj.product_id.id] * .06) * 1.16).__round__(2)})
                    else:
                        data_dict.update({'4%': ''})
                        data_dict.update({'5%': ''})
                        data_dict.update({'6%': ''})
                else:
                    if obj.product_id.id in bonus_cards:
                        data_dict.update({'4%': ((bonus_cards[obj.product_id.id] * .04) * 1.16).__round__(2)})
                        data_dict.update({'5%': ((bonus_cards[obj.product_id.id] * .05) * 1.16).__round__(2)})
                        data_dict.update({'6%': ((bonus_cards[obj.product_id.id] * .06) * 1.16).__round__(2)})
                    else:
                        data_dict.update({'4%': ''})
                        data_dict.update({'5%': ''})
                        data_dict.update({'6%': ''})  
                
                # if obj.volumen > 0:
                #     data_dict.update({
                #         'PRECIO FACTURA': (obj.volumen * 1.16)
                #     })
                # else:
                #     data_dict.update({
                #         'PRECIO FACTURA': obj.promo_dot * 1.16
                #     })
            return data_list
        
        objects = objects.browse(ids)
        data_list = []     
        for obj in objects:
            resultado = None
            data_dict = {                
                'id': obj.product_id.id,            
                'Código': obj.default_code,
                'Tier': obj.tier_id.name if obj.tier_id else None,
                'Medida': obj.tire_measure_id.name if obj.tire_measure_id else None,
                'Modelo': obj.model_id.name if obj.model_id else None,
                'Marca': obj.brand_id.name if obj.brand_id else None,
            }
            
            resultado = None
            if obj.tire_measure_id.name and "R" in obj.tire_measure_id.name:
                resultado = obj.tire_measure_id.name.split("R", 1)[1].strip()
                data_dict.update({'Rin': float(resultado)})
                  
            data_dict.update({  
                'Equipo Original': obj.original_equipment_id.name if obj.original_equipment_id else None,
                'Tipo': obj.product_id.type_id.name or None,
                'Seg': obj.product_id.segment_id.name or None,
                'Capas': obj.layer_id.name if obj.layer_id else None,
                'Vel': obj.speed_id.name if obj.speed_id else None,
                'Carga': obj.index_of_load_id.name if obj.index_of_load_id else None,
                'DOT': obj.lot_name or 'N/A' or None,
                'Inv.': obj.inventario_str or None,
                #'Cantidad Disponible': obj.available,
                #'Trans.': (obj.transito_str + obj.backorder_str) or None,
                #'Arribo': obj.fecha_aprox or None,
                })   
            data_list.append(data_dict)            
            data_dict.update({
                'Mayoreo': obj.volumen * 1.16,
                'Outlet': obj.outlet * 1.16,
                'Promo Dot': obj.promo_dot * 1.16,
                'Precio Regular': "",
                'PRECIO CON DESCUENTOS': "",
                'Pedido': "",
            })
            if self.partner_id:
                desc_pirelli = {t[0]: t[1] for t in codes_pirelli}
                desc_kumho = {t[0]: t[1] for t in codes_kumho}
                desc_goodyear = {t[0]: t[1] for t in codes_goodyear}
                if obj.product_id.id in desc_kumho:
                    data_dict.update({'DESCUENTO': desc_kumho[obj.product_id.id]})
                elif obj.product_id.id in desc_goodyear:
                    data_dict.update({'DESCUENTO': desc_goodyear[obj.product_id.id]})
                elif obj.product_id.id in desc_pirelli:
                    data_dict.update({'DESCUENTO': desc_pirelli[obj.product_id.id]})
                else:
                    data_dict.update({'DESCUENTO': 0})
            else:
                if obj.product_id.id in desc_kumho:
                    data_dict.update({'DESCUENTO': desc_kumho[obj.product_id.id]})
                elif obj.product_id.id in desc_goodyear:
                    data_dict.update({'DESCUENTO': desc_goodyear[obj.product_id.id]})
                elif obj.product_id.id in desc_pirelli:
                    data_dict.update({'DESCUENTO': desc_pirelli[obj.product_id.id]})
                else:
                    data_dict.update({'DESCUENTO': 0})
        return data_list

    def set_frames(self, sheet):        
        img_path = "/mnt/extra-addons/inv_promo/wizard/models/Logo.png"    
        img = Image(img_path)
        img.height = 65  # Establece la altura en píxeles calculados
        img.width = 355   # Establece el ancho en píxeles calculados                       
        # Insertar la imagen en la hoja
        sheet.add_image(img, 'A1')
        # Crear un comentario
        comentario = Comment("Aplica por entrega en una misma dirección", "Ztyres")
        # Asignar el comentario a la celda
        sheet["E8"].comment = comentario
        
    def set_brief(self, sheet):        
        img_path = "/mnt/extra-addons/inv_promo/wizard/models/Encabezado.png"
        img_path = "/mnt/extra-addons/inv_promo/wizard/models/Brief.jpg"
        img = Image(img_path)
        img.height = 708  # Establece la altura en píxeles calculados
        img.width = 1196   # Establece el ancho en píxeles calculados         
        sheet.add_image(img, 'A1')
        # return

    def get_xlsx_report(self, partner_id, return_base_64=False):
        include_promo = True
        
        objects = self.env['inv_promo.report'].sudo().insert_data()
        con_iva = self.get_dict_data(objects,'Precios Con Iva',partner_id)
        promo_bridgestone = self.get_dict_data(objects, 'P. BRIDGESTONE', partner_id)
        transitos_tabla = self.get_dict_data(objects, 'Transitos', partner_id)
        
        
        wb = Workbook()
        sheet1 = wb.active
        sheet1.title = "Precios Con Iva"

        #financial,logistic = self.get_profile_data(partner_id)
        vendedor = self.get_profile_data(partner_id)
                
        llantas_x_mes = ['1', '150', '350', '600']
        
        #volume_percent = ['0%','2%','3%']
        logistic_percent = ['0%','2%','4%']
        financial_percent = ['0%','2%','3%']
        
        des_x_factura = ['0%', '3%']
        
        bonus_cards = [
            'Sin bono',
            'Por cada 50 mil pesos por mes', 
            'Por cada 100 mil pesos por mes', 
            'Por cada 200 mil pesos por mes'
            ]
        
        #bs_percentR14 = ['0%', '5%', '8%']
        #bs_percentR18 = ['0%', '8%']
        #bs_percentR14 = ['$1 a $46¸399', '$46¸400 a $579¸999', 'Más de $580¸000']
        #bs_percentR18 = ['$1 a $46¸399', 'Más de $46¸400']
         
        combo_data_sheet1 = [
            #{'cell_ref': 'D7', 'values': volume_percent},
            {'cell_ref': 'E8', 'values': logistic_percent},
            {'cell_ref': 'F8', 'values': financial_percent},
            {'cell_ref': 'A8', 'values': llantas_x_mes},
            
            {'cell_ref': 'S7', 'values': des_x_factura},
            {'cell_ref': 'S9', 'values': des_x_factura},
        ]
        
        combo_data_sheet3 = [
            {'cell_ref': 'E8', 'values': logistic_percent},
            {'cell_ref': 'F8', 'values': financial_percent},
            
            {'cell_ref': 'A8', 'values': llantas_x_mes},
            
            {'cell_ref': 'K8', 'values': bonus_cards},
            #{'cell_ref': 'I8', 'values': bs_percentR14},
            #{'cell_ref': 'M8', 'values': bs_percentR18}
        ]
        
        #####Fill Tables
        num_rows_1, num_cols_1 = self.insert_table_sheet1(sheet1, con_iva, "TablaDatos1")
        
        for row in sheet1.iter_rows(min_row=1, max_row=num_rows_1, min_col=1, max_col=num_cols_1 - 1):
            for cell in row:
                cell.protection = Protection(locked=True)
                
        # Desbloquear las celdas del rango B2:B4 (por ejemplo)
        for row in sheet1.iter_rows(min_row=1, max_row=num_rows_1, min_col=22, max_col=26):
            for cell in row:
                cell.protection = Protection(locked=False)
                
        # sheet1.protection.sheet = True
        # sheet1.protection.password = "Top$ecret"  # opcional
        # sheet1.protection.pivotTables = False
        # sheet1.protection.autoFilter = False
        # sheet1.protection.sort = True  
        # sheet1.protection.enable()
        
        self.set_combos(sheet1, combo_data_sheet1)

        self.set_frames(sheet1)
        
        sheet1.sheet_properties.tabColor = WHITE

        self.set_white_fill(sheet1, 'A1', num_rows_1, num_cols_1)
        values = '{"DOUBLESTAR","DELINTE","FIREMAX","APTANY"}'
        
         # Definir los datos para las celdas
        data_for_sheet1 = [
            {'cell_ref': 'A6:C7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "LLANTAS AL MES", 'data_type': 'string'},
            {'cell_ref': 'D6:F6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': RED, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "DESCUENTOS  SEGÚN POLÍTICA COMERCIAL", 'data_type': 'string'},
            {'cell_ref': 'D7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': '595959', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Volumen", 'data_type': 'string'},
            {'cell_ref': 'E7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'EBEBEB', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Logístico", 'data_type': 'string'},
            {'cell_ref': 'F7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': '595959', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Financiero", 'data_type': 'string'},
            
            {'cell_ref': 'A8:C8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': 1},
            {'cell_ref': 'D8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': f"""=IF(A8=1,0%,IF(A8=150,1%,IF(A8=350,2%,IF(A8=600,3%, 0%))))"""},
            {'cell_ref': 'E8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
            {'cell_ref': 'F8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': '00B050', 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
            
            {'cell_ref': 'A9:C9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "TOTAL LLANTAS", 'data_type': 'string'},
            {'cell_ref': 'A10:C11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=SUM(U14:U{num_rows_1})+SUM('P. BRIDGESTONE'!X14:X{num_rows_1})"""},
            
            {'cell_ref': 'D9:F9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=IF(E8=0%, "Sin descuento de 1 a 99 llantas por envío", IF(E8=2%,"Descuento Logístico: Mín. 100 llantas x envío", IF(E8=4%, "Descuento Logístico: Mín. 300 llantas x envío", "Sin descuento de 1 a 99 llantas por envío")))"""},
            {'cell_ref': 'D10:F10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'EBEBEB', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Códigos con Super descuento", 'data_type': 'string'},
            {'cell_ref': 'D11:F11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': '00B050', 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Financiero aplica pagando en tiempo sus facturas", 'data_type': 'string'},
            
            ########################################################################################################################################################################################################################################################################################################################################
            # {'cell_ref': 'I6:L6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': RED, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "DESCUENTO REFLEJADO EN LA COLUMNA PRECIO CON DESCUENTOS", 'data_type': 'string'},
            
            # {'cell_ref': 'I12:I13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Milestar / Venom", 'data_type': 'string'},
            # {'cell_ref': 'J12:J13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Federal", 'data_type': 'string'},
            # {'cell_ref': 'K12:K13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Driveforce", 'data_type': 'string'},
            # {'cell_ref': 'L12:M13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Aptany/Delinte/ DoubleStar/Firemax", 'data_type': 'string'},
            # {'cell_ref': 'N12:Q13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "PIRELLI / FEDERAL / DUNLOP / ONYX", 'data_type': 'string'},
            # {'cell_ref': 'I7:J8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'FDE9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "KUMHO", 'data_type': 'string'},
            # {'cell_ref': 'K7:L8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': YELLOW, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "PIRELLI", 'data_type': 'string'},
            #{'cell_ref': 'K7:K8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'DCE6F1', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "GOODYEAR", 'data_type': 'string'},
            #{'cell_ref': 'L7:L8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'EBEBEB', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Lista Outlet ", 'data_type': 'string'},
            
            # {'cell_ref': 'I14:I15', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '0%', 'value': f"""=IF(A13 = 1, 0%, IF(A13 = 150, 3%, IF(A13 = 350, 5%, IF(A13 = 600, 5%, 0%))))"""},
            # {'cell_ref': 'J14:J15', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '0%', 'value': f"""=IF(A13 = 1, 0%, IF(A13 = 150, 3%, IF(A13 = 350, 5%, IF(A13 = 600, 5%, 0%))))"""},
            # {'cell_ref': 'K14:K15', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '0%', 'value': f"""=IF(A13 = 1, 0%, IF(A13 = 150, 3%, IF(A13 = 350, 4%, IF(A13 = 600, 4%, 0%))))"""},
            # {'cell_ref': 'L14:M15', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '0%', 'value': f"""=IF(A13 = 1, 0%, IF(A13 = 150, 3%, IF(A13 = 350, 3%, IF(A13 = 600, 4%, 0%))))"""},
            # {'cell_ref': 'N14:Q15', 'font_name': 'Calibri', 'font_size': 8, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '0%', 'value': "En un solo pedido con 2% financiero/capturar solo de una marca"},
            # {'cell_ref': 'I9:L10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Consulta códigos y descuentos", 'data_type': 'string'},
            # {'cell_ref': 'L9:L10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '0%', 'value': f"""=IF(A8 = 1, 0%, IF(A8 = 150, 4%, IF(A8 = 350, 4%, IF(A8 = 600, 4%, 0%))))"""},

            ########################################################################################################################################################################################################################################################################################################################################
            {'cell_ref': 'N6:S6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': RED, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "PROMOCIONES DE MARCA POR MES", 'data_type': 'string'},
            {'cell_ref': 'T6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "TOTAL LLANTAS", 'data_type': 'string'},
            
            {'cell_ref': 'N7:N8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "DUNLOP", 'data_type': 'string'},
            {'cell_ref': 'N9:N10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "ONYX", 'data_type': 'string'},
            {'cell_ref': 'N11:N12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "MILESTAR/VENOM", 'data_type': 'string'},
            
            {'cell_ref': 'O7:R8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': f"""=IF(S7=3%, "Mínimo 200 llantas Dunlop x mes", "No aplica")"""},
            {'cell_ref': 'O9:R10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': f"""=IF(S9=3%, "Mínimo 200 llantas Onyx x mes", "No aplica")"""},
            {'cell_ref': 'O11:S12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "$4,000 netos x cada 100 llantas x mes", 'data_type': 'string'},
            
            {'cell_ref': 'S7:S8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '0%',  'value': "0%", 'data_type': 'string'},
            {'cell_ref': 'S9:S10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '0%',  'value': "0%", 'data_type': 'string'},
            
            {'cell_ref': 'T7:T8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': f"""=SUMIF(F14:F{num_rows_1}, N7, U14:U{num_rows_1})"""},
            {'cell_ref': 'T9:T10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': f"""=SUMIF(F14:F{num_rows_1}, N9, U14:U{num_rows_1})"""},
            {'cell_ref': 'T11:T12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': f"""=SUMIF(F14:F{num_rows_1}, "MILESTAR", U14:U{num_rows_1}) + SUMIF(F14:F{num_rows_1}, "VENOM", U14:U{num_rows_1})"""},
            
            ########################################################################################################################################################################################################################################################################################################################################
            {'cell_ref': 'A2:D2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': None, 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "CÓDIGO:", 'data_type': 'string'},   
            {'cell_ref': 'E2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': None, 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "VTA-FO-03", 'data_type': 'string'},   
            {'cell_ref': 'J2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': None, 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "VERSIÓN:", 'data_type': 'string'},   
            {'cell_ref': 'K2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': None, 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "01", 'data_type': 'string'},
            {'cell_ref': 'O2:S2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': None, 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "FECHA DE EMISIÓN:", 'data_type': 'string'},   
            {'cell_ref': 'T2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': None, 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': 'DD/MM/YYYY', 'value': "17/12/2025", 'data_type': 'string'},   
            
            {'cell_ref': 'A3:U3', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'data_type': 'string'},   
            
            {'cell_ref': 'A4:E4', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'right', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "ASESOR: ", 'data_type': 'string'},   
            {'cell_ref': 'F4:J4', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': vendedor, 'data_type': 'string'},   
            
            {'cell_ref': 'A5:J5', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "PRECIOS SUJETOS A CAMBIOS SIN PREVIO AVISO", 'data_type': 'string'},   
            {'cell_ref': 'K4:O5', 'font_name': 'Calibri', 'font_size': 18, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': None, 'align': 'right', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'value': "FECHA DE ACTUALIZACIÓN", 'data_type': 'string'},
            
            {'cell_ref': 'S4:S5', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': None, 'align': 'right', 'top_align': 'center', 'wrap_text': True, 'num_format': 'DD/MM/YYYY', 'value': date.today(), 'data_type': 'string'},
            
            {'cell_ref': 'A1:E1', 'font_name': 'Calibri', 'font_size': 20, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thick', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'data_type': 'string'},  
            {'cell_ref': 'F1:U1', 'font_name': 'Calibri', 'font_size': 20, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thick', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Lista de precios", 'data_type': 'string'},   
            
            {'cell_ref': 'A13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'B13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'C13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'D13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'E13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'F13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'G13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'H13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'I13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'J13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'K13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'L13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'M13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'N13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'O13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'P13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'Q13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': '808080', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'S13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'T13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': RED, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'U13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'V13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
        ]
        
        #Establecer formatos
        self.format_column(sheet1,'A','number')
        self.format_column(sheet1,'B','string')
        self.format_column(sheet1,'C','string')
        self.format_column(sheet1,'D','string')
        self.format_column(sheet1,'E','string')
        self.format_column(sheet1,'F','string')
        self.format_column(sheet1,'G','number')
        self.format_column(sheet1,'H','string')
        self.format_column(sheet1,'I','string')
        self.format_column(sheet1,'J','string')
        self.format_column(sheet1,'K','string')
        self.format_column(sheet1,'L','string')
        self.format_column(sheet1,'M','string')
        self.format_column(sheet1,'N','number')
        self.format_column(sheet1,'O','number')
        self.format_column(sheet1,'P','currency')
        self.format_column(sheet1,'Q','currency')
        self.format_column(sheet1,'R','currency')
        self.format_column(sheet1,'S','currency')
        self.format_column(sheet1,'T','currency')
        self.format_column(sheet1,'U','number')
        self.format_column(sheet1,'V','string')
        
        columna_a_ocultar_sheet1 = ['A', 'C', 'G', 'P', 'Q', 'R', 'V']
        
        for columna_sheet1 in columna_a_ocultar_sheet1:
            sheet1.column_dimensions[columna_sheet1].hidden = True
        
        # Formatear las celdas para la hoja 1
        for data in data_for_sheet1:
            self.format_cell(sheet1, **data)
            
        self.color_cells_based_on_condition(sheet1)
        sheet1.sheet_view.showGridLines = False
        sheet1.freeze_panes = 'A14'
        
        start_row = 13
        end_row = num_rows_1
        start_col = 'A'
        end_col = 'V'   
        # Definir el borde que se aplicará a las celdas
        thin_border = Border(
            left=Side(style='thin', color="A6A6A6"),
            right=Side(style='thin', color="A6A6A6"),
            top=Side(style='thin', color="A6A6A6"),
            bottom=Side(style='thin', color="A6A6A6")
        )
        for row in sheet1.iter_rows(min_row=start_row, max_row=end_row, min_col=column_index_from_string(start_col), max_col=column_index_from_string(end_col)):
            for cell in row:
                cell.border = thin_border
        
        if include_promo:
            sheet3 = wb.create_sheet(title="P. BRIDGESTONE")
            sheet4 = wb.create_sheet(title="BRIEF_Promociones")
            sheet5 = wb.create_sheet(title="Transitos")
            
            num_rows_3, num_cols_3 = self.insert_table_sheet3(sheet3, promo_bridgestone, "TablaDatos2")
            num_rows_4, num_cols_4 = self.insert_table_sheet5(sheet5, transitos_tabla, "TablaDatos3")
            
            hojas_a_bloquear = [sheet3, sheet4, sheet5]
            
            for hoja in hojas_a_bloquear:
                for row in hoja.iter_rows(min_row=1, max_row=num_rows_3, min_col=1, max_col=num_cols_3):
                    for cell in row:
                        if cell.column_letter == "X":
                            cell.protection = Protection(locked=False)
                            #print ("Celda desbloqueada:", cell.coordinate)
                        else:
                            cell.protection = Protection(locked=True)
                        
                # Desbloquear las celdas del rango B2:B4 (por ejemplo)
                for row in hoja.iter_rows(min_row=1, max_row=num_rows_3, min_col=26, max_col=30):
                    for cell in row:
                        cell.protection = Protection(locked=False)
                    
            # for hoja in hojas_a_bloquear:
            #     hoja.protection.sheet = True
            #     hoja.protection.password = "Top$ecret"  # opcional
            #     hoja.protection.pivotTables = False
            #     hoja.protection.autoFilter = False
            #     hoja.protection.sort = True  
            #     hoja.protection.enable()
            
            self.set_frames(sheet3)
            self.set_brief(sheet4)
            sheet3.sheet_properties.tabColor = 'E6B8B8'
            sheet4.sheet_properties.tabColor = 'FFFF00'
            sheet5.sheet_properties.tabColor = '92D050'
            self.set_white_fill(sheet3, 'A1', num_rows_3, num_cols_3)
            self.set_white_fill(sheet5, 'A1', num_rows_4, num_cols_4)
            self.set_combos(sheet3, combo_data_sheet3)

            data_for_sheet3 = [
                {'cell_ref': 'A2:D2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': None, 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "CÓDIGO:", 'data_type': 'string'},   
                {'cell_ref': 'E2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': None, 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "VTA-FO-03", 'data_type': 'string'},   
                {'cell_ref': 'J2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': None, 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "VERSIÓN:", 'data_type': 'string'},   
                {'cell_ref': 'K2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': None, 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "01", 'data_type': 'string'},
                {'cell_ref': 'O2:T2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': None, 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "FECHA DE EMISIÓN:", 'data_type': 'string'},   
                {'cell_ref': 'U2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': None, 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': 'DD/MM/YYYY', 'value': "17/12/2025", 'data_type': 'string'},   
                
                {'cell_ref': 'A3:U3', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'data_type': 'string'},   
                
                {'cell_ref': 'A4:E4', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'right', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "ASESOR: ", 'data_type': 'string'},   
                {'cell_ref': 'F4:J4', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': vendedor, 'data_type': 'string'},   
                
                {'cell_ref': 'A5:J5', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "PRECIOS SUJETOS A CAMBIOS SIN PREVIO AVISO", 'data_type': 'string'},   
                {'cell_ref': 'K4:O5', 'font_name': 'Calibri', 'font_size': 18, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': None, 'align': 'right', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'value': "FECHA DE ACTUALIZACIÓN", 'data_type': 'string'},
                
                {'cell_ref': 'U4:U5', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': None, 'align': 'right', 'top_align': 'center', 'wrap_text': True, 'num_format': 'DD/MM/YYYY', 'value': date.today(), 'data_type': 'string'},
                
                {'cell_ref': 'A1:E1', 'font_name': 'Calibri', 'font_size': 20, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thick', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'data_type': 'string'},  
                {'cell_ref': 'F1:U1', 'font_name': 'Calibri', 'font_size': 20, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thick', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Lista de precios", 'data_type': 'string'},  
                    
                {'cell_ref': 'A6:C7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "LLANTAS AL MES", 'data_type': 'string'},
                {'cell_ref': 'D6:F6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': RED, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "DESCUENTOS  SEGÚN POLÍTICA COMERCIAL", 'data_type': 'string'},
                {'cell_ref': 'D7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': '595959', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Volumen", 'data_type': 'string'},
                {'cell_ref': 'E7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'EBEBEB', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Logístico", 'data_type': 'string'},
                {'cell_ref': 'F7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': '595959', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Financiero", 'data_type': 'string'},
                
                {'cell_ref': 'A8:C8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': 1},
                {'cell_ref': 'D8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': f"""=IF(A8=1,0%,IF(A8=150,1%,IF(A8=350,2%,IF(A8=600,3%, 0%))))"""},
                {'cell_ref': 'E8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
                {'cell_ref': 'F8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': '00B050', 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
                
                {'cell_ref': 'A9:C9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "TOTAL LLANTAS", 'data_type': 'string'},
                {'cell_ref': 'A10:C11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=SUM(U14:U{num_rows_3})+SUM('Precios Con Iva'!U14:U{num_rows_1})"""},
                
                {'cell_ref': 'D9:F9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=IF(E8=0%, "Sin descuento de 1 a 99 llantas por envío", IF(E8=2%,"Descuento Logístico: Mín. 100 llantas x envío", IF(E8=4%, "Descuento Logístico: Mín. 300 llantas x envío", "Sin descuento de 1 a 99 llantas por envío")))"""},
                {'cell_ref': 'D10:F10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'EBEBEB', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Códigos con Super descuento", 'data_type': 'string'},
                {'cell_ref': 'D11:F11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': '00B050', 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Financiero aplica pagando en tiempo sus facturas", 'data_type': 'string'},
                    
                {'cell_ref': 'A13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'B13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'C13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'D13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'E13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'F13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'G13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'H13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'I13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'J13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'K13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'L13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'M13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'N13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'O13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'P13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'Q13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                
                {'cell_ref': 'R13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': 'C00000', 'bold': True, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'S13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': '92D050', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'T13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': '92D050', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'U13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': 'C00000', 'bold': True, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                
                # {'cell_ref': 'U13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                # {'cell_ref': 'V13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
                
                {'cell_ref': 'V13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': '92D050', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'W13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': '92D050', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'X13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': '92D050', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
                
                # {'cell_ref': 'W13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': 'C00000', 'bold': True, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
                
                # {'cell_ref': 'X13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': '92D050', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
                # {'cell_ref': 'Y13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': '92D050', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},

                # {'cell_ref': 'Z13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': 'C00000', 'bold': True, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                # {'cell_ref': 'Y14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': 'C00000', 'bold': True, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                
                # {'cell_ref': 'S12:V13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': 'C00000', 'bold': True, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'value': "VALOR CUPON YA DESCONTADO EN PRECIO CON DESCUENTO", 'data_type': 'string'},
                ]
            
            promobrid = [
                {'cell_ref': 'I6:L6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': RED, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "PROMOCIÓN BRIDGESTONE Y FIRESTONE", 'data_type': 'string'},
                
                {'cell_ref': 'I7:J7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'FDE9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "CUPONES", 'data_type': 'string'},
                {'cell_ref': 'I8:J8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Desde 1 llanta limitado a 200 por RFC", 'data_type': 'string'},
                {'cell_ref': 'I9:J9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'FDE9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "5% (Consulte medidas participantes)", 'data_type': 'string'},
                
                {'cell_ref': 'K7:L7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'F2DCDB', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "BONO TARJETA", 'data_type': 'string'},
                
                {'cell_ref': 'K8:L8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "Sin bono", 'data_type': 'string'},
                {'cell_ref': 'K9:L9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'F2DCDB', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=IF(K8 = "Por cada 50 mil pesos por mes", "Tarjeta de 2 mil pesos de regalo", IF(K8 = "Por cada 100 mil pesos por mes", "Tarjeta de 5 mil pesos de regalo", IF(K8 = "Por cada 200 mil pesos por mes", "Tarjeta de 12 mil pesos de regalo", "Seleccione Promoción")))""", 'data_type': 'string'},
                                                                                                                                                                                                                                                            
                {'cell_ref': 'I10:L10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "DESCUENTO ACUMULADO", 'data_type': 'string'},
                
                {'cell_ref': 'I11:J11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '$#,##0.00', 'value': f"""=SUMPRODUCT((Q14:Q{num_rows_3} <> "")*(Q14:Q{num_rows_3})*(U14:U{num_rows_3}))""", 'data_type': 'string'},
                {'cell_ref': 'K11:L11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '$#,##0.00', 'value': f"""=SUMPRODUCT((S14:S{num_rows_3} <> "")*(S14:S{num_rows_3})*(U14:U{num_rows_3}))""", 'data_type': 'string'},
                ]

            data_for_sheet5 = [
                {'cell_ref': 'E1', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "", 'data_type': 'string'},
                {'cell_ref': 'A2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'B2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'C2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'D2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'E2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'F2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'G2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'H2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'I2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'J2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'K2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'L2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'M2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'N2', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                ]

            # Formatear las celdas para la hoja 3
            for data in data_for_sheet3:
                self.format_cell(sheet3, **data)
            for data in promobrid:
                self.format_cell(sheet3, **data)
            for data in data_for_sheet5:
                self.format_cell(sheet5, **data)
                
                  
            # Lista de hojas a formatear
            sheets = [sheet3]
            sheets2 = [sheet5]
            # Diccionario que define las columnas y sus formatos
            formats = {
                'string': ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'M'],
                'number': ['A', 'L', 'U'],
                'currency': ['N', 'O', 'P', 'Q', 'R', 'S', 'T', 'V', 'W', 'X'],
            }
            
            formats2 = {
                'string': ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'],
                'number': ['M'],
                'date': ['N'],
            }
            
            #-------- Ocultar columnas ----------------------
            # Seleccionar la hoja que deseas ocultar
            # sheet = wb['P. BRIDGESTONE']
            # Para ocultar la hoja:
            # sheet.sheet_state = 'hidden'
            
            columna_a_ocultar_sheet3 = ['A', 'N', 'O', 'V', 'W', 'X']
            
            # Itera sobre cada hoja
            for sheet in sheets:
                start_row = 13
                end_row = num_rows_3
                start_col = 'A'
                end_col = 'X'
                # Itera sobre cada tipo de formato y sus respectivas columnas
                for format_type, columns in formats.items():
                    for column in columns:
                        self.format_column(sheet, column, format_type)
                        #-----------Ocultar cuadricula---------------------------
                        self.color_cells_based_on_condition_sheet3(sheet)
                        sheet.sheet_view.showGridLines = False
                        sheet.freeze_panes = 'A14'
                for columna_sheet3 in columna_a_ocultar_sheet3:
                    sheet.column_dimensions[columna_sheet3].hidden = True

                # Definir el borde que se aplicará a las celdas
                thin_border = Border(
                    left=Side(style='thin', color="A6A6A6"),
                    right=Side(style='thin', color="A6A6A6"),
                    top=Side(style='thin', color="A6A6A6"),
                    bottom=Side(style='thin', color="A6A6A6")
                )
                for row in sheet.iter_rows(min_row=start_row, max_row=end_row, min_col=column_index_from_string(start_col), max_col=column_index_from_string(end_col)):
                    for cell in row:
                        cell.border = thin_border
                        
            for sheet in sheets2:
                start_row = 2
                end_row = num_rows_4
                start_col = 'A'
                end_col = 'N'
                # Itera sobre cada tipo de formato y sus respectivas columnas
                for format_type, columns in formats2.items():
                    for column in columns:
                        self.format_column(sheet, column, format_type)
                        #-----------Ocultar cuadricula---------------------------
                        sheet.sheet_view.showGridLines = False
                        sheet.freeze_panes = 'A1'
                # Definir el borde que se aplicará a las celdas
                thin_border = Border(
                    left=Side(style='thin', color="A6A6A6"),
                    right=Side(style='thin', color="A6A6A6"),
                    top=Side(style='thin', color="A6A6A6"),
                    bottom=Side(style='thin', color="A6A6A6")
                )
                for row in sheet.iter_rows(min_row=start_row, max_row=end_row, min_col=column_index_from_string(start_col), max_col=column_index_from_string(end_col)):
                    for cell in row:
                        cell.border = thin_border


        # Ajustar el ancho de las columnas en todas las hojas basándose en la fila 1 (por ejemplo)
        for sheet_name in wb.sheetnames:
            row_num = 13
            desired_height = 40  # Altura deseada en Columnas
            desired_height_2 = 50  # Altura deseada en ENCABEZADO
            if sheet_name in ['Transitos']:
                row_num = 2
                ws = wb[sheet_name]
                ws.row_dimensions[row_num].height = desired_height
            else:
                ws = wb[sheet_name]
                ws.row_dimensions[row_num].height = desired_height
                ws.row_dimensions[row_num - 12].height = desired_height_2
                
                # start_col = ['E', 'O', 'U', 'X']
                # thin_border = Border(
                #                 right=Side(style='thick', color=BLACK),
                # )
                # for col in start_col:
                #     if sheet_name == 'Precios Con Iva' and col == 'X':
                #         continue
                #     for row in ws.iter_rows(min_row=1, max_row=6, min_col=column_index_from_string(col), max_col=column_index_from_string(col)):
                #         for cell in row:
                #             cell.border = thin_border

            if sheet_name == 'P. BRIDGESTONE':
                col = 23  # columna W
            elif sheet_name == 'Precios Con Iva':
                col = 21  # columna U
            else:
                col = None

            if col is not None:
                for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=col, max_col=col):
                    for cell in row:
                        cell.protection = Protection(locked=False)
            # self.auto_adjust_column_widths(ws, row_num)
            
            # Calcular la cantidad de columnas que tiene la hoja
            max_col = ws.max_column

            # Asignar ancho aproximado de 151 píxeles
            ancho_excel = 117 / 7  # ≈21.5

            for col_idx in range(1, max_col + 1):
                col_letter = get_column_letter(col_idx)
                ws.column_dimensions[col_letter].width = ancho_excel
            
            # #FORMATO CONDICIONAL
            # yellow_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
            # # Crear la regla condicional con una fórmula
            # rule1 = FormulaRule(formula=["I13=3%"], stopIfTrue=False, fill=yellow_fill)
            # rule2 = FormulaRule(formula=["I12=4%"], stopIfTrue=False, fill=yellow_fill)
            # rule3 = FormulaRule(formula=["I11=5%"], stopIfTrue=False, fill=yellow_fill)
            # # Aplicar la regla a la celda J11
            # ws.conditional_formatting.add("J11:M11", rule3)
            # ws.conditional_formatting.add("J12:M12", rule2)
            # ws.conditional_formatting.add("J13:M13", rule1)
            
        propiedades = wb.properties
        # Crear un buffer en memoria
        excel_bytes_io = io.BytesIO()

        # Guardar el archivo en el buffer
        wb.save(excel_bytes_io)

        # Obtener los bytes del archivo y codificarlo en base64
        excel_bytes_io.seek(0)  # Rewind the buffer to the beginning before reading it
        excel_base64 = base64.b64encode(excel_bytes_io.read()).decode("utf-8")

        # Si deseas devolver el archivo como base64, puedes hacerlo:
        if return_base_64:
            return excel_base64
        
        self.write({'file_data': excel_base64})
        
        action = {
            'name': 'Lista de Precios',
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model=inv_promo.lista_precios_wizard&id={self.id}&field=file_data&download=true&filename=VTA-FO-03 Lista de Precios {date.today()}.xlsx',
            'target': '_blank',
            }
        return action
    
    def auto_adjust_column_widths(self, ws, row_num):
        row = ws[row_num]
        for cell in row:
            column_index = cell.column
            column_letter = get_column_letter(column_index)
            max_length = len(str(cell.value)) if cell.value else 0
            adjusted_width = max_length + 5
            ws.column_dimensions[column_letter].width = adjusted_width

    def download_report(self):
        if self.partner_id:
            return self.sudo().get_xlsx_report(self.partner_id)
        elif not self.partner_id and self.volume_profile and self.financial_profile and self.logistic_profile:
            return self.sudo().get_xlsx_report(self.partner_id)