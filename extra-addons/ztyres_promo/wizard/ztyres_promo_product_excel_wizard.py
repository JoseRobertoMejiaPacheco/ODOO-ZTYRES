from odoo import models, fields, api, _
from odoo.exceptions import UserError

import io
import base64

class ProductExcelWizard(models.TransientModel):
    _name = 'ztyres_promo.product_excel_wizard'
    _description = 'Wizard para importar productos desde Excel'
    
    file = fields.Binary(
        string='Archivo Excel',
        required=True,
        help='Suba el archivo Excel con los códigos de producto'
    )
    file_name = fields.Char(string="Nombre del archivo")
    
    def action_import(self):
        self.ensure_one()
        if not self.file:
            raise UserError(_("Debe subir un archivo Excel."))
        
        try:
            import pandas as pd
            # Leer el archivo Excel
            file_content = base64.b64decode(self.file)
            excel_data = pd.read_excel(io.BytesIO(file_content))
            
            # Validar estructura básica
            if 'codigo' not in excel_data.columns:
                raise UserError(_("El archivo debe contener solo una columna llamada 'codigo'."))
            
            # Procesar códigos de productos
            product_obj = self.env['product.template']
            product_codes = excel_data['codigo'].dropna().astype(str).str.strip().unique()
            
            # Buscar productos existentes
            products = product_obj.search([('default_code', 'in', list(product_codes))])
            
            found_codes = products.mapped('default_code')
            missing_codes = set(product_codes) - set(found_codes)
            self.env[self._context.get('default_res_model')].browse(self._context.get('default_res_id')).write({'product_ids': [(6, 0, products.ids)],'not_found':missing_codes})            
            
            # Retornar resultado
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Éxito'),
                    'message': _('Se procesaron %d productos correctamente.') % len(products),
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        except Exception as e:
            raise UserError(_("Error al procesar el archivo: %s") % str(e))