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

codes=[ 
       22568, 22067, 22569, 22079, 22078, 22305, 22085, 22812, 22682, 22164, 22260, 22574, 22075, 22074, 22356, 51533, 22086, 22549, 22097, 22462, 22589, 
       22106, 22118, 22114, 58465, 22113, 22726, 22576, 22536, 22518, 22140, 22139, 22365, 22158, 22325, 50301, 22793, 22295, 22318, 22252, 22693, 59744, 
       22419, 59267, 22125, 22653, 22129, 51129, 22524, 22133, 22717, 48697, 22683, 22712, 51666, 22786, 49072, 22590, 22603, 22822, 22804, 22605, 22599, 
       22864, 50300, 22161, 22585, 22823, 22162, 22814, 22824, 22821, 57693, 22626, 22652, 22461, 22811, 22196, 22853, 22810, 22494, 22797, 22854, 22807, 
       59868, 61087, 22836, 22516, 22837, 22233, 22733, 22301, 22799, 22760, 22759, 22782, 22561, 22381, 22258, 22259, 49875, 57249, 22684, 22711, 51715, 
       22818, 22600, 22155, 48878, 22846, 59268, 22628, 58933, 49876, 58485, 61073, 22175, 61076, 61070, 48953, 22625, 22422, 22474, 22170, 22802, 22630, 
       58466, 22284, 59867, 22677, 61088, 22806, 22795, 60952, 59271, 22727, 59869, 22737, 59255, 61081, 22856, 22805, 22281, 22758, 22790, 22832, 22857, 
       59870, 22550, 22778, 22757, 22572, 22355, 22798, 61085, 22742, 22741, 58459, 22785, 22792, 48877, 22692, 22816, 22547, 61072, 48930, 48951, 59252, 
       48952, 22581, 22604, 22675, 59242, 59253, 61082, 22633, 51858, 22616, 48954, 61086, 59260, 22288, 22686, 51855, 22809, 22754, 22848, 22829, 51856, 
       57251, 22861, 59748, 22448, 22838, 22839, 59258, 22351, 22466, 22840, 22841, 22825, 22762, 61084, 59259, 22715, 22756, 22755, 22763, 22753, 22562, 
       59251, 22800, 59745, 22637, 59243, 22858, 51659, 61074, 59254, 61075, 22777, 22862, 51859, 22803, 59270, 22817, 22613, 59865, 61077, 58828, 22850, 
       61071, 59256, 59257, 51130, 59747, 22584, 22705, 22704, 22859, 22689, 58462, 22860, 22833, 59746, 22852, 22826, 22748, 49622, 58464, 22796, 22842, 
       22827, 61080, 22749, 57226, 22843, 22783, 22694, 22609, 22780, 22680, 22681, 51857, 59749, 22752, 22808, 59871
       ]

codes2=[]

codes3=[]

codes_pirelli = [61691, 48712, 51521, 51336, 49018, 29415, 48713, 49637, 53019, 60987, 60995, 48626, 60991, 28800, 48995, 29435, 62643, 62910, 29349, 
                 29901, 61692, 60986, 60997, 49060, 60988
                ]

codes_goodyear = [57246, 58473, 50147, 57522, 19580, 50202, 58488, 59098, 57684, 62649, 9810, 50389, 59245, 61007, 48980
                ]

codes_kumho = [ 62397, 59762, 51451, 51449, 62613
               ]

tupla10= [ 
        (22086, 177.21), (22549, 186.07), (22113, 164.23), (22356, 165.76), (22712, 224.01), (22118, 182.71), (22516, 292.6), 
        (22114, 164.23), (49072, 211.69), (22683, 199.84), (22419, 176.18), (22075, 175.36), (22726, 170.22)
]

