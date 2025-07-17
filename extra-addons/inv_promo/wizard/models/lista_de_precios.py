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
from pytz import timezone
import openpyxl
import base64
import io

codes=[22088, 22137, 22067, 22569, 22079, 22305, 22085, 22682, 22164, 22260, 22078, 22084, 22812, 22574, 22075, 22356, 22385, 22086, 22549, 
       22097, 22462, 22589, 22106, 22118, 22114, 58465, 22536, 22518, 22140, 22365, 22158, 50301, 22325, 22793, 22295, 22252, 22693, 22139, 
       22726, 22113, 22318, 59744, 22419, 22125, 22129, 22524, 51129, 48697, 22683, 22712, 51666, 22786, 22603, 22822, 22804, 22605, 22599, 
       22864, 22160, 22109, 22585, 22823, 22162, 22814, 22824, 22821, 57693, 22626, 22652, 22811, 22196, 22853, 22810, 22494, 22797, 22854, 
       22807, 22836, 22516, 22837, 22233, 22799, 22760, 22301, 22759, 22561, 59241, 22657, 59267, 22653, 22590, 22787, 22465, 22679, 22380, 
       22461, 22732, 22299, 22397, 22733, 22729, 22782, 22381, 22258, 22259, 22121, 57249, 22684, 22711, 51715, 22818, 22600, 22155, 48878, 
       22846, 22628, 58933, 49876, 58485, 48953, 22625, 22422, 22474, 22170, 22630, 58466, 22284, 22677, 22806, 22795, 59271, 22727, 22856, 
       22805, 22281, 22758, 22790, 22832, 22857, 22778, 22757, 22572, 22355, 22798, 59255, 22548, 22697, 22710, 59268, 22802, 22634, 22519, 
       22208, 22735, 22736, 22279, 22737, 22550, 22739, 59272, 22741, 22742, 58459, 22785, 22792, 48877, 22816, 22547, 48930, 48951, 59252, 
       48952, 22581, 22604, 22675, 59242, 59253, 22722, 22633, 51858, 48954, 59260, 22288, 22686, 22754, 22848, 22829, 22861, 59748, 22448, 
       22838, 22839, 59258, 22466, 22840, 22841, 22825, 22762, 59259, 22756, 22755, 22763, 22620, 22692, 22560, 22616, 51855, 22809, 22554, 
       51856, 22743, 22351, 22745, 22746, 22715, 22753, 22562, 59251, 22800, 22637, 59243, 22858, 22845, 59254, 22777, 22862, 59270, 22834, 
       22803, 22817, 58828, 22850, 59256, 59257, 51130, 59747, 59745, 22584, 22485, 22613, 22705, 22704, 22859, 22689, 58462, 22860, 22833, 
       59746, 22852, 22826, 49622, 58464, 22796, 22842, 22827, 57226, 22843, 22783, 22694, 22609, 22780, 22666, 22748, 22749, 22750, 22680, 
       22681, 22863, 59749, 22752, 22781, 22713, 22808, 22102, 22094, 22576, 22578, 22661, 22382, 22734, 22503, 22453, 59269, 22738, 22175, 
       22480, 22849, 51579, 22835, 22393, 22294, 22210, 22172, 22454, 22292, 22871, 22587
]

codes2=[]

codes3=[]

# codes_kumho = [57455, 47550, 47549, 53305, 51419, 57470, 47068, 48583, 48368, 49929, 48410, 57471, 48333, 49914, 57462, 47052, 53298, 57482, 
#                48366, 48311, 51431, 51427, 47572, 47556, 48413, 57458, 51437, 48409, 49921, 48457, 48288, 57477, 51412, 51434, 48384, 48411, 
#                57662, 49918, 51436, 47580, 57466, 48355, 48356, 48286, 51432, 48401, 57469, 58501, 53293, 47060, 58497, 51420, 48302, 48403, 
#                53302, 58496, 48312, 47577, 47039, 51445, 51442, 48382, 57493, 58506, 48372, 57488, 51448, 49926, 48438, 57473, 47582, 53297, 
#                48424, 59090, 47030, 48423, 48374, 48859, 47579, 49925, 51451, 51449, 58500, 48377, 48400, 57666, 51450, 57476, 53294, 48415, 
#                47581, 47064, 48354, 57489, 48416, 58505, 57478, 47583, 58498, 58502, 48452, 48319, 48444, 48342, 47043, 51403, 47044, 47034, 
#                48412, 48748, 48352, 57667, 57490, 57486, 57497, 57494, 48453, 48451, 48439, 47046
# ]

tupla10= [(22518, 263), (22260, 265), (22086, 177), (22804, 318), (22356, 166), (22712, 224), (22118, 183), (22114, 171), 
          (49072, 224), (22683, 200), (22752, 571)
]

