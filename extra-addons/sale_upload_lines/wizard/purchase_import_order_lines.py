from odoo import models, fields,_,api
import logging
import base64
from io import BytesIO
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)

try:
    import openpyxl
    _openpyxl_lib_imported = True

except ImportError:
    _openpyxl_lib_imported = False
    _logger.info(
        "The `openpyxl` Python module is not available."
        "Phone number validation will be skipped."
        "Try `pip3 install openpyxl` to install it."
    )
    
class PurchaseOrderImport(models.TransientModel):
    _name = 'purchase.import_order_lines'
    _description = 'Cargar líneas de pedido de compra'
    file = fields.Binary(string='Archivo',required=True)
    upload_options = fields.Selection(
        string='Campo de referencia',
        selection=[('name', 'Nombre'), ('default_code', 'Código de referencia'),('product_tmpl_id', 'ID')],required=True        
    )
    def unlink_duplicate_products(self,order_lines,id):
        return order_lines.filtered(lambda line: line.product_id.id == id).unlink()
        
    def search_product_by_key(self,field,value):
        product = self.env['product.product']
        res = product.search([(field,'in',[value])])
        if not len(res)==1:
            raise UserError(_('Por favor asegurese de que el producto exista y no esté duplicado %s %s'%(res.mapped('id'),value)))
        else:
            return res.id
                    
    @api.model
    def create(self, values):
        order_id = self.env[self._context['active_model']].browse(self._context['active_id'])        
        try:
            if _openpyxl_lib_imported:                    
                wb = openpyxl.load_workbook(filename=BytesIO(base64.b64decode(values.get('file'))), read_only=True)
                ws = wb.active  
                upload_options =  values.get('upload_options')
                vals = []             
                for record in ws.iter_rows(min_row=2, max_row=None, min_col=None,max_col=None, values_only=True):
                    product_id = self.search_product_by_key(upload_options,record[0])
                    self.unlink_duplicate_products(order_id.order_line,product_id)
                    line = {
                        "product_id": product_id,
                        "product_qty": record[2],
                        "price_unit": record[1],
                        "x_studio_costo_final": record[3]
                        }
                    vals.append((0,0,line))
                order_id.order_line = vals
            return super(PurchaseOrderImport, self).create(values)
                                                                                       
                    # search if the price exist else create
        except Exception as e:
            raise UserError(_('El archivo no es válido %s'%(e)))



