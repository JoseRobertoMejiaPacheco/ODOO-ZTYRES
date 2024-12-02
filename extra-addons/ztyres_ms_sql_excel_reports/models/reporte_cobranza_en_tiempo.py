from odoo import api, fields, models
import datetime
import pandas as pd


class ReservaCostoVentas(models.TransientModel):
    _name = 'reporte_cobranza_en_tiempo'
   
    def convert_to_company_currency(currency_id, amount, date):
        currency_record = self.env['res.currency'].browse(currency_id.id)
        converted_amount = currency_record._convert(
            amount,
            currency_record.env.company.currency_id,
            currency_record.env.company,
            date
        )
        return converted_amount if converted_amount else 0    
    
    def get_report(self):
        am = self.env['account.move']
        rp = self.env['res.partner'].search([('type', 'in', ['contact'])])
        report_data = []

        for partner_id in rp:
            out_invoices = partner_id.invoice_ids.filtered(lambda inv: inv.move_type == 'out_invoice')
            for invoice in out_invoices:
                if invoice.invoice_payments_widget and invoice.invoice_payments_widget.get("content"):
                    for item in invoice.invoice_payments_widget["content"]:
                        if item.get("move_id"):
                            move = self.env['account.move'].browse(item["move_id"])
                            mv = ''
                            if move.move_type == 'entry':
                                mv = 'Pago'
                            elif move.move_type == 'out_refund':
                                mv = 'Nota de Credito'
                            
                            vals = {
                                'ID': partner_id.id or '',
                                'Cliente': partner_id.name or '',
                                'Días de Crédito': partner_id.property_payment_term_id.line_ids.days,
                                'Factura': invoice.name,
                                'Vendedor': invoice.invoice_user_id.name,
                                'Fecha de Factura': invoice.invoice_date,
                                'Fecha Vencimiento': invoice.invoice_date_due,
                                'Pago Realizado': self.convert_to_company_currency(invoice.currency_id, item.get("amount"), invoice.invoice_date) or 0,
                                'Fecha Pago': item.get("date") or '',
                                'Forma de Pago': mv
                            }
                            if vals['Fecha Pago']:
                                fecha_pago_str = str(vals['Fecha Pago'])  # Convertir a cadena
                                fecha_pago = datetime.datetime.strptime(fecha_pago_str, '%Y-%m-%d').date()
                                dias_transcurridos = (fecha_pago - invoice.invoice_date_due).days
                                vals['Días de Pago'] = dias_transcurridos
                            else:
                                vals['Días de Pago'] = 0
                            report_data.append(vals)
        df = pd.DataFrame(report_data)
        ##Instanciar la clase ztyres_ms_sql_excel_core que tiene el metodo para insertar un dataframe en sql server
        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(df, 'reporte_cobranza')
        return

       
