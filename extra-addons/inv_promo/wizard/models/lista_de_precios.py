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
from openpyxl.utils import get_column_letter
from pytz import timezone
import openpyxl
import base64
import io

codes=[22094,22419,22356,51533,22305,22086,22088,22518,22589,22118,22804,49875,57249,51810,22524,48697,51129,22711,51575,22684,22712,22683,
       22603,22822,22822,22605,22785,58459,48877,22155,22158,22158,22158,22161,22628,58933,22814,22823,49876,50301,22260,58485,22175,48951,
       48953,22604,22776,22828,22170,22652,22633,22777,22817,51859,22288,51855,49653,58466,22295,22295,22484,22299,22833,22516,22281,22826,
       22301,58463,58464,51857,22827,57226,22393,22752,59242,22547,48954,22816,22075,22284,22625,48878,49072,51666,57693
]

codes2=[]

codes3=[]

codes_kumho = []

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
                    sheet.cell(row=row_idx, column=col_idx).value = f'=MIN(N{row_idx}:P{row_idx})'     
                    #=IF(IF(MIN(Q{row_idx}:T{row_idx}) > 0, MIN(Q{row_idx}:T{row_idx}), "") = S{row_idx}, S{row_idx}, IF(MIN(Q{row_idx}:T{row_idx}) > 0, MIN(Q{row_idx}:T{row_idx}), "") * (1-IF(ISNUMBER($U$13), $U$13, 0)))
                elif header == "PRECIO CON DESCUENTOS":
                    sheet.cell(row=row_idx, column=col_idx).value = f'=Q{row_idx}-(IF(IF(MIN(N{row_idx}:P{row_idx}) > 0, MIN(N{row_idx}:P{row_idx}), 0) = O{row_idx}, 0, (IF(MIN(N{row_idx}:P{row_idx}) > 0, MIN(N{row_idx}:P{row_idx}), 0) * (IF(ISNUMBER($C$6), $C$6, 0)))))-(Q{row_idx}*$C$8)-(IF(OR(H{row_idx}="ONYX", H{row_idx}="DOUBLESTAR", H{row_idx}="DELINTE", H{row_idx}="FIREMAX", H{row_idx}="APTANY"), (Q{row_idx}*$C$11), 0)) - (Q{row_idx}*$C$7) - (IF(H{row_idx} = "MILESTAR", (Q{row_idx}*$C$12), 0))'                                              
                                                                      
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
                    sheet.cell(row=row_idx, column=col_idx).value = f'=MIN(N{row_idx}:P{row_idx})'     
                    #=IF(IF(MIN(Q{row_idx}:T{row_idx}) > 0, MIN(Q{row_idx}:T{row_idx}), "") = S{row_idx}, S{row_idx}, IF(MIN(Q{row_idx}:T{row_idx}) > 0, MIN(Q{row_idx}:T{row_idx}), "") * (1-IF(ISNUMBER($U$13), $U$13, 0)))
                elif header == "PRECIO CON DESCUENTOS":
                    sheet.cell(row=row_idx, column=col_idx).value = f'=(W{row_idx}-(W{row_idx}*$C$6)-(W{row_idx}*$C$7)-(W{row_idx}*$C$8)-(R{row_idx})) - V{row_idx} - IF(O{row_idx} = (W{row_idx} * 0.9), W{row_idx}*0.1, 0)'
                    #=IF($Y$11 = "", (U{row_idx} * (1 - $W$13)), (V{row_idx} * (1 - $W$13)))
                    #=(Q{row_idx}-(MIN(O{row_idx}:P{row_idx})  * (IF(ISNUMBER($C$6), $C$6, 0)))-(Q{row_idx}*$C$7)-(Q{row_idx}*$C$8)-(R{row_idx})) - V{row_idx}
                elif header == "PROMO BS":
                    sheet.cell(row=row_idx, column=col_idx).value = f'=IF(N{row_idx} = "SI", W{row_idx}*$L$12, 0)'
                elif header == "PESOS":
                    sheet.cell(row=row_idx, column=col_idx).value = f'=IF(T{row_idx} = "", "", T{row_idx}*W{row_idx})'                                          
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
        outlet_col_idx = column_index_from_string('O')  # Replace 'A' with actual column letter for 'Outlet'
        ids_in_codes_brig = column_index_from_string('H')
        # Define el rango de celdas que deseas pintar
        outlet_start_column = 'Q'
        outlet_end_column = 'S'
        
        t4_col_idx = column_index_from_string('B')
        tier4_col_idx = column_index_from_string('H')
        
        milestar_col_idx = column_index_from_string('H')
        start_column = 'A'
        end_column = 'S'
        
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
                
            if tier4_cell.value in ['DOUBLESTAR', 'DELINTE', 'FIREMAX', 'APTANY', 'ONYX']:
                t4_cell.fill = PatternFill(start_color='DAEEF3', end_color='DAEEF3', fill_type='solid')
                    
        for row in sheet.iter_rows(min_row=15):
            milestar_cell = row[milestar_col_idx - 1]
            for col in range(ord(start_column), ord(end_column) + 1):
                if milestar_cell.value in ['MILESTAR']:
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
                    'Tipo': obj.product_id.type_id.name or None,
                    'Seg': obj.product_id.segment_id.name or None,
                    'Tier': obj.tier_id.name if obj.tier_id else None,
                    'Inv.': obj.inventario_str,
                    #'Cantidad Disponible': obj.available,
                    #'Trans.': (obj.transito_str + obj.backorder_str) or None,
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
                    'Mayoreo': (obj.volumen * 1.16) * 0.9,
                    'Promo Dot': obj.promo_dot * 1.16,
                    'Mejor Condición': "",
                    'PROMO BS': "",
                    'PRECIO CON DESCUENTOS': "",
                    'PIEZAS': "",
                    'PESOS': "",
                })
                if self.partner_id:
                    if obj.product_id.id in [22094,22356,22086,48697,22605,22814,49875,22175,58485,22170,22785]:
                        data_dict.update({'Cupones': '80'})
                    elif obj.product_id.id in [22804,22712,22299,22288,22826]:
                        data_dict.update({'Cupones': '120'})
                    elif obj.product_id.id in [22260,22518,22604]:
                        data_dict.update({'Cupones': '150'})
                    elif obj.product_id.id in [51857]:
                        data_dict.update({'Cupones': '180'})
                    else:
                        data_dict.update({'Cupones': ''})
                
                if obj.volumen > 0:
                    data_dict.update({
                        'PRECIO FACTURA': (obj.volumen * 1.16)
                    })
                else:
                    data_dict.update({
                        'PRECIO FACTURA': obj.promo_dot * 1.16
                    })
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
                'Tipo': obj.product_id.type_id.name or None,
                'Seg': obj.product_id.segment_id.name or None,
                'Tier': obj.tier_id.name if obj.tier_id else None,
                'Inv.': obj.inventario_str,
                #'Cantidad Disponible': obj.available,
                #'Trans.': (obj.transito_str + obj.backorder_str) or None,
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
        
        bs_percent = ['0%','4%','6%','8%','10%']
        t4_percent = ['0%','2%','4%','6%']
        milestar_bonuses = ['0%','2%','3%']
         
        combo_data_sheet1 = [
            {'cell_ref': 'C6', 'values': logistic_percent},
            {'cell_ref': 'C7', 'values': volume_percent},
            {'cell_ref': 'C8', 'values': financial_percent},
            {'cell_ref': 'C11', 'values': t4_percent},
            {'cell_ref': 'C12', 'values': milestar_bonuses},
        ]
        
        combo_data_sheet3 = [
            {'cell_ref': 'C6', 'values': logistic_percent},
            {'cell_ref': 'C7', 'values': volume_percent},
            {'cell_ref': 'C8', 'values': financial_percent},
            {'cell_ref': 'L12', 'values': bs_percent}
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
            {'cell_ref': 'A5:F5', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': '595959', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "CONDICIONES:", 'data_type': 'string'},
            {'cell_ref': 'A6:B6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Logístico", 'data_type': 'string'},
            {'cell_ref': 'A7:B7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Volumen", 'data_type': 'string'},
            {'cell_ref': 'A8:B8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Financiero", 'data_type': 'string'},
            {'cell_ref': 'A9:F9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'FDFFCD', 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Códigos en los que no aplica desc. logístico", 'data_type': 'string'},
            {'cell_ref': 'A10:F10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': False, 'fill_color': '595959', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "PROMOCIONES:", 'data_type': 'string'},
            {'cell_ref': 'A11:B11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'DDE5F2', 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "TIER 4", 'data_type': 'string'},
            {'cell_ref': 'A12:B12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': 'BFBFBF', 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "MILESTAR", 'data_type': 'string'},
            {'cell_ref': 'Q11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': False, 'fill_color': WHITE, 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "BRIDGESTONE", 'data_type': 'string'},
            {'cell_ref': 'D6:F6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=IF(C6 = 4%, "Min 300 pz x envío", IF(C6 = 2%, "Min 100 pz x envío", "0-99 pz x envío"))"""},
            {'cell_ref': 'D7:F7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=IF(C7 = 3%, "Min 600 pz mensuales", IF(C7 = 2%, "Min 400 pz mensuales", "0-399 pz mensuales"))"""},
            {'cell_ref': 'D8:F8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "Pagando en tiempo sus facturas.", 'data_type': 'string'},
            {'cell_ref': 'D11:F11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'DDE5F2', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=IF(C11 = 6%, "Min 150 pz mensuales", IF(C11 = 4%, "Min 100 pz mensuales", IF(C11 = 2%, "Min 50 pz mensuales", "0-49 pz mensuales")))"""},
            {'cell_ref': 'D12:F12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'BFBFBF', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=IF(C12=3%, "Min 350Pz, Iphone 14 Ó Galaxy Z Flip", IF(C12 = 2%, "Min 180Pz, Galaxy Wath 7 ó Apple Watch SE", "No aplica promoción"))"""},
            
            
            {'cell_ref': 'G5', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "TOTAL LLANTAS", 'data_type': 'string'},
            {'cell_ref': 'G6:G7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=SUM(S15:S{num_rows_1})+SUM('P. BRIDGESTONE'!T15:T{num_rows_1})"""},
            {'cell_ref': 'G10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "TOTAL LLANTAS", 'data_type': 'string'},
            {'cell_ref': 'G11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'DDE5F2', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=SUMIFS(S15:S{num_rows_1},H15:H{num_rows_1},"TIER 4")"""},
            {'cell_ref': 'G12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'BFBFBF', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=SUMIFS(S15:S{num_rows_1},H15:H{num_rows_1},"MILESTAR")"""},

            {'cell_ref': 'C6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
            {'cell_ref': 'C7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
            {'cell_ref': 'C8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
            {'cell_ref': 'C11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'DDE5F2', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
            {'cell_ref': 'C12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'BFBFBF', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},

            {'cell_ref': 'R11:S11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '$#,##0.00', 'value': "Consulte segunda hoja", 'data_type': 'string'},

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
            {'cell_ref': 'R14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': 'FF0000', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
            {'cell_ref': 'S14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
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
        self.format_column(sheet1,'N','currency')
        self.format_column(sheet1,'O','currency')
        self.format_column(sheet1,'P','currency')
        self.format_column(sheet1,'Q','currency')
        self.format_column(sheet1,'R','currency')
        self.format_column(sheet1,'S','number')
        
        columna_a_ocultar_sheet1 = ['A', 'N', 'O', 'P', 'T']
        
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
        end_col = 'S'   
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
            self.set_combos(sheet3, combo_data_sheet3) 
            num_rows_3, num_cols_3 = self.insert_table_sheet3(sheet3, promo_bridgestone, "TablaDatos3")
            self.set_frames(sheet3)
            sheet3.sheet_properties.tabColor = 'E6B8B8'
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
                {'cell_ref': 'R14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'S14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': RED, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'T14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'U14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': DARK_GRAY, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                {'cell_ref': 'V14', 'font_name': 'Calibri', 'font_size': 11, 'font_color': 'C00000', 'bold': True, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'data_type': 'string'},
                
                {'cell_ref': 'S12:V13', 'font_name': 'Calibri', 'font_size': 11, 'font_color': 'C00000', 'bold': True, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': True, 'num_format': '#,##0.00', 'value': "VALOR CUPON YA DESCONTADO EN PRECIO CON DESCUENTO", 'data_type': 'string'},
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
                {'cell_ref': 'G6:G7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': f"""=SUM(T15:T{num_rows_3})+SUM('Precios Con Iva'!S15:S{num_rows_1})"""},
                {'cell_ref': 'C6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
                {'cell_ref': 'C7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
                {'cell_ref': 'C8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
                
                {'cell_ref': 'J4:M4', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0', 'value': "PROMOCIÓN:", 'data_type': 'string'},
                
                {'cell_ref': 'J5:K5', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "Monto neto mensual", 'data_type': 'string'},
                {'cell_ref': 'L5', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "Desc", 'data_type': 'string'},
                {'cell_ref': 'M5', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "ADICIONAL", 'data_type': 'string'},
                
                {'cell_ref': 'J6:K6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "$0 a $46,399", 'data_type': 'string'},
                {'cell_ref': 'L6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "0%", 'data_type': 'string'},
                {'cell_ref': 'M6', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "", 'data_type': 'string'},
                
                {'cell_ref': 'J7:K7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "$46,400 a $115,999", 'data_type': 'string'},
                {'cell_ref': 'L7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "4%", 'data_type': 'string'},
                {'cell_ref': 'M7', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "", 'data_type': 'string'},
                
                {'cell_ref': 'J8:K8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "$116,000 a $347,999", 'data_type': 'string'},
                {'cell_ref': 'L8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "6%", 'data_type': 'string'},
                {'cell_ref': 'M8', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "", 'data_type': 'string'},
                
                {'cell_ref': 'J9:K9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "$348,000 a $927,999", 'data_type': 'string'},
                {'cell_ref': 'L9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "8%", 'data_type': 'string'},
                {'cell_ref': 'M9', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "", 'data_type': 'string'},
                
                {'cell_ref': 'J10:K10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "Más de $928,000", 'data_type': 'string'},
                {'cell_ref': 'L10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "10%", 'data_type': 'string'},
                {'cell_ref': 'M10', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "", 'data_type': 'string'},
                
                {'cell_ref': 'A11:E12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': 'C00000', 'bold': True, 'fill_color': 'D9D9D9', 'border': 'thin', 'align': 'left', 'top_align': 'center', 'wrap_text': True, 'num_format': '$#,##0.00', 'value': "Códigos que otorgan el descuento del cupón señalado ya reflejado en el precio. Máx. 200 x medida x RFC.", 'data_type': 'string'},
                {'cell_ref': 'F11:G11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': 'F2F2F2', 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "ACUMULADO TOTAL", 'data_type': 'string'},
                {'cell_ref': 'F12:G12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': BLACK, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '$#,##0.00', 'value': f"""=SUM(U15:U{num_rows_3})""", 'data_type': '$0'},
                {'cell_ref': 'H11:K11', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': BLACK, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '#,##0.00', 'value': "ACUMULADO PROMO", 'data_type': 'string'},
                {'cell_ref': 'H12:K12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': RED, 'bold': True, 'fill_color': WHITE, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '$#,##0.00', 'value': f"""=SUMIFS(U15:U{num_rows_3},N15:N{num_rows_3},"SI")""", 'data_type': '$0'},
                
                {'cell_ref': 'L12', 'font_name': 'Calibri', 'font_size': 11, 'font_color': WHITE, 'bold': True, 'fill_color': RED, 'border': 'thin', 'align': 'center', 'top_align': 'center', 'wrap_text': False, 'num_format': '0%', 'value': "0%"},
                ]

            # Formatear las celdas para la hoja 3
            for data in data_for_sheet3:
                self.format_cell(sheet3, **data)
            for data in promobrid:
                self.format_cell(sheet3, **data)
                
            # Lista de hojas a formatear
            sheets = [sheet3]

            # Diccionario que define las columnas y sus formatos
            formats = {
                'string': ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'P', 'W'],
                'number': ['T'],
                'currency': ['O', 'P', 'Q', 'R', 'S', 'U', 'V']
            }
            
            #-------- Ocultar columnas ----------------------
            # Seleccionar la hoja que deseas ocultar
            # sheet = wb['P. BRIDGESTONE']
            # Para ocultar la hoja:
            # sheet.sheet_state = 'hidden'
            
            columna_a_ocultar_sheet3 = ['A', 'N', 'O', 'P', 'R', 'U', 'W']
            
            # Itera sobre cada hoja
            for sheet in sheets:
                start_row = 14
                end_row = num_rows_3
                start_col = 'A'
                end_col = 'V'
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