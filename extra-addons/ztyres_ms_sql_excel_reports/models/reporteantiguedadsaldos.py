import pandas as pd
import numpy as np
#pip install pyodbc sqlalchemy
#apt-get install unixodbc
from odoo import api, fields, models
import pandas as pd
from datetime import date,datetime, timedelta
from dateutil.relativedelta import relativedelta

class MyModel(models.TransientModel):
    _name = 'ztyres_ms_sql_excel_reports_antiguedad'

    def dias_hasta_vencimiento(self,factura):
        fecha_vencimiento = factura.invoice_date_due
        fecha_actual = date.today()
        diferencia_dias = (fecha_vencimiento - fecha_actual).days
        return diferencia_dias < 0, diferencia_dias

    def reporte_antiguedadsaldos(self):
        unreconciled_aml_ids = self.env['res.partner'].search([]).mapped('unreconciled_aml_ids')

        report_data = []
        for line in unreconciled_aml_ids.filtered(lambda aml: aml.move_id.move_type in ['out_invoice','out_refund','entry']):
            am_date = ''
            date_due = ''
            if line.move_id.move_type == 'entry':
                am_date = line.payment_id.date
                estatus = 'Por Vencer'
                mensaje_vencimiento = 0
            else:
                date_due = line.move_id.invoice_date_due
                vencida, diferencia = self.dias_hasta_vencimiento(line.move_id)
            # Mensaje inicial sobre el vencimiento
                if vencida:
                    mensaje_vencimiento = diferencia
                    estatus = 'Vencida'
                else:
                    mensaje_vencimiento = diferencia
                    estatus = 'Por Vencer'
            factura_dict = {
                "Id factura": line.move_id.id,
                "Id cliente": line.move_id.partner_id.id,
                "Nombre cliente": line.move_id.partner_id.name,
                "Dias de Credito": line.move_id.partner_id.property_payment_term_id.line_ids.days,
                "Limite de credito": line.move_id.partner_id.credit_limit,
                "Grupo": line.move_id.partner_id.x_studio_grupo or 'Sin Grupo',
                "Creado por": line.move_id.user_id.name,
                "Vendedor": line.move_id.partner_id.user_id.name,
                "Tipo de factura": line.move_id.move_type,
                "Número de factura": line.move_id.name,
                "fecha_factura": line.move_id.invoice_date or am_date,
                "fecha_vencimiento": date_due or am_date,
                "estatus": estatus,
                "dias": mensaje_vencimiento,
            }
            
            if line.move_id.invoice_date:
                factura_dict.update({"monto": line.move_id.currency_id._convert(line.amount_residual_currency, 
                                                                                line.move_id.company_id.currency_id,
                                                                                line.move_id.company_id,
                                                                                line.move_id.invoice_date or am_date)})
            
            report_data.append(factura_dict)

        # Obtener la fecha de hoy
        fecha_hoy = datetime.now().date()
        df = pd.DataFrame(report_data)
        reports_core = self.env['ztyres_ms_sql_excel_core']
        reports_core.action_insert_dataframe(df,'reporte_antiguedad')