tupla5= [
        (22518, 131.26), (22260, 132.32), (22589, 98.19), (22106, 85.02), (22170, 123.64), (22804, 154.29), (48697, 92.56), (51129, 87.93), 
        (22155, 123.4), (22785, 153.48), (22295, 159.59), (51857, 368.52), (48954, 121.23), (22604, 157.37), (22814, 102.6), (22605, 142.29), 
        (58485, 106.62), (22677, 207.23), (22524, 89.98), (22162, 124.04), (22422, 124.48), (59242, 147.01), (22816, 123.44), (22777, 189.94), 
        (22633, 152.99), (59868, 156.62), (22752, 285.62), (22288, 186.72), (22826, 189.37), (22625, 116.75), (22823, 109.64), (22628, 113.3), 
        (22140, 96.66), (22067, 82.43), (48878, 123.4), (22711, 103.93), (22684, 106.85), (22822, 146.18), (58933, 117.14)
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
        else:
            financial = self.partner_id.get_row_values_volumen(self.volume_profile)
            logistic = self.partner_id.get_row_values_logistico(self.logistic_profile)    
        
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
        
        return financial_percentages, logistic_percentages
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
            cell = sheet.cell(row=14, column=col_idx)
            cell.value = header
            cell.font = Font(bold=True)

        for row_idx, row_data in enumerate(table_data, start=15):
            for col_idx, header in enumerate(headers, start=1):
                if header == "Precio Regular":
                    sheet.cell(row=row_idx, column=col_idx).value = f'=MIN(P{row_idx}:R{row_idx})'     
                    #=IF(IF(MIN(Q{row_idx}:T{row_idx}) > 0, MIN(Q{row_idx}:T{row_idx}), "") = S{row_idx}, S{row_idx}, IF(MIN(Q{row_idx}:T{row_idx}) > 0, MIN(Q{row_idx}:T{row_idx}), "") * (1-IF(ISNUMBER($U$13), $U$13, 0)))
                elif header == "PRECIO CON DESCUENTOS":
                    sheet.cell(row=row_idx, column=col_idx).value = f'''=S{row_idx} - 
                                                                        (IF(OR($A$7=1,$A$7=150,$A$7=350,$A$7=600), ((S{row_idx}*$D$7) + (S{row_idx}*$E$7) + (S{row_idx}*$F$7)), 0)) - 
                                                                        (S{row_idx} * IF(AND(ISNUMBER(IFERROR(FIND(F{row_idx}, UPPER($H$6)), "")), V{row_idx} = "SI"), $H$8, 0)) - 
                                                                        (S{row_idx} * IF(ISNUMBER(IFERROR(FIND(F{row_idx}, UPPER($I$6)), "")), $I$8, 0)) - 
                                                                        (S{row_idx} * IF(AND(ISNUMBER(IFERROR(FIND(F{row_idx}, UPPER($J$6)), "")), V{row_idx} = "SI"), $J$8, 0)) - 
                                                                        (S{row_idx} * IF(ISNUMBER(IFERROR(FIND(F{row_idx}, UPPER($K$6)), "")), $K$8, 0)) - 
                                                                        (S{row_idx} * IF(ISNUMBER(IFERROR(FIND(F{row_idx}, UPPER($L$6)), "")), $L$8, 0)) - 
                                                                        (S{row_idx} * IF(ISNUMBER(IFERROR(FIND(F{row_idx}, UPPER($M$6)), "")), $M$8, 0)) - 
                                                                        (S{row_idx} * IF(ISNUMBER(IFERROR(FIND(F{row_idx}, UPPER($N$6)), "")), $N$8, 0)) - 
                                                                        (S{row_idx} * IF(AND(ISNUMBER(IFERROR(FIND(F{row_idx}, UPPER($P$6)), "")), V{row_idx} = "SI"), $P$8, 0))'''
                else:
                     sheet.cell(row=row_idx, column=col_idx).value = row_data.get(header, "")

        end_col_letter = get_column_letter(len(headers))
        table_ref = f"A14:{end_col_letter}{num_rows + 14}"
        table = Table(displayName=table_name, ref=table_ref)
        style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False,
                               showLastColumn=False, showRowStripes=True, showColumnStripes=True)
        table.tableStyleInfo = style
        sheet.add_table(table)
        return num_rows + 14, len(headers)  # Retorna el número de filas y columnas
