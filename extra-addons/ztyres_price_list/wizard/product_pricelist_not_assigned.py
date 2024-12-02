# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
import pandas as pd
from io import BytesIO
import base64

class NotAssigned(models.TransientModel):
    _name = 'product_pricelist.not_assigned'
    _description = 'Descarga de reporte de productos sin precio'

    name = fields.Char(string='')
    attachment_id = fields.Many2one('ir.attachment', string='Archivo Excel')

    def generate_report(self):
        product_obj = self.env['product.template']
        pricelist_obj = self.env['product.pricelist']
        active_pricelist_ids = [1,108,113]
        all_products_with_price = pricelist_obj.browse(active_pricelist_ids).mapped('item_ids').mapped('product_tmpl_id').ids
        data = []
        all_products = product_obj.search([('detailed_type','in',['product'])])
        for product_id in all_products:
            if product_id.qty_available > 0:
                if product_id.id not in all_products_with_price:
                    data.append({
                        'Id': product_id.id,
                        'Referencia': product_id.default_code,
                        'Nombre': product_id.name,
                        'Cantidad Disponible': product_id.qty_available
                    })
        # Convertir los datos a DataFrame
        df = pd.DataFrame(data)
        output = BytesIO()
        df.to_excel(output, index=False, sheet_name='Productos sin Precio')  # index=False para evitar incluir el índice del DataFrame
        output.seek(0)  # Vuelve al inicio del archivo en memoria
        # Convertir el contenido del archivo Excel a base64
        encoded_data = base64.b64encode(output.getvalue())
        # Crear el adjunto
        attachment = self.env['ir.attachment'].create({
            'name': 'reporte_productos_sin_precio.xls',
            'type': 'binary',
            'datas': encoded_data,
            'store_fname': 'reporte_productos_sin_precio.xls',
            'mimetype': 'application/vnd.ms-excel',
            'res_model': self._name,
            'res_id': self.id,
        })
        # Devolver una acción para descargar directamente el archivo
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        download_url = '{}/web/content/ir.attachment/{}/datas'.format(base_url, attachment.id)
        return {
            'type': 'ir.actions.act_url',
            'url': download_url,
            'target': 'new',
        }