#-*- coding: utf-8 -*-
from odoo import models, fields, api
from collections import defaultdict
import math
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.fields import Command


    def discount_increase(self,quotation=False):
        is_expo_values = self.line_ids.sale_line_ids.mapped('order_id').mapped('is_expo')
        if not any(is_expo_values):
            vals_for_credit_note = []
            promo_item = self.ahhh_group()
            for manufacturer_item in promo_item:
                description = f'PROMOCIÓN: {manufacturer_item[0].additional_discounts_id.name} PARTICIPANTES: {", ".join(manufacturer_item[0].manufacturer_id.mapped("name"))} CANTIDAD PARTICIPANTE: {manufacturer_item[1]}'
                monto = (manufacturer_item[0].discount_amount)/(1+(16/100))
                vals_for_credit_note.append((description,monto))                   
            logistic_discount,quantity_logistic,valid_lines = self.get_total_logistic_discount_line()
            if logistic_discount:
                if logistic_discount.discount > 0:
                    valid_lines = self.invoice_line_ids.filtered(lambda x: x.sale_line_ids.list_origin in logistic_discount.profile_logistic_discount_id.pricelist_ids.mapped('name') and x.product_id.id not in [50959])
                    price_subtotal = sum(valid_lines.mapped('price_subtotal'))
                    vals_for_credit_note.append((f'DESCUENTO: Logístico {logistic_discount.discount}% CANTIDAD PARTICIPANTE: {quantity_logistic}', price_subtotal * (logistic_discount.discount / 100)))
            lines_nc = []
            for description,amount in vals_for_credit_note:
                if amount>0:
                    print(amount)
                    print(round((amount/1.16),2))
                    lines_nc.append((0, 0, {
                            "product_id": 50785,
                            "quantity": 1,
                            'name': description,
                            "price_unit": round((amount),2),
                        }))
            if quotation:
                return lines_nc
            if lines_nc:
                credit_note_vals = {
                    'l10n_mx_edi_origin':f'01|{self.l10n_mx_edi_cfdi_uuid or ""}',
                    'move_type': 'out_refund',  
                    "x_studio_tipo": "Bonificación",
                    "generic_edi":self.generic_edi,
                    "invoice_date": fields.date.today().strftime(DEFAULT_SERVER_DATE_FORMAT),
                    "journal_id": 24,
                    "l10n_mx_edi_payment_method_id": 11, #Condonacion
                    "l10n_mx_edi_usage": "G02",# Devoluciones y Bonificaciones
                    "currency_id": self.env.company.currency_id.id,
                    "partner_id": self.partner_id.id,
                    "partner_shipping_id": self.partner_id.id,   
                        'invoice_line_ids': lines_nc,
                    }
                
                
                res = self.sudo().create(credit_note_vals)
                res.sudo().action_post()
                nc_credit_id = res.mapped('line_ids').filtered(lambda line: line.account_type == 'asset_receivable')
                invoice_debit_id = self.get_debit_move_id()
                apply_out_invoice = self.env['apply_out_invoice.payments']
                apply_out_invoice.sudo().create_partial_reconcile(
                    credit_move_id=nc_credit_id.id,
                    debit_move_id=invoice_debit_id.id,
                    amount=nc_credit_id.credit
                )
                self.credit_note_promo = res.id
                