####################################################################################################
    def insert_table_sheet3(self, sheet, table_data, table_name):
        headers = list(table_data[0].keys()) if table_data else []
        num_rows = len(table_data)
        if num_rows == 0 or not headers:
            return  # No hay datos o encabezados, salir sin crear la tabla

        for col_idx, header in enumerate(headers, start=1):
            cell = sheet.cell(row=14, column=col_idx)
            cell.value = header
            cell.font = Font(bold=True)

        for row_idx, row_data in enumerate(table_data, start=15):
            for col_idx, header in enumerate(headers, start=1):
                if header == "Precio Regular":
                    sheet.cell(row=row_idx, column=col_idx).value = f'=MIN(Q{row_idx}:S{row_idx})'
                elif header == "PRECIO CON DESCUENTOS":
                    sheet.cell(row=row_idx, column=col_idx).value = f'''=V{row_idx} - (IF(OR($A$7=1,$A$7=150,$A$7=350,$A$7=600), ((V{row_idx}*$D$7) + (V{row_idx}*$E$7) + (V{row_idx}*$F$7)), 0)) - T{row_idx}- U{row_idx}'''
                elif header == "PROMO BS":
                    sheet.cell(row=row_idx, column=col_idx).value = f'''=IF(AND(P{row_idx} = "SI", OR(G{row_idx} = 14,G{row_idx} = 15, G{row_idx} = 16, G{row_idx} = 17)), (V{row_idx}*$K$8), IF(AND(P{row_idx} = "SI", OR(G{row_idx} = 18, G{row_idx} = 19, G{row_idx} = 20, G{row_idx} = 21, G{row_idx} = 22)), (V{row_idx}*$P$8), 0))'''
                elif header == "FACTURACIÓN":
                    sheet.cell(row=row_idx, column=col_idx).value = f'=IF(X{row_idx} = "", "", X{row_idx}*V{row_idx})'   
                else:
                     sheet.cell(row=row_idx, column=col_idx).value = row_data.get(header, "")

        end_col_letter = get_column_letter(len(headers))
        table_ref = f"A14:{end_col_letter}{num_rows + 14}"
        table = Table(displayName=table_name, ref=table_ref)
        style = TableStyleInfo(name="TableStyleMedium9", showFirstColumn=False,
                               showLastColumn=False, showRowStripes=True, showColumnStripes=True)
        table.tableStyleInfo = style
        sheet.add_table(table)
        return num_rows + 14, len(headers)  # Retorna el número de filas y columnas
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
        for row in sheet.iter_rows(min_col=col_idx, max_col=col_idx, min_row=15):
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
        
        for row in sheet.iter_rows(min_row=15):  # Start from row 2 to skip header
            outlet_cell = row[outlet_col_idx - 1]  # Adjust index to zero-based
            t4_cell = row[t4_col_idx - 1]
            tier4_cell = row[tier4_col_idx - 1]
            # Example condition: Color 'Outlet' column yellow if cell value is not empty
            if isinstance(outlet_cell.value, (int, float)) and outlet_cell.value > 0:
                for col_idx in range(column_index_from_string(outlet_start_column) - 1, column_index_from_string(outlet_end_column)):
                    cell = row[col_idx]
                    cell.fill = PatternFill(start_color='EBEBEB', end_color='EBEBEB', fill_type='solid')
                outlet_cell.fill = PatternFill(start_color='EBEBEB', end_color='EBEBEB', fill_type='solid')
                
            # if tier4_cell.value in ['APTANY', 'DOUBLESTAR']:
            #     t4_cell.fill = PatternFill(start_color='DDE5F2', end_color='DDE5F2', fill_type='solid')
                    
        # for row in sheet.iter_rows(min_row=15):
        #     milestar_cell = row[milestar_col_idx - 1]
        #     for col in range(ord(start_column), ord(end_column) + 1):
        #         if milestar_cell.value in ['ONYX']:
        #             cell = row[col - ord(start_column)]
        #             cell.fill = PatternFill(start_color='EBF1DE', end_color='EBF1DE', fill_type='solid')
        #         elif milestar_cell.value in ['DRIVEFORCE']:
        #             cell = row[col - ord(start_column)]
        #             cell.fill = PatternFill(start_color='92CDDC', end_color='92CDDC', fill_type='solid')
                    
        for row in sheet.iter_rows(min_row=15):
            cupon_cell = row[column_index_from_string(id_col_idx) - 1]
            if cupon_cell.value in codes_pirelli:
                for col_idx in range(column_index_from_string(start_column) - 1, column_index_from_string(end_column)):
                    cell = row[col_idx]
                    cell.fill = PatternFill(start_color=YELLOW, end_color=YELLOW, fill_type='solid')
            elif cupon_cell.value in codes_goodyear:
                for col_idx in range(column_index_from_string(start_column) - 1, column_index_from_string(end_column)):
                    cell = row[col_idx]
                    cell.fill = PatternFill(start_color='DCE6F1', end_color='DCE6F1', fill_type='solid')
            elif cupon_cell.value in codes_kumho:
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
        start_column = 'S'
        end_column = 'U'
        cupones = 'W'
        outlet_col_idx = column_index_from_string('R')
        outlet_start_column = 'V'
        outlet_end_column = 'X'
        
        for row in sheet.iter_rows(min_row=15):  # Start from row 2 to skip header
            outlet_cell = row[outlet_col_idx - 1]  # Adjust index to zero-based
            # Example condition: Color 'Outlet' column yellow if cell value is not empty
            if isinstance(outlet_cell.value, (int, float)) and outlet_cell.value > 0:
                for col_idx in range(column_index_from_string(outlet_start_column) - 1, column_index_from_string(outlet_end_column)):
                    cell = row[col_idx]
                    cell.fill = PatternFill(start_color='EBEBEB', end_color='EBEBEB', fill_type='solid')
                outlet_cell.fill = PatternFill(start_color='EBEBEB', end_color='EBEBEB', fill_type='solid')
                
        for row in sheet.iter_rows(min_row=15):
            cupon_cell = row[column_index_from_string(ids_in_codes_brig) - 1]
            if cupon_cell.value in codes:
                for col_idx in range(column_index_from_string(start_column) - 1, column_index_from_string(end_column)):
                    cell = row[col_idx]
                    cell.fill = PatternFill(start_color='FDE9D9', end_color='FDE9D9', fill_type='solid')
                for col_idx in range(column_index_from_string(ids_in_codes_brig) - 1, column_index_from_string(codes_brige)):
                    cell = row[col_idx]
                    cell.fill = PatternFill(start_color='FDE9D9', end_color='FDE9D9', fill_type='solid')
                    
        for row in sheet.iter_rows(min_row=15):
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
            # Convertir la lista de códigos en una tupla para SQL
            codes_tuple = tuple(codes)
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
            # Convertir la lista de códigos en una tupla para SQL
            codes_tuple = tuple(codes)
            
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
                    'DOT': obj.lot_name or '' or None,
                    'Inv.': obj.inventario_str or None,
                    #'Cantidad Disponible': obj.available,
                    #'Trans.': (obj.transito_str + obj.backorder_str) or None,
                    #'Arribo': obj.fecha_aprox or None,
                    })
                if self.partner_id:
                    if obj.product_id.id in codes:
                        data_dict.update({'PARTICIPA': 'SI'})
                    else:
                        data_dict.update({'PARTICIPA': 'NO'})
                else:
                    if obj.product_id.id in codes:
                        data_dict.update({'PARTICIPA': 'SI'})
                    else:
                        data_dict.update({'PARTICIPA': 'NO'})      
                data_list.append(data_dict)            
                data_dict.update({
                    'Mayoreo': (obj.volumen * 1.16),
                    'Outlet': obj.outlet * 1.16,
                    'Promo Dot': obj.promo_dot * 1.16,
                    'PROMO BS': ""
                    })
                if self.partner_id:
                    cupones_dict5 = {t[0]: t[1] for t in tupla5}
                    cupones_dict10 = {t[0]: t[1] for t in tupla10}
                    if obj.product_id.id in cupones_dict5:
                        data_dict.update({'Cupones': cupones_dict5[obj.product_id.id]})
                    elif obj.product_id.id in cupones_dict10:
                        data_dict.update({'Cupones': cupones_dict10[obj.product_id.id]})
                    else:
                        data_dict.update({'Cupones': ''})
                data_dict.update({
                    'Precio Regular': "",
                    'PRECIO CON DESCUENTOS': "",
                    'PIEZAS': "",
                    'FACTURACIÓN': ""
                    })
                
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
                if obj.product_id.id in codes_kumho + codes_goodyear + codes_pirelli:
                    data_dict.update({'PARTICIPA': 'SI'})
                else:
                    data_dict.update({'PARTICIPA': 'NO'})
            else:
                if obj.product_id.id in codes_kumho:
                    data_dict.update({'PARTICIPA': 'SI'})
                else:
                    data_dict.update({'PARTICIPA': 'NO'})
        return data_list

    def set_frames(self, sheet):        
        img_path = "/mnt/extra-addons/inv_promo/wizard/models/Encabezado.png"    
        img = Image(img_path)
        img.height = 58.5  # Establece la altura en píxeles calculados
        img.width = 1100   # Establece el ancho en píxeles calculados                       
        # Insertar la imagen en la hoja
        sheet.add_image(img, 'A1')
        # Crear un comentario
        comentario = Comment("Aplica por entrega en una misma dirección", "Ztyres")
        # Asignar el comentario a la celda
        sheet["C6"].comment = comentario
        
    def set_brief(self, sheet):        
        #img_path = "/mnt/extra-addons/inv_promo/wizard/models/Encabezado.png"
        img_path = "/mnt/extra-addons/inv_promo/wizard/models/Brief.jpg"
        img = Image(img_path)
        #img.height = 708  # Establece la altura en píxeles calculados
        #img.width = 1196   # Establece el ancho en píxeles calculados                       
        # Insertar la imagen en la hoja
        sheet.add_image(img, 'A1')

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
        llantas_x_mes = ['1', '150', '350', '600']
        
        #volume_percent = ['0%','2%','3%']
        logistic_percent = ['0%','2%','4%']
        financial_percent = ['0%','2%','3%']
        
        #bs_percentR14 = ['0%', '5%', '8%']
        #bs_percentR18 = ['0%', '8%']
        bs_percentR14 = ['$1 a $46¸399', '$46¸400 a $579¸999', 'Más de $580¸000']
        bs_percentR18 = ['$1 a $46¸399', 'Más de $46¸400']
         
        combo_data_sheet1 = [
            #{'cell_ref': 'D7', 'values': volume_percent},
            {'cell_ref': 'E7', 'values': logistic_percent},
            {'cell_ref': 'F7', 'values': financial_percent},
            
            {'cell_ref': 'A7', 'values': llantas_x_mes},
        ]
        
        combo_data_sheet3 = [
            {'cell_ref': 'E7', 'values': logistic_percent},
            {'cell_ref': 'F7', 'values': financial_percent},
            
            {'cell_ref': 'A7', 'values': llantas_x_mes},
            
            {'cell_ref': 'I8', 'values': bs_percentR14},
            {'cell_ref': 'M8', 'values': bs_percentR18}
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
                
        sheet1.protection.sheet = True
        sheet1.protection.password = "Top$ecret"  # opcional
        sheet1.protection.pivotTables = False
        sheet1.protection.autoFilter = False
        sheet1.protection.sort = True  
        sheet1.protection.enable()
        
        self.set_combos(sheet1, combo_data_sheet1)

        self.set_frames(sheet1)
        
        sheet1.sheet_properties.tabColor = WHITE

        self.set_white_fill(sheet1, 'A1', num_rows_1, num_cols_1)
        values = '{"DOUBLESTAR","DELINTE","FIREMAX","APTANY"}'
        
         # Definir los datos para las celdas
        data_for_sheet1 = [
            {'cell_ref': 'A5:C6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "LLANTAS AL MES", 'data_type': 'string'},
            {'cell_ref': 'D5:F5', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': RED, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "DESCUENTOS  SEGÚN POLÍTICA COMERCIAL", 'data_type': 'string'},
            {'cell_ref': 'D6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': '595959', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Volumen", 'data_type': 'string'},
            {'cell_ref': 'E6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'EBEBEB', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Logístico", 'data_type': 'string'},
            {'cell_ref': 'F6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': '595959', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Financiero", 'data_type': 'string'},
            
            {'cell_ref': 'A7:C7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': 1},
            {'cell_ref': 'D7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': f"""=IF(A7=1,0%,IF(A7=150,1%,IF(A7=350,2%,IF(A7=600,3%, 0%))))"""},
            {'cell_ref': 'E7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
            {'cell_ref': 'F7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': '00B050', 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
            
            {'cell_ref': 'A8:C8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "TOTAL LLANTAS", 'data_type': 'string'},
            {'cell_ref': 'A9:C10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=SUM(U15:U{num_rows_1})+SUM('P. BRIDGESTONE'!X15:X{num_rows_1})"""},
            
            {'cell_ref': 'D8:F8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=IF(E7=0%, "Sin descuento de 1 a 99 llantas por envío", IF(E7=2%,"Descuento Logístico: Mín. 100 llantas x envío", IF(E7=4%, "Descuento Logístico: Mín. 300 llantas x envío", "Sin descuento de 1 a 99 llantas por envío")))"""},
            {'cell_ref': 'D9:F9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'EBEBEB', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Códigos con Super descuento", 'data_type': 'string'},
            {'cell_ref': 'D10:F10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': '00B050', 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Financiero aplica pagando en tiempo sus facturas", 'data_type': 'string'},
            
            {'cell_ref': 'H5:T5', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': RED, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "DESCUENTO REFLEJADO EN LA COLUMNA PRECIO CON DESCUENTOS", 'data_type': 'string'},
            {'cell_ref': 'H6:H7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'DCE6F1', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Goodyear", 'data_type': 'string'},
            {'cell_ref': 'I6:I7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Milestar / Venom", 'data_type': 'string'},
            {'cell_ref': 'J6:J7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': YELLOW, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Pirelli", 'data_type': 'string'},
            {'cell_ref': 'K6:K7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Onyx", 'data_type': 'string'},
            {'cell_ref': 'L6:L7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Federal", 'data_type': 'string'},
            {'cell_ref': 'M6:M7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Driveforce", 'data_type': 'string'},
            {'cell_ref': 'N6:O7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Aptany/Delinte/ DoubleStar/Firemax", 'data_type': 'string'},
            {'cell_ref': 'P6:T7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'FDE9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Kumho", 'data_type': 'string'},
            
            {'cell_ref': 'H8:H9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '0%', 'value': f"""=IF(A7 = 1, 0%, IF(A7 = 150, 5%, IF(A7 = 350, 6%, IF(A7 = 600, 6%, 0%))))"""},
            {'cell_ref': 'I8:I9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '0%', 'value': f"""=IF(A7 = 1, 1%, IF(A7 = 150, 3%, IF(A7 = 350, 5%, IF(A7 = 600, 5%, 0%))))"""},
            {'cell_ref': 'J8:J9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '0%', 'value': f"""=IF(A7 = 1, 0%, IF(A7 = 150, 3%, IF(A7 = 350, 4%, IF( A7 = 600, 4%, 0%))))"""},
            {'cell_ref': 'K8:K9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '0%', 'value': f"""=IF(A7 = 1, 8%, IF(A7 = 150, 10%, IF(A7 = 350, 12%, IF(A7 = 600, 12%, 0%))))"""},
            {'cell_ref': 'L8:L9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '0%', 'value': f"""=IF(A7 = 1, 2%, IF(A7 = 150, 4%, IF(A7 = 350, 4%, IF(A7 = 600, 4%, 0%))))"""},
            {'cell_ref': 'M8:M9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '0%', 'value': f"""=IF(A7 = 1, 7%, IF(A7 = 150, 10%, IF(A7 = 350, 12%, IF(A7 = 600, 12%, 0%))))"""},
            {'cell_ref': 'N8:O9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '0%', 'value': f"""=IF(A7 = 1, 1%, IF(A7 = 150, 2%, IF(A7 = 350, 3%, IF(A7 = 600, 3%, 0%))))"""},
            {'cell_ref': 'P8:T9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '0%', 'value': f"""=IF(A7 = 1, 0%, IF(A7 = 150, 4%, IF(A7 = 350, 6%, IF(A7 = 600, 6%, 0%))))"""},
            
            {'cell_ref': 'O3', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': None, 'align': 'right', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'value': "** Goodyear / Kumho / Pirelli - Consulte Códigos Participantes.", 'data_type': 'string'},
                
            {'cell_ref': 'K1:O2', 'font_name': 'Calibri', 'font_size': 18, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': None, 'align': 'right', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'value': "INVENTARIO Y PRECIOS VIGENTES", 'data_type': 'string'},
            {'cell_ref': 'O3', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': None, 'align': 'right', 'top_align': 'center', 'wrap_text': True, 'num_format': 'DD/MM/YYYY', 'value': date.today(), 'data_type': 'string'},
            
            {'cell_ref': 'A14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'B14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'C14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'D14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'E14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'F14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'G14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'H14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'I14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'J14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'K14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'L14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'M14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'N14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'O14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'P14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'Q14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': '808080', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'S14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'T14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': RED, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'U14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'V14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
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
        
        columna_a_ocultar_sheet1 = ['A', 'C', 'G', 'N', 'P', 'Q', 'R', 'S', 'V']
        
        for columna_sheet1 in columna_a_ocultar_sheet1:
            sheet1.column_dimensions[columna_sheet1].hidden = True
        
        # Formatear las celdas para la hoja 1
        for data in data_for_sheet1:
            self.format_cell(sheet1, **data)
            
        self.color_cells_based_on_condition(sheet1)
        sheet1.sheet_view.showGridLines = False
        sheet1.freeze_panes = 'A15'
        
        start_row = 14
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
                            print ("Celda desbloqueada:", cell.coordinate)
                        else:
                            cell.protection = Protection(locked=True)
                            
                        
                # Desbloquear las celdas del rango B2:B4 (por ejemplo)
                for row in hoja.iter_rows(min_row=1, max_row=num_rows_3, min_col=26, max_col=30):
                    for cell in row:
                        cell.protection = Protection(locked=False)
                    
            for hoja in hojas_a_bloquear:
                hoja.protection.sheet = True
                hoja.protection.password = "Top$ecret"  # opcional
                hoja.protection.pivotTables = False
                hoja.protection.autoFilter = False
                hoja.protection.sort = True  
                hoja.protection.enable()
            
            self.set_frames(sheet3)
            self.set_brief(sheet4)
            sheet3.sheet_properties.tabColor = 'E6B8B8'
            sheet4.sheet_properties.tabColor = 'FFFF00'
            sheet5.sheet_properties.tabColor = '92D050'
            self.set_white_fill(sheet3, 'A1', num_rows_3, num_cols_3)
            self.set_white_fill(sheet5, 'A1', num_rows_4, num_cols_4)
            self.set_combos(sheet3, combo_data_sheet3)

            data_for_sheet3 = [
                {'cell_ref': 'K1:O2', 'font_name': 'Calibri', 'font_size': 18, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': None, 'align': 'right', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'value': "INVENTARIO Y PRECIOS VIGENTES", 'data_type': 'string'},
                {'cell_ref': 'O3', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': None, 'align': 'right', 'top_align': 'center', 'wrap_text': True, 'num_format': 'DD/MM/YYYY', 'value': date.today(), 'data_type': 'string'},
            
                {'cell_ref': 'A14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'B14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'C14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'D14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'E14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'F14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'G14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'H14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'I14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'J14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'K14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'L14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'M14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'N14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'O14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'P14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'Q14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': '808080', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'S14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': RED, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'T14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'U14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'V14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'W14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': 'C00000', 'bold': True, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'X14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': 'C00000', 'bold': True, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                #{'cell_ref': 'Y14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': 'C00000', 'bold': True, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                
                #{'cell_ref': 'S12:V13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': 'C00000', 'bold': True, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'value': "VALOR CUPON YA DESCONTADO EN PRECIO CON DESCUENTO", 'data_type': 'string'},
                ]
            
            promobrid = [
                {'cell_ref': 'A5:C6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "LLANTAS AL MES", 'data_type': 'string'},
                {'cell_ref': 'D5:F5', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': RED, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "DESCUENTOS  SEGÚN POLÍTICA COMERCIAL", 'data_type': 'string'},
                {'cell_ref': 'D6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': '595959', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Volumen", 'data_type': 'string'},
                {'cell_ref': 'E6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'EBEBEB', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Logístico", 'data_type': 'string'},
                {'cell_ref': 'F6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': '595959', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Financiero", 'data_type': 'string'},
                
                {'cell_ref': 'A7:C7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': 1},
                {'cell_ref': 'D7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': f"""=IF(A7=1,0%,IF(A7=150,1%,IF(A7=350,2%,IF(A7=600,3%, 0%))))"""},
                {'cell_ref': 'E7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
                {'cell_ref': 'F7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': '00B050', 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
                
                {'cell_ref': 'A8:C8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "TOTAL LLANTAS", 'data_type': 'string'},
                {'cell_ref': 'A9:C10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=SUM(X15:X{num_rows_3})+SUM('Precios Con Iva'!U15:U{num_rows_1})"""},
                
                {'cell_ref': 'D8:F8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=IF(E7=0%, "Sin descuento de 1 a 99 llantas por envío", IF(E7=2%,"Descuento Logístico: Mín. 100 llantas x envío", IF(E7=4%, "Descuento Logístico: Mín. 300 llantas x envío", "Sin descuento de 1 a 99 llantas por envío")))"""},
                {'cell_ref': 'D9:F9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'EBEBEB', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Códigos con Super descuento", 'data_type': 'string'},
                {'cell_ref': 'D10:F10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': '00B050', 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Financiero aplica pagando en tiempo sus facturas", 'data_type': 'string'},
                
                {'cell_ref': 'I5:W5', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': RED, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "P R O M O C I Ó N        M A Y O R E O    B S", 'data_type': 'string'},
                {'cell_ref': 'I6:L6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': '404040', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "RIN 13 A RIN 16", 'data_type': 'string'},
                {'cell_ref': 'M6:W6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': '404040', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "RIN 17 EN ADELANTE", 'data_type': 'string'},
                {'cell_ref': 'I7:J7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "FACTURACIÓN REQUERIDA", 'data_type': 'string'},
                {'cell_ref': 'K7:L7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': RED, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "DESCUENTO REFLEJADO EN PRECIO CON DESCUENTOS", 'data_type': 'string'},
                {'cell_ref': 'M7:O7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "FACTURACIÓN REQUERIDA", 'data_type': 'string'},
                {'cell_ref': 'P7:W7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': RED, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "DESCUENTO REFLEJADO EN PRECIO CON DESCUENTOS", 'data_type': 'string'},
                
                {'cell_ref': 'I8:J8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': '$1 a $46¸399', 'data_type': 'string'},
                {'cell_ref': 'K8:L8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': f"""=IF(I8 = "$1 a $46¸399", 0%, IF(I8 = "$46¸400 a $579¸999", 5%, IF(I8 = "Más de $580¸000", 8%, 0%)))"""},
                {'cell_ref': 'M8:O8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': '$1 a $46¸399', 'data_type': 'string'},
                {'cell_ref': 'P8:W8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': f"""=IF(M8 = "$1 a $46¸399", 0%, IF(M8 = "Más de $46¸400", 8%, 0%))"""},
                
                {'cell_ref': 'I9:L9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "FACTURACIÓN ACUMULADA RIN 13 A RIN 16", 'data_type': 'string'},
                {'cell_ref': 'M9:W9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "FACTURACIÓN ACUMULADA RIN 17 EN ADELANTE", 'data_type': 'string'},
                
                {'cell_ref': 'I10:L10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '$#,##0.00', 'value': f"""=SUM(SUMIFS(Y15:Y{num_rows_3}, G15:G{num_rows_3}, {{13, 14, 15, 16}}, P15:P{num_rows_3}, "SI"))""", 'data_type': 'string'},
                {'cell_ref': 'M10:W10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '$#,##0.00', 'value': f"""=SUM(SUMIFS(Y15:Y{num_rows_3}, G15:G{num_rows_3}, {{17, 18, 19, 20, 21, 22}}, P15:P{num_rows_3}, "SI"))""", 'data_type': 'string'},
                
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
                'string': ['B', 'C', 'D', 'E', 'F', 'H', 'I', 'J', 'K', 'L', 'M', 'O', 'P'],
                'number': ['A', 'X'],
                'currency': ['Q', 'R', 'S', 'T', 'U', 'V', 'W', 'Y'],
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
            
            columna_a_ocultar_sheet3 = ['A', 'C', 'G', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'Y']
            
            # Itera sobre cada hoja
            for sheet in sheets:
                start_row = 14
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
                        sheet.freeze_panes = 'A15'
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
        row_num = 14
        desired_height = 40  # Altura deseada en puntos
        
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]

            ws.row_dimensions[row_num].height = desired_height

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
            'url': f'/web/content/?model=inv_promo.lista_precios_wizard&id={self.id}&field=file_data&download=true&filename={self.partner_id.name or "Lista de Precios M"}.xlsx',
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