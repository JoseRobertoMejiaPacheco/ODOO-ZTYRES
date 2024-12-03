# -*- coding: utf-8 -*-
from odoo import models, fields, _,api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    def update_costo_final(self):
        for po in self.with_progress(msg="Actualizando Costo Final :3"):
            for invoice_line in po.invoice_ids.invoice_line_ids:
                # Obtener el costo final de la factura
                costo_final_factura_lista =  po.order_line.filtered(lambda line: line.product_id.id == invoice_line.product_id.id
                                                                        and line.x_studio_costo_final not in [0, 0.0]).mapped('x_studio_costo_final')
                print(costo_final_factura_lista)
                if costo_final_factura_lista:
                    costo_final_factura_lista = sum(costo_final_factura_lista) / len(costo_final_factura_lista)
                    # Si la lista no está vacía, obtener el máximo valor
                    invoice_line.costo_final = costo_final_factura_lista   