tupla5= [(22170, 124),  (48697, 93),  (22155, 123),  (22785, 153),  (22252, 159),  (22295, 160),  (51857, 369),  (48954, 121),  
         (22604, 157),  (22814, 100),  (22288, 187),  (22605, 142),  (58485, 107),  (22826, 189),  (22677, 207),  (22524, 90),  
         (22162, 124),  (22422, 124),  (22625, 117),  (59242, 147),  (22516, 146),  (22816, 123),  (22823, 110),  (22419, 88),  
         (22684, 107),  (22075, 88),  (22777, 190),  (22633, 153),  (22711, 104),  (22822, 146),  (22628, 133),  (59868, 157),  
         (48878, 123)
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
########################################################################## Efervecente#########################################################################################################################################################################################
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
                if header == "Mejor Condición":
                    sheet.cell(row=row_idx, column=col_idx).value = f'=MIN(P{row_idx}:R{row_idx})'     
                    #=IF(IF(MIN(Q{row_idx}:T{row_idx}) > 0, MIN(Q{row_idx}:T{row_idx}), "") = S{row_idx}, S{row_idx}, IF(MIN(Q{row_idx}:T{row_idx}) > 0, MIN(Q{row_idx}:T{row_idx}), "") * (1-IF(ISNUMBER($U$13), $U$13, 0)))
                elif header == "PRECIO CON DESCUENTOS":
                    sheet.cell(row=row_idx, column=col_idx).value = f'''=S{row_idx}-(IF(IF(MIN(P{row_idx}:R{row_idx}) > 0, MIN(P{row_idx}:R{row_idx}), 0) = Q{row_idx}, 0, (IF(MIN(P{row_idx}:R{row_idx}) > 0, MIN(P{row_idx}:R{row_idx}), 0) * (IF(ISNUMBER($C$6), $C$6, 0))))) - (S{row_idx} * $C$8) - (S{row_idx} * $C$7) - (IF(H{row_idx} = "ONYX", (S{row_idx} * $J$10), 0)) - (IF(OR(H{row_idx} = "VENOM", H{row_idx} = "MILESTAR"), (S{row_idx} * $C$12), 0))'''
                   #=S{row_idx}-(IF(IF(MIN(P{row_idx}:R{row_idx}) > 0, MIN(P{row_idx}:R{row_idx}), 0) = Q{row_idx}, 0, (IF(MIN(P{row_idx}:R{row_idx}) > 0, MIN(P{row_idx}:R{row_idx}), 0) * (IF(ISNUMBER($C$6), $C$6, 0))))) - (IF($J$11 <> 0%, IF(OR(H{row_idx}="DELINTE", H{row_idx}="FIREMAX", H{row_idx}="APTANY", H{row_idx}="DOUBLESTAR"), (S{row_idx} * $J$11), (S{row_idx} * $C$8)), (S{row_idx} * $C$8))) - (S{row_idx} * $C$7) - (IF(H{row_idx} = "ONYX", (S{row_idx} * $J$10), 0)) - (IF(OR(H{row_idx} = "VENOM", H{row_idx} = "MILESTAR"), (S{row_idx} * $C$12), 0))
                   #sheet.cell(row=row_idx, column=col_idx).value = f'=S{row_idx}-(IF(IF(MIN(P{row_idx}:R{row_idx}) > 0, MIN(P{row_idx}:R{row_idx}), 0) = Q{row_idx}, 0, (IF(MIN(P{row_idx}:R{row_idx}) > 0, MIN(P{row_idx}:R{row_idx}), 0) * (IF(ISNUMBER($C$6), $C$6, 0))))) - (IF($C$11 <> 0%, IF(OR(H{row_idx}="DELINTE", H{row_idx}="FIREMAX", H{row_idx}="APTANY", H{row_idx}="DOUBLESTAR"), (S{row_idx} * $C$11), (S{row_idx} * $C$8)), (S{row_idx} * $C$8))) - (S{row_idx} * $C$7) - (IF(H{row_idx} = "ONYX", (S{row_idx} * $C$13), 0))'
                   #=S{row_idx}-(IF(IF(MIN(P{row_idx}:R{row_idx}) > 0, MIN(P{row_idx}:R{row_idx}), 0) = Q{row_idx}, 0, (IF(MIN(P{row_idx}:R{row_idx}) > 0, MIN(P{row_idx}:R{row_idx}), 0) * (IF(ISNUMBER($C$6), $C$6, 0))))) - (IF($C$11 <> 0%, IF(OR(H{row_idx}="DELINTE", H{row_idx}="FIREMAX", H{row_idx}="APTANY", H{row_idx}="DOUBLESTAR"), (S{row_idx} * $C$11), (S{row_idx} * $C$8)), (S{row_idx} * $C$8))) - (S{row_idx} * $C$7) - (IF(H{row_idx} = "ONYX", (S{row_idx} * $J$11), 0)) - (IF(OR(G{row_idx} = "MS932 SPORT", G{row_idx} = "WEATHERGUARD AW365", G{row_idx} = "COVERT GRIP CV"),S{row_idx} * $C$12,0))- (IF(AND(ISNUMBER(MATCH(MID(C{row_idx}, FIND("R", C{row_idx}), 3), {{"R13","R14","R15","R16"}}, 0)),H{row_idx} = "KUMHO",OR(K{row_idx} = "AT", K{row_idx} = "MT")),S{row_idx} * $J$12,0))- (IF(AND(ISNUMBER(MATCH(MID(C{row_idx}, FIND("R", C{row_idx}), 3), {{"R17","R18","R19","R20","R21","R22"}}, 0)),H{row_idx} = "KUMHO",OR(K{row_idx} = "AT", K{row_idx} = "MT")),S{row_idx} * $J$13,0))
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
                if header == "Mejor Condición":
                    sheet.cell(row=row_idx, column=col_idx).value = f'=IF(Q{row_idx}="", R{row_idx}, MIN((Q{row_idx}*0.9), R{row_idx}))'
                    #=MIN(Q{row_idx}:R{row_idx})
                    #=IF(IF(MIN(Q{row_idx}:T{row_idx}) > 0, MIN(Q{row_idx}:T{row_idx}), "") = S{row_idx}, S{row_idx}, IF(MIN(Q{row_idx}:T{row_idx}) > 0, MIN(Q{row_idx}:T{row_idx}), "") * (1-IF(ISNUMBER($U$13), $U$13, 0)))
                    
                elif header == "PRECIO CON DESCUENTOS":
                    sheet.cell(row=row_idx, column=col_idx).value = f'=(S{row_idx}-(IF(Q{row_idx} = "",  R{row_idx}*$C$6,  Q{row_idx}*$C$6))-(IF(Q{row_idx} = "",  R{row_idx}*$C$7,  Q{row_idx}*$C$7))-(IF(Q{row_idx} = "",  R{row_idx}*$C$8,  Q{row_idx}*$C$8))-(T{row_idx})) - X{row_idx}'
                                                                      
                    #=(W{row_idx}-(W{row_idx}*$C$6)-(W{row_idx}*$C$7)-(W{row_idx}*$C$8)-(R{row_idx})) - V{row_idx} - IF(O{row_idx} = (W{row_idx} * 0.9), W{row_idx}*0.1, 0)
                    #=(Y{row_idx}-(Y{row_idx}*$C$6)-(Y{row_idx}*$C$7)-(Y{row_idx}*$C$8)-(T{row_idx})) - X{row_idx} - IF(Q{row_idx} = (Y{row_idx} * 0.9), Y{row_idx}*0.1, 0)
                    
                elif header == "PROMO BS":
                    sheet.cell(row=row_idx, column=col_idx).value = f'=IF(P{row_idx} = "SI", IF(Q{row_idx} = "",  R{row_idx}*$L$13,  Q{row_idx}*$L$13), 0)'
                                                                                                                      
                elif header == "PESOS":
                    sheet.cell(row=row_idx, column=col_idx).value = f'=IF(V{row_idx} = "", "", V{row_idx}*S{row_idx})'   
                                                                                                             
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
    def set_combos(self,sheet, combo_data):
        combo_cells = []
        for data in combo_data:
            cell_ref = data['cell_ref']
            values = data['values']
            combo_cells.append(self._set_combo(sheet, cell_ref, values))
        return combo_cells

    def _set_combo(self,sheet, cell_ref, values):
        dv = DataValidation(type="list", formula1='"' + ','.join(values) + '"', allow_blank=True)
        sheet.add_data_validation(dv)
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
        
        milestar_col_idx = column_index_from_string('H')
        measure_col_idx = column_index_from_string('C')
        segment_col_idx = column_index_from_string('K')
        model_col_idx = column_index_from_string('G')
        id_col_idx = column_index_from_string('A')
        start_column = 'A'
        end_column = 'S'
        
        start_column2 = 'G'
        end_column2 = 'G'
        
        start_column3 = 'A'
        end_column3 = 'B'
        
        for row in sheet.iter_rows(min_row=15):  # Start from row 2 to skip header
            outlet_cell = row[outlet_col_idx - 1]  # Adjust index to zero-based
            t4_cell = row[t4_col_idx - 1]
            tier4_cell = row[tier4_col_idx - 1]
            # Example condition: Color 'Outlet' column yellow if cell value is not empty
            if isinstance(outlet_cell.value, (int, float)) and outlet_cell.value > 0:
                for col_idx in range(column_index_from_string(outlet_start_column) - 1, column_index_from_string(outlet_end_column)):
                    cell = row[col_idx]
                    cell.fill = PatternFill(start_color='FDFFCD', end_color='FDFFCD', fill_type='solid')
                outlet_cell.fill = PatternFill(start_color='FDFFCD', end_color='FDFFCD', fill_type='solid')
                
            if tier4_cell.value in ['DELINTE', 'FIREMAX', 'APTANY', 'DOUBLESTAR']:
                t4_cell.fill = PatternFill(start_color='DDE5F2', end_color='DDE5F2', fill_type='solid')
                    
        for row in sheet.iter_rows(min_row=15):
            milestar_cell = row[milestar_col_idx - 1]
            for col in range(ord(start_column), ord(end_column) + 1):
                if milestar_cell.value in ['ONYX']:
                    cell = row[col - ord(start_column)]
                    cell.fill = PatternFill(start_color='EBF1DE', end_color='EBF1DE', fill_type='solid')

                    
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
                    
        for row in sheet.iter_rows(min_row=15):
            tier4_cell = row[tier4_col_idx - 1]
            for col in range(ord(start_column3), ord(end_column3) + 1):
                if tier4_cell.value in ['MILESTAR', 'VENOM']:
                    cell = row[col - ord(start_column)]
                    cell.fill = PatternFill(start_color='BFBFBF', end_color='BFBFBF', fill_type='solid')  
                    
    def color_cells_based_on_condition_sheet3(self, sheet):
        ids_in_codes_brig = 'A'
        codes_brige = 'B'
        start_column = 'S'
        end_column = 'U'
        cupones = 'V'
                
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
                    'Medida': obj.tire_measure_id.name if obj.tire_measure_id else None,
                    'Capas': obj.layer_id.name if obj.layer_id else None,
                    'Vel': obj.speed_id.name if obj.speed_id else None,
                    'Carga': obj.index_of_load_id.name if obj.index_of_load_id else None,
                    'Modelo': obj.model_id.name if obj.model_id else None,
                    'Marca': obj.brand_id.name if obj.brand_id else None,
                    'Equipo Original': obj.original_equipment_id.name if obj.original_equipment_id else None,
                    'Tipo': obj.product_id.type_id.name or None,
                    'Seg': obj.product_id.segment_id.name or None,
                    'Tier': obj.tier_id.name if obj.tier_id else None,
                    'Inv.': obj.inventario_str,
                    #'Cantidad Disponible': obj.available,
                    'Trans.': (obj.transito_str + obj.backorder_str) or None,
                    #'Arribo': obj.fecha_aprox or None,
                    'DOT': obj.lot_name or 'N/A' or None,  
                    }
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
                    'Promo Dot': obj.promo_dot * 1.16,
                    'Mejor Condición': "",
                    'PROMO BS': "",
                    'PRECIO CON DESCUENTOS': "",
                    'PIEZAS': "",
                    'PESOS': "",
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
            data_dict = {                
                'id': obj.product_id.id,            
                'Código': obj.default_code,
                'Medida': obj.tire_measure_id.name if obj.tire_measure_id else None,
                'Capas': obj.layer_id.name if obj.layer_id else None,
                'Vel': obj.speed_id.name if obj.speed_id else None,
                'Carga': obj.index_of_load_id.name if obj.index_of_load_id else None,
                'Modelo': obj.model_id.name if obj.model_id else None,
                'Marca': obj.brand_id.name if obj.brand_id else None,
                'Equipo Original': obj.original_equipment_id.name if obj.original_equipment_id else None,
                'Tipo': obj.product_id.type_id.name or None,
                'Seg': obj.product_id.segment_id.name or None,
                'Tier': obj.tier_id.name if obj.tier_id else None,
                'Inv.': obj.inventario_str,
                #'Cantidad Disponible': obj.available,
                'Trans.': (obj.transito_str + obj.backorder_str) or None,
                #'Arribo': obj.fecha_aprox or None,
                'DOT': obj.lot_name or 'N/A' or None,  
                }         
            data_list.append(data_dict)            
            data_dict.update({
                'Mayoreo': obj.volumen * 1.16,
                'Outlet': obj.outlet * 1.16,
                'Promo Dot': obj.promo_dot * 1.16,
                'Mejor Condición': "",
                'PRECIO CON DESCUENTOS': "",
                'Pedido': "",
            })  
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

    def get_xlsx_report(self, partner_id, return_base_64=False):
        # 1
        include_promo = True
        
        objects = self.env['inv_promo.report'].sudo().insert_data()
        con_iva = self.get_dict_data(objects,'Precios Con Iva',partner_id)
        #precio_especial = self.get_dict_data(objects,'P. GOODYEAR')
        promo_bridgestone = self.get_dict_data(objects, 'P. BRIDGESTONE', partner_id)
        wb = Workbook()
        sheet1 = wb.active
        sheet1.title = "Precios Con Iva"

        #financial,logistic = self.get_profile_data(partner_id)
        logistic_percent = ['0%','2%','4%']
        volume_percent = ['0%','2%','3%']
        financial_percent = ['0%','2%','3%']
        
        bs_percent = [
            '0%', '2%', '4%', '6%', '8%', '9%', '10%'
            ]
        
        t3_f1 = ['0', '700']
        t3_percent = ['0', '50', '150']
        t3_cred = ['0%', '2%']
        
        onyx_percent = ['0%', '5%', '7%']
        t4_percent = ['0%', '2%']
         
        combo_data_sheet1 = [
            {'cell_ref': 'C6', 'values': logistic_percent},
            {'cell_ref': 'C7', 'values': volume_percent},
            {'cell_ref': 'C8', 'values': financial_percent},
            
            {'cell_ref': 'C10', 'values': t3_f1},
            {'cell_ref': 'C11', 'values': t3_percent},
            {'cell_ref': 'C12', 'values': t3_cred},
            
            
            {'cell_ref': 'J10', 'values': onyx_percent},
            {'cell_ref': 'J11', 'values': t4_percent},
        ]
        
        combo_data_sheet3 = [
            {'cell_ref': 'C6', 'values': logistic_percent},
            {'cell_ref': 'C7', 'values': volume_percent},
            {'cell_ref': 'C8', 'values': financial_percent},
            {'cell_ref': 'L13', 'values': bs_percent}
        ]
        
        self.set_combos(sheet1, combo_data_sheet1)
        
        #####Fill Tables
        num_rows_1, num_cols_1 = self.insert_table_sheet1(sheet1, con_iva, "TablaDatos1")

        self.set_frames(sheet1)
        
        sheet1.sheet_properties.tabColor = WHITE

        self.set_white_fill(sheet1, 'A1', num_rows_1, num_cols_1)
        values = '{"DOUBLESTAR","DELINTE","FIREMAX","APTANY"}'
        
         # Definir los datos para las celdas
        data_for_sheet1 = [
            {'cell_ref': 'W7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': '808080', 'bold': True, 'fill_color': WHITE, 'border': 'none', 'align': 'left', 'top_align': 'top', 'wrap_text': False, 'num_format': '#,##0.00', 'value': f"V{self.partner_id.volume_profile.name}F{self.partner_id.financial_profile.letter}L{self.partner_id.logistic_profile.letter}", 'data_type': 'string'},
            {'cell_ref': 'A4:G4', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "LISTA DE PRECIOS", 'data_type': 'string'},
            {'cell_ref': 'A6:B6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Logístico", 'data_type': 'string'},
            {'cell_ref': 'A7:B7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Volumen", 'data_type': 'string'},
            {'cell_ref': 'A8:B8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Financiero", 'data_type': 'string'},
            {'cell_ref': 'S10:U10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'FDFFCD', 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Códigos en los que no aplica desc. logístico", 'data_type': 'string'},
            
            {'cell_ref': 'C6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
            {'cell_ref': 'C7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
            {'cell_ref': 'C8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
            
            {'cell_ref': 'D6:F6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=IF(C6 = 4%, "Min 300 pz x envío", IF(C6 = 2%, "Min 100 pz x envío", "0-99 pz x envío"))"""},
            {'cell_ref': 'D7:F7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=IF(C7 = 3%, "Min 600 pz mensuales", IF(C7 = 2%, "Min 400 pz mensuales", "0-399 pz mensuales"))"""},
            {'cell_ref': 'D8:F8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Pagando en tiempo sus facturas.", 'data_type': 'string'},
            
            {'cell_ref': 'A5:F5', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': '595959', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "CONDICIONES:", 'data_type': 'string'},
            {'cell_ref': 'G5', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "TOTAL LLANTAS", 'data_type': 'string'},
            {'cell_ref': 'A9:F9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': '595959', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "PROMOCIONES:", 'data_type': 'string'},
            {'cell_ref': 'G9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "TOTAL LLANTAS", 'data_type': 'string'},
            {'cell_ref': 'H9:M9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': '595959', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "PROMOCIONES:", 'data_type': 'string'},
            {'cell_ref': 'N9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "TOTAL LLANTAS", 'data_type': 'string'},
            
            {'cell_ref': 'A10:B10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'BFBFBF', 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "TIER 3 F1", 'data_type': 'string'},
            {'cell_ref': 'A11:B11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'BFBFBF', 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "TIER 3", 'data_type': 'string'},
            {'cell_ref': 'A12:B12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'BFBFBF', 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "TIER 3 CRED", 'data_type': 'string'},
            
            {'cell_ref': 'H10:I10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'EBF1DE', 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "ONYX", 'data_type': 'string'},
            {'cell_ref': 'H11:I11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'C5D9F1', 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "TIER 4", 'data_type': 'string'},
            
            {'cell_ref': 'C10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'BFBFBF', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': 0},
            {'cell_ref': 'C11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'BFBFBF', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': 0},
            {'cell_ref': 'C12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'BFBFBF', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
            
            {'cell_ref': 'J10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'EBF1DE', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
            {'cell_ref': 'J11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'C5D9F1', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
            
            
            {'cell_ref': 'D10:F10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'BFBFBF', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=IF(C10 = 700, "BOLETO F1", "No aplica promoción")"""},
            {'cell_ref': 'D11:F11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'BFBFBF', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=IF(C11 >= 120, "Min 150 pz mensuales, ME 8K", IF(C11 >= 35, "Min 50 pz mensuales, ME 2.5K", "<------ ¡ ELIGE TU PROMO!"))"""},
            {'cell_ref': 'D12:F12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'BFBFBF', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=IF(C12 = 2%, "Min 50pz, 2% fin  + 60 Dias cred.", "No aplica promoción")"""},
            
            {'cell_ref': 'K10:M10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'EBF1DE', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=IF(J10 = 7%, "Min 100pz por pedido", IF(J10 = 5%, "Min 40pz por pedido", "No aplica promoción"))"""},
            {'cell_ref': 'K11:M11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'C5D9F1', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=IF(J11 = 2%, "Min 40pz, 2% fin  + 60 Dias cred.", "No aplica promoción")"""},  
                                                                                                                                                                                                                                                        
            {'cell_ref': 'G6:G7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=SUM(U15:U{num_rows_1})+SUM('P. BRIDGESTONE'!V15:V{num_rows_1})"""},
            
            {'cell_ref': 'G10:G12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'BFBFBF', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=SUMIFS(U15:U{num_rows_1},H15:H{num_rows_1},"MILESTAR") + SUMIFS(U15:U{num_rows_1},H15:H{num_rows_1},"VENOM")"""},
            
            {'cell_ref': 'N10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'EBF1DE', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=SUMIFS(U15:U{num_rows_1},H15:H{num_rows_1},"ONYX")"""},
            {'cell_ref': 'N11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'C5D9F1', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=SUMIF(H15:H1017, "DELINTE", U15:U1017) + SUMIF(H15:H1017, "FIREMAX", U15:U1017) + SUMIF(H15:H1017, "APTANY", U15:U1017) + SUMIF(H15:H1017, "DOUBLESTAR", U15:U1017)"""},
            
            {'cell_ref': 'S11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "BRIDGESTONE", 'data_type': 'string'},
            {'cell_ref': 'T11:U11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '$#,##0.00', 'value': "Consulte segunda hoja", 'data_type': 'string'},

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
            {'cell_ref': 'S14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'T14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': RED, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'U14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},

        ]
        
        #Establecer formatos
        self.format_column(sheet1,'B','string')
        self.format_column(sheet1,'C','string')
        self.format_column(sheet1,'D','string')
        self.format_column(sheet1,'E','string')
        self.format_column(sheet1,'F','string')
        self.format_column(sheet1,'G','string')
        self.format_column(sheet1,'H','string')
        self.format_column(sheet1,'I','string')
        self.format_column(sheet1,'J','string')
        self.format_column(sheet1,'K','string')
        self.format_column(sheet1,'L','string')
        self.format_column(sheet1,'M','string')
        self.format_column(sheet1,'N','string')
        self.format_column(sheet1,'O','currency')
        self.format_column(sheet1,'P','currency')
        self.format_column(sheet1,'Q','currency')
        self.format_column(sheet1,'R','currency')
        self.format_column(sheet1,'S','currency')
        self.format_column(sheet1,'T','currency')
        self.format_column(sheet1,'U','number')
        
        columna_a_ocultar_sheet1 = ['A', 'P', 'Q', 'R']
        
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
        end_col = 'U'   
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
            self.set_combos(sheet3, combo_data_sheet3) 
            num_rows_3, num_cols_3 = self.insert_table_sheet3(sheet3, promo_bridgestone, "TablaDatos3")
            self.set_frames(sheet3)
            sheet3.sheet_properties.tabColor = 'E6B8B8'
            sheet4.sheet_properties.tabColor = 'FFFF00'
            self.set_white_fill(sheet3, 'A1', num_rows_3, num_cols_3)

            data_for_sheet3 = [
                {'cell_ref': 'E1', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "", 'data_type': 'string'},
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
                {'cell_ref': 'V14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'W14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': 'C00000', 'bold': True, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'X14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': 'C00000', 'bold': True, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                #{'cell_ref': 'Y14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': 'C00000', 'bold': True, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                
                #{'cell_ref': 'S12:V13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': 'C00000', 'bold': True, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'value': "VALOR CUPON YA DESCONTADO EN PRECIO CON DESCUENTO", 'data_type': 'string'},
                ]
            
            promobrid = [
                {'cell_ref': 'A4:G4', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "LISTA DE PRECIOS", 'data_type': 'string'},
                {'cell_ref': 'A5:F5', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': '595959', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "CONDICIONES:", 'data_type': 'string'},
                {'cell_ref': 'A6:B6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Logístico", 'data_type': 'string'},
                {'cell_ref': 'A7:B7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Volumen", 'data_type': 'string'},
                {'cell_ref': 'A8:B8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Financiero", 'data_type': 'string'},
                {'cell_ref': 'A9:F9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'FDE9D9', 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Códigos que suman a la promoción", 'data_type': 'string'},
                {'cell_ref': 'D6:F6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=IF(C6 = 4%, "Min 300 pz x envío", IF(C6 = 2%, "Min 100 pz x envío", "0-99 pz x envío"))"""},
                {'cell_ref': 'D7:F7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=IF(C7 = 3%, "Min 600 pz mensuales", IF(C7 = 2%, "Min 400 pz mensuales", "0-399 pz mensuales"))"""},
                {'cell_ref': 'D8:F8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Pagando en tiempo sus facturas.", 'data_type': 'string'},
                {'cell_ref': 'G5', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "TOTAL LLANTAS", 'data_type': 'string'},
                {'cell_ref': 'G6:G7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=SUM(V15:V{num_rows_3})+SUM('Precios Con Iva'!U15:U{num_rows_1})"""},
                {'cell_ref': 'C6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
                {'cell_ref': 'C7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
                {'cell_ref': 'C8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
                
                {'cell_ref': 'J4:N4', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "PROMOCIÓN:", 'data_type': 'string'},
                
                {'cell_ref': 'J5:K5', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "Monto neto mensual", 'data_type': 'string'},
                {'cell_ref': 'L5', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "Desc", 'data_type': 'string'},
                {'cell_ref': 'M5:N5', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "ADICIONAL", 'data_type': 'string'},
                {'cell_ref': 'M6:N12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'value': "", 'data_type': 'string'},
                
                {'cell_ref': 'J6:K6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "$0 a $46,399", 'data_type': 'string'},
                {'cell_ref': 'L6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "0%", 'data_type': 'string'},
                
                {'cell_ref': 'J7:K7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "$46,400 a $115,999", 'data_type': 'string'},
                {'cell_ref': 'L7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "2%", 'data_type': 'string'},
                
                {'cell_ref': 'J8:K8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "$116,000 a $347,999", 'data_type': 'string'},
                {'cell_ref': 'L8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "4%", 'data_type': 'string'},
                
                {'cell_ref': 'J9:K9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "$348,000 a $695,999", 'data_type': 'string'},
                {'cell_ref': 'L9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "6%", 'data_type': 'string'},
                
                {'cell_ref': 'J10:K10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "$696,000 a $869,999", 'data_type': 'string'},
                {'cell_ref': 'L10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "8%", 'data_type': 'string'},
                
                {'cell_ref': 'J11:K11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "$870,000 a $1,087,499", 'data_type': 'string'},
                {'cell_ref': 'L11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "9%", 'data_type': 'string'},
            
                {'cell_ref': 'J12:K12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "Más de $1,087,500", 'data_type': 'string'},
                {'cell_ref': 'L12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "10%", 'data_type': 'string'},
                
                {'cell_ref': 'A11:E12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': 'C00000', 'bold': True, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': True, 'num_format': '$#,##0.00', 'value': "Códigos que otorgan el descuento del cupón señalado ya reflejado en el precio. Máx. 200 x medida x RFC.", 'data_type': 'string'},
                {'cell_ref': 'F11:G11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'F2F2F2', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "ACUMULADO TOTAL", 'data_type': 'string'},
                {'cell_ref': 'F12:G12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '$#,##0.00', 'value': f"""=SUM(W15:W{num_rows_3})""", 'data_type': '$0'},
                {'cell_ref': 'H11:I11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "ACUMULADO PROMO", 'data_type': 'string'},
                {'cell_ref': 'H12:I12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '$#,##0.00', 'value': f"""=SUMIFS(W15:W{num_rows_3},P15:P{num_rows_3},"SI")""", 'data_type': '$0'},
                
                {'cell_ref': 'L13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': RED, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
                ]
            
            data_for_sheet4 = [
                {'cell_ref': 'A4:N4', 'font_name': 'Calibri', 'font_size': 11, 'font_color': 'FFC000', 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Promociones Comerciales Mayo 2025", 'data_type': 'string'},
                
                {'cell_ref': 'A6:B7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Marcas", 'data_type': 'string'},
                {'cell_ref': 'C6:C7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Clave de la Promoción", 'data_type': 'string'},
                {'cell_ref': 'D6:D7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Facturación Neta requerida", 'data_type': 'string'},
                {'cell_ref': 'E6:E7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Condición", 'data_type': 'string'},
                {'cell_ref': 'F6:F7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Vigencia", 'data_type': 'string'},
                {'cell_ref': 'G6:I6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Beneficios", 'data_type': 'string'},
                {'cell_ref': 'G7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': '595959', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Bonificación", 'data_type': 'string'},
                {'cell_ref': 'H7:I7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': '595959', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Adicional", 'data_type': 'string'},
                {'cell_ref': 'J6:N7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Observaciones", 'data_type': 'string'},
                
                {'cell_ref': 'A8:B13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "BRIDGESTONE Y FIRESTONE", 'data_type': 'string'},
                
                {'cell_ref': 'C8:C13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "BS-07", 'data_type': 'string'},
                
                {'cell_ref': 'D8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "de $46,400 a $115,999 netos", 'data_type': 'string'},
                {'cell_ref': 'D9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "de $116,000 a $347,999 netos", 'data_type': 'string'},
                {'cell_ref': 'D10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "de $348,000 a $695,999 netos", 'data_type': 'string'},
                {'cell_ref': 'D11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "de $696,000 a $869,999 netos", 'data_type': 'string'},
                {'cell_ref': 'D12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "de $870,000 a $1,087,499 netos", 'data_type': 'string'},
                {'cell_ref': 'D13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Más de $1,087,500  netos", 'data_type': 'string'},
                
                {'cell_ref': 'E8:E13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Por periodo", 'data_type': 'string'},
                
                {'cell_ref': 'F8:F13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "1 al 31 de Mayo", 'data_type': 'string'},
                
                {'cell_ref': 'G8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "2%", 'data_type': 'string'},
                {'cell_ref': 'G9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "4%", 'data_type': 'string'},
                {'cell_ref': 'G10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "6%", 'data_type': 'string'},
                {'cell_ref': 'G11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "8%", 'data_type': 'string'},
                {'cell_ref': 'G12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "9%", 'data_type': 'string'},
                {'cell_ref': 'G13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "10%", 'data_type': 'string'},
                
                {'cell_ref': 'H8:I13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "", 'data_type': 'string'},
                
                {'cell_ref': 'J8:N13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Códigos y promoción adicional por confirmar.Consulte códigos participantes / Bonificación en Nota de Crédito /  ", 'data_type': 'string'},
                #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
                #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
                {'cell_ref': 'A14:B15', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Marcas", 'data_type': 'string'},
                {'cell_ref': 'C14:C15', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Clave de la Promoción", 'data_type': 'string'},
                {'cell_ref': 'D14:D15', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Llantas Requeridas", 'data_type': 'string'},
                {'cell_ref': 'E14:E15', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Condición", 'data_type': 'string'},
                {'cell_ref': 'F14:F15', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Vigencia", 'data_type': 'string'},
                {'cell_ref': 'G14:I15', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Beneficios", 'data_type': 'string'},
                {'cell_ref': 'J14:N15', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Observaciones", 'data_type': 'string'},
                
                {'cell_ref': 'A16:B21', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Milestar y Venom", 'data_type': 'string'},
                
                {'cell_ref': 'C16:C17', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Tier 3 - 07", 'data_type': 'string'},
                {'cell_ref': 'C18:C19', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Fórmula 1 - Tier 3", 'data_type': 'string'},
                {'cell_ref': 'C20:C21', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Tier 3 - Crédito 07", 'data_type': 'string'},
            
                {'cell_ref': 'D16', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "50", 'data_type': 'string'},
                {'cell_ref': 'D17', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "160", 'data_type': 'string'},
                {'cell_ref': 'D18:D19', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "700", 'data_type': 'string'},
                {'cell_ref': 'D20:D21', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "50", 'data_type': 'string'},
            
                {'cell_ref': 'E16:E19', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Por Periodo", 'data_type': 'string'},
                {'cell_ref': 'E20:E21', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Por Factura", 'data_type': 'string'},
                
                {'cell_ref': 'F16:F17', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "1 al 31 de Julio", 'data_type': 'string'},
                {'cell_ref': 'F18:F19', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "1 de Julio al 30 de Agosto", 'data_type': 'string'},
                {'cell_ref': 'F20:F21', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "1 al 31 de Julio", 'data_type': 'string'},
                
                {'cell_ref': 'G16:I16', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "ME  $2,500", 'data_type': 'string'},
                {'cell_ref': 'G17:I17', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "ME  $8,000", 'data_type': 'string'},
                {'cell_ref': 'G18:I19', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "1 Acceso Fórmula 1", 'data_type': 'string'},
                {'cell_ref': 'G20:I21', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "60 días de Crédito y 2'%' Financiero", 'data_type': 'string'},
                
                {'cell_ref': 'J16:N17', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Participan Todos los Modelos Milestar y Venom", 'data_type': 'string'},
                {'cell_ref': 'J18:N19', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Participan Todos los Modelos Milestar y Venom. / Limitado a 4 accesos.", 'data_type': 'string'},
                {'cell_ref': 'J20:N21', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Participan Todos los Modelos Milestar y Venom / Aplica solo para clientes con crédito.", 'data_type': 'string'},
                #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
                #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
                {'cell_ref': 'A22:B23', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Marcas", 'data_type': 'string'},
                {'cell_ref': 'C22:C23', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Clave de la Promoción", 'data_type': 'string'},
                {'cell_ref': 'D22:D23', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Llantas Requeridas", 'data_type': 'string'},
                {'cell_ref': 'E22:E23', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Condición", 'data_type': 'string'},
                {'cell_ref': 'F22:F23', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Vigencia", 'data_type': 'string'},
                {'cell_ref': 'G22:I23', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Beneficios", 'data_type': 'string'},
                {'cell_ref': 'J22:N23', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Observaciones", 'data_type': 'string'},
                
                {'cell_ref': 'A24:B25', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Aptany Delinte, Firemax y Doublestar", 'data_type': 'string'},
                
                {'cell_ref': 'C24:C25', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Tier 4 - 07", 'data_type': 'string'},
                
                {'cell_ref': 'D24:D25', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "40", 'data_type': 'string'},
            
                {'cell_ref': 'E24:E25', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Por Factura", 'data_type': 'string'},
            
                {'cell_ref': 'F24:F25', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "1 al 31 de Julio", 'data_type': 'string'},
            
                {'cell_ref': 'G24:I25', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "60 días de Crédito y 2'%' Financiero", 'data_type': 'string'},
            
                {'cell_ref': 'J24:N25', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Participan todos los modelos. / Aplica solo para clientes con crédito.", 'data_type': 'string'},
                #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
                #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
                {'cell_ref': 'A26:B27', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Marcas", 'data_type': 'string'},
                {'cell_ref': 'C26:C27', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Clave de la Promoción", 'data_type': 'string'},
                {'cell_ref': 'D26:D27', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Llantas Requeridas", 'data_type': 'string'},
                {'cell_ref': 'E26:E27', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Condición", 'data_type': 'string'},
                {'cell_ref': 'F26:F27', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Vigencia", 'data_type': 'string'},
                {'cell_ref': 'G26:I26', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Beneficios", 'data_type': 'string'},
                {'cell_ref': 'G27:I27', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': '595959', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Bonificación", 'data_type': 'string'},
                {'cell_ref': 'J26:N27', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Observaciones", 'data_type': 'string'},
                
                {'cell_ref': 'A28:B29', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "ONYX", 'data_type': 'string'},
            
                {'cell_ref': 'C28:C29', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Onyx - 07", 'data_type': 'string'},
            
                {'cell_ref': 'D28:D28', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "40", 'data_type': 'string'},
                {'cell_ref': 'D29:D29', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "100", 'data_type': 'string'},
                
                {'cell_ref': 'E28:E29', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Por Periodo", 'data_type': 'string'},
            
                {'cell_ref': 'F28:F29', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "1 al 31 de Mayo", 'data_type': 'string'},
            
                {'cell_ref': 'G28:I28', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "5%", 'data_type': 'string'},
                {'cell_ref': 'G29:I29', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "7%", 'data_type': 'string'},
                
                {'cell_ref': 'J28:N29', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Bonificación en Nota de Crédito.", 'data_type': 'string'},
                #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
                #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
                {'cell_ref': 'A30:B31', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Marcas", 'data_type': 'string'},
                {'cell_ref': 'C30:C31', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Clave de la Promoción", 'data_type': 'string'},
                {'cell_ref': 'D30:D31', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Llantas Requeridas", 'data_type': 'string'},
                {'cell_ref': 'E30:E31', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Condición", 'data_type': 'string'},
                {'cell_ref': 'F30:F31', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Vigencia", 'data_type': 'string'},
                {'cell_ref': 'G30:I30', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Beneficios", 'data_type': 'string'},
                {'cell_ref': 'G31:I31', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': '595959', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Bonificación", 'data_type': 'string'},
                {'cell_ref': 'J30:N31', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Observaciones", 'data_type': 'string'},
                
                {'cell_ref': 'A32:B33', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "DRC", 'data_type': 'string'},
            
                {'cell_ref': 'C32:C33', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "DRC - 07", 'data_type': 'string'},
            
                {'cell_ref': 'D32:D33', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "100", 'data_type': 'string'},
                
                {'cell_ref': 'E32:E33', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Por Factura", 'data_type': 'string'},
            
                {'cell_ref': 'F32:F33', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "14 al 31 de Julio", 'data_type': 'string'},
            
                {'cell_ref': 'G32:I33', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "15%", 'data_type': 'string'},
                
                {'cell_ref': 'J32:N33', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Descuento aplicado en factura.", 'data_type': 'string'},
                #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
                #------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
                {'cell_ref': 'A34:N34', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Estas promociones sustituyen a las anteriores.", 'data_type': 'string'},
                {'cell_ref': 'A35:N36', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Las promociones por periodo serán válidas sumando las piezas facturadas durante el periodo indicado y el adicional se entregará durante los últimos 10 días del mes siguiente, o cuando el cliente liquide las facturas.", 'data_type': 'string'},
                {'cell_ref': 'A37:N37', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0', 'value': "Las promociones aplican únicamente al pago en tiempo de las facturas.", 'data_type': 'string'},
                
                ]

            # Formatear las celdas para la hoja 3
            for data in data_for_sheet3:
                self.format_cell(sheet3, **data)
            for data in promobrid:
                self.format_cell(sheet3, **data)
            for data in data_for_sheet4:
                self.format_cell(sheet4, **data)
                
                  
            # Lista de hojas a formatear
            sheets = [sheet3]

            # Diccionario que define las columnas y sus formatos
            formats = {
                'string': ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'O', 'P'],
                'number': ['N', 'V'],
                'currency': ['Q', 'R', 'S', 'T', 'U', 'W', 'X', 'Y'],
            }
            
            #-------- Ocultar columnas ----------------------
            # Seleccionar la hoja que deseas ocultar
            # sheet = wb['P. BRIDGESTONE']
            # Para ocultar la hoja:
            # sheet.sheet_state = 'hidden'
            
            columna_a_ocultar_sheet3 = ['A','P', 'Q', 'R', 'T', 'W', 'X', 'Y']
            
            # Itera sobre cada hoja
            for sheet in sheets:
                start_row = 14
                end_row = num_rows_3
                start_col = 'A'
                end_col = 'Y'
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
                        

        # Ajustar el ancho de las columnas en todas las hojas basándose en la fila 1 (por ejemplo)
        row_num = 14
        desired_height = 40  # Altura deseada en puntos
        
        for sheet in wb.sheetnames:
            ws = wb[sheet]
            ws.row_dimensions[row_num].height = desired_height
            self.auto_adjust_column_widths(ws, row_num)
            
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