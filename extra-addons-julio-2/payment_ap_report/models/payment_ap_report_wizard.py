# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
import pandas as pd
from datetime import timedelta, date

class Wizard(models.TransientModel):
    _name = 'payment_ap_report.wizard'
    _description = 'Wizard Reporte de aplicacion de pagos'
    partner_id = fields.Many2one('res.partner',string="Cliente")
    
    def get_payment_ap_report(self):
        if self.partner_id:
            return  self.env['payment_ap_report.report'].get_report(self.partner_id.ids)
        else:
            raise UserError("¡No ha seleccionado ningun cliente.")
    