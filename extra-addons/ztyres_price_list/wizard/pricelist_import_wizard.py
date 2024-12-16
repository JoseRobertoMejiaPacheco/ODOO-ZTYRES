from odoo import models, fields,_
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
        "The `openpyxl` Python module is not available. "
        "Phone number validation will be skipped. "
        "Try `pip3 install openpyxl` to install it."
    )
class ImportCustomerWizard(models.TransientModel):
    _name = "ztyres_price_list.pricelist_import_wizard"
    file = fields.Binary(string="File", required=True)
    pricelist_ids = fields.Many2many('product.pricelist', string='Lista de Precios destino',required=True)    
    options = fields.Selection(
        string='Opciones de carga de precios',
        selection=[('replace', 'Reemplazar precios si existen y crear nuevos precios si no existen.'),('delete all', 'Borrar todo y dejar los únicamente los precios cargados.'),('delete', 'Borrar solo los incluidos en la lista.')],required=True        
    )
    upload_options = fields.Selection(
        string='Campo de referencia',
        selection=[('name', 'Nombre'), ('code', 'Código de referencia'),('id', 'ID')],required=True        
    )    
    

    def import_prices(self):
        try:
            if self.options == 'delete all':
                self.pricelist_ids.ensure_one()
                self.pricelist_ids.item_ids.unlink()
            if _openpyxl_lib_imported:
                    
                wb = openpyxl.load_workbook(filename=BytesIO(base64.b64decode(self.file)), read_only=True)
                ws = wb.active                
                for record in ws.iter_rows(min_row=2, max_row=None, min_col=None,max_col=None, values_only=True):
                    if record[0] and  record[1]:                    
                   #    TODO Usar filtered para mejorar el performance
                        product_tmpl_id = False
                        domain = [('pricelist_id','in',[self.pricelist_ids.id])]
                        if self.upload_options == 'name':
                                add_domain = (('name','in',[str(record[0])]))                            
                                product_tmpl_id = self.pricelist_ids.item_ids.product_tmpl_id.with_context(active_test=True).search([add_domain])
                        elif self.upload_options == 'code':
                            add_domain = (('default_code','in',[str(record[0])]))                            
                            product_tmpl_id = self.pricelist_ids.item_ids.product_tmpl_id.with_context(active_test=True).search([add_domain])                           
                        elif self.upload_options == 'id':
                                add_domain = (('id','in',[int(record[0])]))                            
                                product_tmpl_id = self.pricelist_ids.item_ids.product_tmpl_id.with_context(active_test=True).search([add_domain])
                        if not product_tmpl_id:
                            raise UserError(_('El producto que desea subir no existe %s'%(record[0])))
                        if len(product_tmpl_id)>1:
                            raise UserError(_('El producto se encuentra duplicado %s'%(record[0])))
                        domain.append(('product_tmpl_id','in',product_tmpl_id.ids))
                        
                        if len(record)==3:
                            if record[2]:
                                domain.append(('lot_name','in',[record[2]]))
                        product = self.pricelist_ids.item_ids.with_context(active_test=True).search(domain)
                        if product and self.options == 'delete':
                                product.unlink()
                                continue                                       
                        if product:
                            product.fixed_price = float(record[1])                                    
                        else:
                            vals = {
                            "applied_on": "1_product",
                            "product_tmpl_id": product_tmpl_id.id,
                            "pricelist_id": self.pricelist_ids.id,
                            "compute_price": "fixed",
                            "fixed_price":float(record[1])                                
                            }
                            if len(record)==3:
                                vals.update({

                            "lot_name":record[2],
                            })
                            res = self.pricelist_ids.item_ids.create(vals)
                            if not res:
                                raise UserError(_('No se encontro el prodcuto con referencia %s'%(record[0])))
                            
                                  
                return {
                    'name': _('Listas de Precios'),
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'product.pricelist',
                    'res_id': self.pricelist_ids.id                    
                }                                                                  
                    # search if the price exist else create
        except Exception as e:
            raise UserError(_('El archivo no es válido %s'%(e)))
        
#/mnt/extra-addons/ztyres_price_list/wizard/pricelist_import_wizard.py