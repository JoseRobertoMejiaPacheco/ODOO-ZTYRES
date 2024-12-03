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

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    costo_final = fields.Monetary(string='Costo Final',compute='_compute_costo_final', store=True, currency_field='currency_id')
    
    @api.depends('product_id')
    def _compute_costo_final(self):
        for line in self:
            costo_final_factura = line.move_id.purchase_id.order_line.filtered(lambda x: x.product_id.id == line.product_id.id).mapped('x_studio_costo_final')
            line.costo_final = costo_final_factura[0] if costo_final_factura else 0                    