from odoo import models, fields, api, _
from odoo.exceptions import UserError

import io
import base64

class CouponExcelWizard(models.TransientModel):
    _name = 'ztyres_promo.coupon_excel_wizard'
    _description = 'Wizard para importar cupones desde Excel'
    
    file = fields.Binary(
        string='Archivo Excel',
        required=True,
        help='Suba el archivo Excel con los códigos de producto y montos'
    )
    file_name = fields.Char(string="Nombre del archivo")
    notas_credito_id = fields.Many2one(
        'ztyres_promo.notas_credito',
        string='Nota de Crédito',
        required=True
    )
    
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
            if 'codigo' not in excel_data.columns or 'monto' not in excel_data.columns:
                raise UserError(_("El archivo debe contener las columnas 'codigo' y 'monto'."))
            
            # Limpiar datos
            excel_data = excel_data.dropna(subset=['codigo', 'monto'])
            excel_data['codigo'] = excel_data['codigo'].astype(str).str.strip()
            excel_data['monto'] = pd.to_numeric(excel_data['monto'], errors='coerce')
            
            # Eliminar filas con montos inválidos
            excel_data = excel_data.dropna(subset=['monto'])
            
            # Buscar productos
            product_obj = self.env['product.template']
            coupon_obj = self.env['ztyres_promo.coupon']
            
            created_coupons = 0
            missing_codes = []
            
            for index, row in excel_data.iterrows():
                codigo = row['codigo']
                monto = row['monto']
                
                # Buscar producto por código
                product = product_obj.search([('default_code', '=', codigo)], limit=1)
                
                if product:
                    # Crear cupón
                    coupon_obj.create({
                        'product_id': product.id,
                        'amount': monto,
                        'notas_credito_id': self.notas_credito_id.id
                    })
                    created_coupons += 1
                else:
                    missing_codes.append(codigo)
            
            # Preparar mensaje de resultado
            message = _('Se crearon %d cupones correctamente.') % created_coupons
            if missing_codes:
                message += _('\n\nProductos no encontrados (%d): %s') % (
                    len(missing_codes), 
                    ', '.join(missing_codes[:10]) + ('...' if len(missing_codes) > 10 else '')
                )
            
            # Retornar resultado
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Importación Completada'),
                    'message': message,
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
            
        except UserError:
            raise
        except Exception as e:
            raise UserError("Error al procesar el archivo: %s" % str(e))