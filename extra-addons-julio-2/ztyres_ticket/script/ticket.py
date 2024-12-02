from fpdf import FPDF
import base64
from odoo import fields
import pytz


class Ticket(FPDF):

    def __init__(self, data,heigth):
        self.heigth = heigth  
        self.data = data              
        super().__init__('P', 'mm', (77,heigth))
        self.add_page()   
        
        
    WIDTH = 77
    HEIGHT = 297




    def header2(self):        
        self.image('/mnt/extra-addons/ztyres_ticket/src/assets/logo.png', 5, 10, self.WIDTH/6, self.HEIGHT/10)
        self.set_font('Arial', '', 8)
        self.cell(30)
        self.cell(20, 5, 'ZTYRES', 0, 0, 'R')
        self.ln(3)
        self.cell(30)
        self.cell(20, 5, 'Carretera León Lagos', 0, 0, 'R')
        self.ln(3)
        self.cell(30)
        self.cell(20, 5, '2237A/4 37690', 0, 0, 'R')
        self.ln(3)
        self.cell(30)
        self.cell(20, 5, 'León, Guanajuato', 0, 0, 'R')
        self.ln(3)
        self.cell(30)
        self.cell(20, 5, 'Teléfono: 4771023900', 0, 0, 'R')
        self.ln(10)
        # Agrega el título
        self.set_font('Arial', 'B', 12)
        self.cell(self.WIDTH - 50)
        self.cell(20, 5,self.data.sale_id.name or '', 1, 0, 'C')
        self.ln(5)
        self.cell(30)
        self.set_font('Arial', 'B', 10)
        self.cell(20, 5,self.data.name, 0, 0, 'R')
        self.ln(5)


   
    def body2(self):
        products = self.get_dict_data()        
        self.set_margins(0,0)
        self.set_font("Arial", "", 8) 
        tz = pytz.timezone(self.data.env.context.get('tz') or 'UTC')
        self.multi_cell(80, 5, 'Fecha y hora: %s'%(pytz.utc.localize(fields.datetime.now()).astimezone(tz).strftime("%d/%m/%Y %H:%M:%S")), border=0,align='L')
        self.set_font("Arial", "", 8)        
        for product in products:
            if 'total de llantas' in product:
                self.set_font('Arial', 'B', 11)
                self.multi_cell(70, 3, 'Total de llantas: %s'%(product['total de llantas']), border=0, align='R')
            else:
                self.cell(80, 0.1, '', border='B', ln=.2)
                self.multi_cell(80, 3, 'SKU:  %s\nMarca:  %s\nModelo:  %s\nMedida:  %s\nCapas:  %s\nCantidad:  %s\nUbicación:  %s'%(product['sku'],product['marca'],product['modelo'],product['medida'],product['capas'],product['cantidad'],product['ubicacion']), border=0)                
                self.ln(1)
        self.cell(80, 0.1, '', border='B', ln=.2)
    def get_dict_data(self):
        data = []        
        for line in sorted(self.data.move_line_ids_without_package, key=lambda x: x.product_id.brand_id.name):
            vals = {
                'sku':line.product_id.code,
                'capas':line.product_id.layer_id.name,
                'marca':line.product_id.brand_id.name,
                'modelo':line.product_id.model_id.name,
                'medida':line.product_id.tire_measure_id.name,
                'cantidad':line.reserved_uom_qty,
                'ubicacion':line.location_id.complete_name                
            }
            data.append(vals)
        data.append({'total de llantas':sum(self.data.move_line_ids_without_package.mapped('reserved_uom_qty'))})
        return data
                
    def get_base64_data(self): 
        self.header2()
        self.body2()
        self.set_auto_page_break(False)        
        pdf_bytes = self.output(dest='S').encode('latin-1')
        return  base64.b64encode(pdf_bytes).decode('utf-8')