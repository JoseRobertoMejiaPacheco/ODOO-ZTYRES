# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
import pandas as pd
from datetime import date

class Report(models.TransientModel):
    _name = 'payment_ap_report.report'
    _description = 'Reporte de aplicacion de pagos'
    _rec_name = 'partner_id'
    partner_id = fields.Many2one('res.partner',string='Cliente')
    invoice_id = fields.Many2one('account.move',string='Factura')
    total = fields.Float(string='Total')
    amount_pending = fields.Float(string='Saldo Pendiente')
    ref = fields.Char(string='Ref')
    amount_paid = fields.Float(string='Monto abonado')
    date = fields.Date(string='Fecha')
    payment_id = fields.Many2one('account.move',string='Documento/Pago')
    
    def delete_all_records(self):
        self.search([]).unlink()

    def generate_report_data(self,partner_ids):
        account_move = self.env['account.move'].search([('partner_id','in',partner_ids),('state','in',['posted']),('move_type','in',['out_invoice'])])
        report_data = []
        err = []

        for invoice in account_move:
            vals = {
                'Cliente': invoice.partner_id.id,  # Valor predeterminado ''
                'Factura': invoice.id,  # Valor predeterminado ''
                'Total': invoice.amount_total,
                'Saldo Pendiente': invoice.amount_residual,
                'Pagos': []  # Inicializa la lista de pagos aquí
            }
            
            if invoice.invoice_payments_widget and invoice.invoice_payments_widget.get("content"):
                for item in invoice.invoice_payments_widget["content"]:
                    if item.get("move_id"):
                        move = self.env['account.move'].browse(item["move_id"])
                        vals_pagos = {
                            'Ref': item.get("name"),
                            'Monto abonado': item.get("amount"),
                            'Fecha': item.get("date"),
                            'payment_id': move.id
                        }
                        vals['Pagos'].append(vals_pagos)  # Agrega los datos de pagos a la lista de pagos en 'vals'
            else:
                vals_pagos = {
                                    'Ref': '',
                                    'Monto abonado':  0,
                                    'Fecha': False,
                                    'payment_id': False
                                }
                vals['Pagos'].append(vals_pagos) 
                err.append(invoice.name)
            report_data.append(vals)

        # Crear un DataFrame a partir de report_data
        data_for_dataframe = []
        for factura in report_data:
            for pago in factura['Pagos']:
                data_for_dataframe.append({
                    "partner_id": factura["Cliente"],
                    "invoice_id": factura["Factura"],
                    "total": factura["Total"],
                    "amount_pending": factura["Saldo Pendiente"],
                    "ref": pago["Ref"],
                    "amount_paid": pago["Monto abonado"],
                    "date": pago["Fecha"],
                    "payment_id": pago["payment_id"],
                })
        return data_for_dataframe

    def get_report_views(self):
        views = [
            (self.env.ref('payment_ap_report.report_tree').id, 'list'),
            (self.env.ref('payment_ap_report.report_view_form').id, 'form'),
            (self.env.ref('payment_ap_report.report_pivot').id, 'pivot')
        ]
        return {
            'name': 'Reporte de aplicación de pagos',
            'view_type': 'form',
            'view_mode': 'tree,form,pivot',  # Corregido: Cambiado a una lista de cadenas
            'res_model': 'payment_ap_report.report',
            'views': views,
            # 'domain': [],
            'type': 'ir.actions.act_window',
        }

    def generate_report(self,partner_ids):
        report_data = self.generate_report_data(partner_ids)
        self.create(report_data)

    def get_report(self,partner_ids):
        self.delete_all_records()
        self.generate_report(partner_ids)
        return self.get_report_views()

    def payment_ap_report_wizard(self):
        views = [(self.env.ref('payment_ap_report.report_wizard').id, 'form')]
        return {
                'name': 'Reporte de aplicacion de pagos',
                'view_type': 'form',
                "view_mode": "form",
                "res_model": "payment_ap_report.wizard",
                'views': views,
                'domain': [],
                'target': 'new',
                'type': 'ir.actions.act_window',
            }