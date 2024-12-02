# -*- coding: utf-8 -*-
from odoo import models, fields, api,_
from odoo.exceptions import ValidationError, UserError

class AccountMove(models.Model):
    _inherit = 'account.move'
    partner_credit_limit_used = fields.Monetary(related='partner_id.credt_limit_used', readonly=True)
    partner_credit_limit_available = fields.Monetary(related='partner_id.credt_limit_available', readonly=True)
    show_partner_credit_alert = fields.Boolean(compute='_compute_show_partner_credit_alert')
    partner_credit_limit = fields.Float(related='partner_id.credit_limit', readonly=True)
    partner_credit_amount_overdue = fields.Monetary(related='partner_id.credit_amount_overdue', readonly=True)
    
    def unlink(self):
        for move in self:
            if move.l10n_mx_edi_cfdi_uuid:
                raise UserError(_('No puedes eliminar una factura que fue timbrada.'))
        return super(AccountMove, self).unlink()
    
    def _compute_show_partner_credit_alert(self):
        for order in self:
            order.show_partner_credit_alert = True
    
    l10n_mx_edi_payment_policy = fields.Selection(string='Payment Policy',
        selection=[('PPD', 'PPD'), ('PUE', 'PUE')],
        compute='_compute_l10n_mx_edi_payment_policy', raise_if_not_found=False)
    
    @api.depends('move_type', 'invoice_date_due', 'invoice_date', 'invoice_payment_term_id', 'invoice_payment_term_id.line_ids')
    def _compute_l10n_mx_edi_payment_policy(self):     
        for move in self:
            if move.move_type == 'out_invoice':
                if sum(move.invoice_payment_term_id.line_ids.mapped('days')) > 0:
                    move.l10n_mx_edi_payment_policy = 'PPD'
                else:
                    move.l10n_mx_edi_payment_policy = 'PUE'
            elif move.move_type == 'out_refund':
                move.l10n_mx_edi_payment_policy = 'PUE'
            else:
                move.l10n_mx_edi_payment_policy = False