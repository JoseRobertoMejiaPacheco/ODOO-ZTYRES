# -*- coding: utf-8 -*-
from odoo import models, fields,api
import datetime
class Product(models.Model):
    _inherit = 'product.product'
    
    dot_range = fields.Char(compute='_compute_dot_range', string='DOT')
    
    def obtener_anos(self,numero):
        if not self.qty_available >0:
            return False
        dots =[
        ]
        for dot in dots:
            if dot[0] == self.id:
                anos = sorted(dot[1])  # Ordena los años
                if len(anos) > 1:
                    return f"{anos[0]}-{anos[-1]}"
                elif len(anos) == 1:
                    return f"{anos[-1]}"
        return False
    

    def _compute_dot_range(self):
        for record in self:
            if not record.qty_available>0:
                record.dot_range = ''
            elif record.qty_available >0:
                lots = []
                if record.estado_conteo_dot == 'done':
                    x = self.env['stock.quant'].search([('product_id', 'in', record.ids), 
                                            ('quantity', '>', 0), 
                                            ('location_id.usage', '=', 'internal')])
                    print(x)
                    lots = self.env['stock.quant'].search([('product_id', 'in', record.ids), 
                                            ('quantity', '>', 0), 
                                            ('location_id.usage', '=', 'internal')]).mapped('lot_id.name')  
                
                product_lot = self.env['stock.lot']
                res_1 = record.obtener_anos(record.id)
                
                if not res_1:
                    record.dot_range = 'N/A'
                    if not lots:
                        lots = product_lot.search([('product_id', 'in', [record.id])]).mapped('name')
                    if lots:
                        try:
                            arr_dict = []
                            for item in lots:
                                if len(item) >= 2:
                                    year = int(item[-2:])
                                    arr_dict.append(year)
                            
                            if arr_dict:
                                sorted_years = sorted(arr_dict)
                                
                                max_dot = sorted_years[-1]
                                min_dot = sorted_years[0]
                                
                                # Obtener el año actual
                                current_year = datetime.datetime.now().year
                                current_century = (current_year // 100) * 100
                                
                                # Convertir los años de dos dígitos a años completos
                                max_year = current_century + max_dot if max_dot <= current_year % 100 else current_century - 100 + max_dot
                                min_year = current_century + min_dot if min_dot <= current_year % 100 else current_century - 100 + min_dot
                                
                                if max_year == min_year:
                                    record.dot_range = '%s' % (max_year)
                                else:
                                    record.dot_range = '%s-%s' % (min_year, max_year)
                            else:
                                record.dot_range = 'N/A'
                        except Exception as e:
                            print('Error de DOT en producto: %s' % e)
                            record.dot_range = 'N/A'
                    else:
                        record.dot_range = 'N/A'
                else:
                    record.dot_range = res_1

