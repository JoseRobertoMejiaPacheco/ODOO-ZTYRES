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
    
    solicitar_cancelacion = fields.Boolean(string="Solicitar Cancelación")
    firma_calidad = fields.Boolean(string="Autoriza Calidad")
    firma_finanzas = fields.Boolean(string="Autoriza Finanzas")
    
     # campos auxiliares para controlar permisos
    can_edit_solicitar_cancelacion = fields.Boolean(
        compute="_compute_permisos", store=False
    )
    can_edit_firma_calidad = fields.Boolean(
        compute="_compute_permisos", store=False
    )
    can_edit_firma_finanzas = fields.Boolean(
        compute="_compute_permisos", store=False
    )
    
    can_cancel_edi = fields.Boolean(
        compute="_compute_permisos_cancel",
        store=False
    )
    
    show_edi_cancel_button_final = fields.Boolean(
        compute="_compute_show_edi_cancel_button_final",
        string="Aprobar Cancelación",
        store=True
    )

    @api.depends('create_uid')
    def _compute_permisos(self):
        for rec in self:
            user = rec.env.user
            rec.can_edit_solicitar_cancelacion = user.has_group('ztyres.group_solicitud')
            rec.can_edit_firma_calidad = user.has_group('ztyres.group_calidad')
            rec.can_edit_firma_finanzas = user.has_group('ztyres.group_finanzas')
            
    @api.depends('show_edi_cancel_button_final')
    def _compute_permisos_cancel(self):
        for rec in self:
            rec.can_cancel_edi = rec.show_edi_cancel_button_final and rec.env.user.has_group('ztyres.group_cancel_edi')

            
    @api.depends('firma_calidad', 'firma_finanzas', 'state')  # o cualquier campo que afecte edi_show_cancel_button
    def _compute_show_edi_cancel_button_final(self):
        for rec in self:
            rec.show_edi_cancel_button_final = (
                rec.firma_calidad and 
                rec.firma_finanzas and 
                rec.state in ('posted')
            )
    def copy(self, default=None):
        default = dict(default or {})
        # Reiniciamos los checks
        default.update({
            'solicitar_cancelacion': False,
            'firma_calidad': False,
            'firma_finanzas': False,
        })
        return super().copy(default)

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
            if move.move_type == 'out_invoice' and not move.journal_id.id in [144,145,147]:
                if sum(move.invoice_payment_term_id.line_ids.mapped('days')) > 0:
                    move.l10n_mx_edi_payment_policy = 'PPD'
                    move.l10n_mx_edi_payment_method_id = 22
                else:
                    move.l10n_mx_edi_payment_policy = 'PPD'
                    move.l10n_mx_edi_payment_method_id = 2
            if move.move_type == 'out_invoice' and move.journal_id.id in [144,145,147]:
                move.l10n_mx_edi_payment_policy = 'PUE'
                if move.journal_id.id in [145,144]:
                    move.l10n_mx_edi_payment_method_id = 3
                if move.journal_id.id in [147]:
                    move.l10n_mx_edi_payment_method_id = 1                
            elif move.move_type == 'out_refund':
                move.l10n_mx_edi_payment_policy = 'PUE'
            else:
                move.l10n_mx_edi_payment_policy = 'PPD'
                move.l10n_mx_edi_payment_method_id = 22