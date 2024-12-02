# -*- coding: utf-8 -*-
from odoo import models, fields, api,_
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta,date





class ResPartner(models.Model):
    _inherit = 'res.partner'

    credt_limit_used = fields.Monetary(compute='_compute_credt_limit_used', string='Crédito Usado')
    credt_limit_available = fields.Monetary(compute='_compute_credt_limit_available', string='Crédito Disponible')
    credit_amount_overdue = fields.Monetary(compute='_compute_credt_limit_available', string='Saldo Vencido')
    credit_limit = fields.Float(string='Límite de Crédito',tracking=True)
    total_overdue_3_days = fields.Monetary(compute='_compute_total_overdue_3_days')

    def _compute_total_overdue_3_days(self):
        today = fields.Date.context_today(self)
        for partner in self:
            total_overdue_3_days = 0
            for aml in partner.unreconciled_aml_ids:
                date_maturity = aml.date_maturity + timedelta(days=3) if aml.date_maturity else today > aml.date
                if isinstance(date_maturity, (date, datetime)):
                    is_overdue = today > date_maturity
                else:
                    is_overdue = False               
                if aml.company_id == self.env.company and not aml.blocked:
                    if is_overdue:
                        total_overdue_3_days += aml.amount_residual
            partner.total_overdue_3_days = total_overdue_3_days

    @api.depends('vat')
    def _check_vat_unique(self):
        for record in self:
            if record.type not in ['delivery','other','private']:
                if record.vat:  # Esta línea se asegura de que el vat no esté vacío
                    duplicate = self.env['res.partner'].search([('vat', '=', record.vat), ('id', '!=', record.id)], limit=1)
                    if duplicate:
                        raise ValidationError(_("El Número de Identificación Fiscal (VAT) ya está registrado con otro contacto."))

    def _compute_credt_limit_used(self):
        for partner in self:
            partner.credt_limit_used = 0
            partner.credit_amount_overdue = 0

    def _compute_credt_limit_available(self):
        for partner in self:
            partner.credt_limit_available = (partner.credit_limit-partner.credt_limit_used) if (partner.credit_limit-partner.credt_limit_used)>=1 else 0
            print(partner.credt_limit_available)
    
          

    def _ztyres_compute_unpaid_invoices(self):
        account_move = self.env['account.move']        
        unpaid_invoices = False
        for record in self:
            unpaid_invoices = account_move.search([
                ('company_id', '=', self.env.company.id),
                ('commercial_partner_id', '=', record.id),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('move_type', 'in', account_move.get_sale_types())
            ]).filtered(lambda inv: not any(inv.line_ids.mapped('blocked')))
        sales_unpaid = unpaid_invoices.mapped('invoice_line_ids').mapped('sale_line_ids').mapped('order_id').mapped('name')
        return (unpaid_invoices,sales_unpaid)

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        # return values in result, as this method is used by _fields_sync()
        if not self.parent_id:
            return
        result = {}
        partner = self._origin
        if partner.parent_id and partner.parent_id != self.parent_id:
            result['warning'] = {
                'title': _('Warning'),
                'message': _('Changing the company of a contact should only be done if it '
                             'was never correctly set. If an existing contact starts working for a new '
                             'company then a new contact should be created under that new '
                             'company. You can use the "Discard" button to abandon this change.')}
        return result

    @api.model
    def create(self, values):
        # Obtén el ID del usuario actual
        user_id = self.env.user.id

        # Verifica si el usuario tiene permiso para crear un registro
        if user_id not in [43,2,85]:
            raise UserError("Solo el usuario con ID 2 puede crear registros en res.partner.")

        # Llama al método original de create para realizar la creación del registro
        return super(ResPartner, self).create(values)
