# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
import pandas as pd
from datetime import timedelta, date
from odoo.exceptions import UserError

class Report(models.TransientModel):
    _name = 'discount_report.report'
    _description = 'Reporte para descuento de usuarios'

    partner_id = fields.Many2one('res.partner',string='Nombre del cliente',readonly=True)
    user_id = fields.Many2one('res.users',string='Vendedor')
    group = fields.Char(string='Grupo',readonly=True)
    partner_discount_id = fields.Many2one('discount_profiles.volume.discount',string='Descuento Volumen%')
    logistic_discount_id = fields.Many2one('discount_profiles.logistic.discount',string='Descuento Logístico%')
    last_count_sale = fields.Integer(string='Unidades Vendidas (mes anterior)',readonly=True)
    count_sale = fields.Integer(string='Unidades Vendidas (mes actual)',readonly=True)
    expected_volume = fields.Integer(string='Volumen Esperado')
    volume_progress = fields.Char(compute='_compute_volume_progress', string='Progreso %',store=True)
    property_payment_term_id = fields.Many2one('account.payment.term', string='Términos de pago del cliente')
    @api.depends('expected_volume', 'count_sale')
    def _compute_volume_progress(self):
        for rec in self:
            if rec.expected_volume and rec.count_sale:
                volume_progress = (100 * rec.count_sale) / rec.expected_volume
                rec.volume_progress = '%s %%' % int(volume_progress)
            else:
                rec.volume_progress = '0 %'

            
    
    @api.onchange('user_id')
    def onchange_user_id(self):
        self.partner_id.user_id = self.user_id 

    def check_users(self):
        if not self.partner_id.invoice_ids:
            raise UserError('El Contacto no tiene nunguna factura creada.')
        if not (self.partner_id and  self.user_id):
            raise UserError('Debe existir un usuario y un vendedor para realizar la asignación de documentos')

    def set_orders(self):
        for partner_id in self.partner_id.ids:
            query = """
                UPDATE sale_order
                SET user_id = %s
                WHERE partner_id = %s
            """
            self.env.cr.execute(query, (self.user_id.id, partner_id))

    def set_invoices(self):
        for partner_id in self.partner_id.ids:
            query = """
                UPDATE account_move
                SET invoice_user_id = %s
                WHERE partner_id = %s
            """
            self.env.cr.execute(query, (self.user_id.id, partner_id))

    def set_partner_docs(self):
        self.check_users()
        self.set_orders()
        self.set_invoices()
    
    @api.onchange('partner_discount_id')
    def onchange_partner_discount_id(self):
        self.partner_id.partner_discount_id = self.partner_discount_id
        
    @api.onchange('logistic_discount_id')
    def onchange_logistic_discount_id(self):
        self.partner_id.logistic_discount_id = self.logistic_discount_id
        
    @api.onchange('expected_volume')
    def onchange_expected_volume(self):
        self.partner_id.expected_volume = self.expected_volume

    def get_invoice_lines(self,partner_id, move_type, start_date, end_date):
        domain = [
            ('move_id.state', 'in', ['posted']),
            ('display_type', '=', 'product'),
            ('product_id.product_tmpl_id.detailed_type', '=', 'product'),
            ('move_id.move_type', 'in', [move_type]),
            ('move_id.partner_id', 'in', [partner_id]),
            ('move_id.invoice_date', '>=', start_date),
            ('move_id.invoice_date', '<=', end_date)
        ]
        print(domain)
        return self.env['account.move.line'].search(domain)

    def net_sales_product_qty(self,partner_id):
        dates = self.get_month_dates()
        inv_current_month = self.get_invoice_lines(partner_id, 'out_invoice', dates.get('start_current_month'), dates.get('end_current_month')).mapped('quantity')
        nc_current_month = self.get_invoice_lines(partner_id, 'out_refund', dates.get('start_current_month'), dates.get('end_current_month')).mapped('quantity')
        inv_last_month = self.get_invoice_lines(partner_id, 'out_invoice', dates.get('start_previous_month'), dates.get('end_previous_month')).mapped('quantity')
        nc_last_month = self.get_invoice_lines(partner_id, 'out_refund', dates.get('start_previous_month'), dates.get('end_previous_month')).mapped('quantity')
        vals = {
            'current_month': sum(inv_current_month) + (-1*sum(nc_current_month)),
            'last_month': sum(inv_last_month) + (-1*sum(nc_last_month))
        }
        return vals

    def get_month_dates(self):
        today = date.today()
        first_day_current_month = today.replace(day=1)
        last_day_current_month = (first_day_current_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        last_day_previous_month = first_day_current_month - timedelta(days=1)
        first_day_previous_month = last_day_previous_month.replace(day=1)

        return {
            'start_current_month': first_day_current_month.strftime('%Y-%m-%d'),
            'end_current_month': last_day_current_month.strftime('%Y-%m-%d'),
            'start_previous_month': first_day_previous_month.strftime('%Y-%m-%d'),
            'end_previous_month': last_day_previous_month.strftime('%Y-%m-%d'),
        }

    def generate_report_data(self):
        report_data = []
        res_partner = self.env['res.partner'].search([('type','in',['contact'])])
        for partner_id in res_partner:
            net_sales = self.net_sales_product_qty(partner_id.id)
            vals = {
                'partner_id': partner_id.id,
                'user_id': partner_id.user_id.id,
                'group': partner_id.x_studio_grupo,
                'logistic_discount_id':partner_id.logistic_profile.id or False,
                'partner_discount_id': partner_id.volume_profile.id or False,
                'expected_volume': partner_id.expected_volume,
                'last_count_sale': net_sales.get('last_month'),
                'count_sale': net_sales.get('current_month'),
                'property_payment_term_id': partner_id.property_payment_term_id.id
            }
            report_data.append(vals)
        return report_data

    def generate_report(self):
        report_data = self.generate_report_data()
        self.create(report_data)
    
    def delete_all_records(self):
        self.search([]).unlink()

    def get_report(self):
        self.delete_all_records()
        self.generate_report()
        return self.get_report_views()
        
    
    def get_report_views(self):
        views = [(self.env.ref('discount_report.report_tree').id, 'list'),]
        return {
                'name': 'Porcentaje de Descuentos',
                'view_type': 'form',
                "view_mode": "tree",
                #"view_mode": "tree,form,graph",
                'views': views,
                "res_model": "discount_report.report",
                'views': views,
                'domain': [],
                'type': 'ir.actions.act_window',
            }