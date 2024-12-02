from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError,ValidationError


#Si quedan saldos quiere decir que esta mal

class ApplyOutInvoicePaymentsLine(models.Model):
    _name = 'apply_out_invoice.payments_line'
    _description = 'apply_out_invoice_payments_line'
    payment_id_to_apply = fields.Many2one('apply_out_invoice.payments',string='Payment')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    payment_amount = fields.Float(string="Payment Amount")
    outstanding_amount = fields.Float(compute='_compute_outstanding_amount',store=True, string='Outstanding Amount')
    
    @api.constrains('payment_amount')
    def _check_payment_amount(self):
        for record in self:
            if record.payment_amount > record.outstanding_amount:
                raise UserError(_(
                                "El monto pagado es mayor al saldo, verifique"
                            ))
    
    @api.depends('invoice_id')
    def _compute_outstanding_amount(self):
        for record in self:
            if record.invoice_id:
                record.outstanding_amount = abs(record.invoice_id.amount_residual)                
            else:
                record.outstanding_amount = 0.0

class ApplyOutInvoicePayments(models.Model):
    _name = 'apply_out_invoice.payments'
    _description = 'apply_out_invoice_payments'
    
    partner_id = fields.Many2one('res.partner', string='Partner')
    payment_id = fields.Many2one('account.payment',string='Payment')
    lines = fields.One2many('apply_out_invoice.payments_line', 'payment_id_to_apply', string="Payment Lines")  # Corrected model name
    outstanding_amount = fields.Float(compute='_compute_outstanding_amount', string='Outstanding Amount')
    amount_pending = fields.Float(compute='_compute_amount_pending',store=True, string='Amount Pending')
    amount_applied = fields.Float(compute='_compute_amount_pending',store=True, string='Amount Applied')
    l10n_mx_edi_payment_method_id = fields.Many2one('l10n_mx_edi.payment.method', string='Forma de Pago')

    name = fields.Char(string='Name', copy=False, readonly=True, index=True, default=lambda self: self.env['ir.sequence'].next_by_code('apply_out_invoice.sequence'))
    state = fields.Selection(selection=[('draft', 'Sin Timbrar'), ('done', 'Timbrado')],compute='_calcular_state', store=True)
    
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.lines.unlink()
    

    def get_partner_payments(self):
        domain = [
            ('payment_type', '=', 'inbound'),
            ('state', '=', 'posted'),
            ('is_reconciled', '=', False),
            ('line_ids.amount_residual', '>', 0),
            ('line_ids.account_id.account_type', '=', 'asset_receivable'),
            ('line_ids.reconciled', '=', False),
            ('partner_id', '=', self.partner_id.id)
        ]
        return {
            "type": "ir.actions.act_window",
            "name": "Pagos de %s"%(self.partner_id.name or 'No hay cliente seleccionado'),
            "view_mode": "tree",
            "view_id": self.env.ref('apply_payments.view_account_payment_tree_with_selection').id,
            "res_model": "account.payment",
            "context": {'create': False, 'edit': False}, 
            "target":"new",
            "domain": domain,
        }
        
    @api.depends('payment_id')
    def _calcular_state(self):
        for record in self:
            record.state = record.payment_id.l10n_mx_edi_cfdi_uuid_state()


    def _check_amount_pending(self):
        for record in self:
            if not record.amount_pending == float(0):
                raise UserError(_(
                    "El pago debe ser aplicado en su totalidad y debe ser exacto %s"%(record.amount_pending)
                ))
    
    
    def apply_payments(self):
        for record in self:
            if record.state != 'done':
                record._check_amount_pending()
                record.payment_id.unlink_edi_document_ids()
                # record.payment_id.action_draft()
                record.payment_id.update({
                    'l10n_mx_edi_payment_method_id': record.l10n_mx_edi_payment_method_id.id
                })
                for line in record.lines:
                    record.create_partial_reconcile(
                        credit_move_id=record.payment_id.get_credit_move_id().id,
                        debit_move_id=line.invoice_id.get_debit_move_id().id,
                        amount=line.payment_amount
                    )                
                record.payment_id.action_l10n_mx_edi_force_generate_cfdi()
            if not record.name:
                record.name = self.env['ir.sequence'].next_by_code('apply_out_invoice.sequence') or '/'
            


    
    @api.depends('lines.payment_amount','partner_id','payment_id.line_ids')
    def _compute_amount_pending(self):
        for record in self:
            record.amount_pending = round(record.outstanding_amount - sum(record.lines.mapped('payment_amount')), 3)
            record.amount_applied = sum(record.lines.mapped('payment_amount'))
            
    @api.depends('payment_id')
    def _compute_outstanding_amount(self):
        for record in self:
            if record.payment_id:
                record.outstanding_amount = abs(record.payment_id.get_credit_move_id().amount_residual)
                # record.partner_id = record.payment_id.partner_id
            else:
                record.outstanding_amount = 0.0

    def create_partial_reconcile(self, credit_move_id, debit_move_id,amount):
        rec = self.env['account.partial.reconcile'].create({
            'amount': amount,
            'debit_amount_currency': amount,
            'credit_amount_currency': amount,
            'debit_move_id':  debit_move_id,
            'credit_move_id': credit_move_id,
            'apm_id':self.id
        })
        return rec

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    def get_balance(self):
        return abs(self.amount_residual)


class AccountMove(models.Model):
    _inherit = 'account.move'
    #Saldo de la factura con pagos aplicados
    def get_debit_move_id(self):
        return self.line_ids.filtered(lambda r: not r.reconciled and r.account_id.account_type in ('liability_payable', 'asset_receivable'))


class AccountPayment(models.AbstractModel):
    _inherit = 'account.payment'
    
    #Saldo del pago pendiente de aplicar
    def get_credit_move_id(self):
        return self.move_id.line_ids.filtered(lambda r: not r.reconciled and r.account_id.account_type in ('liability_payable', 'asset_receivable'))

    def update_l10n_mx_edi_payment_method_id(self,payment_method_id):
        for record in self:
            record.l10n_mx_edi_payment_method_id = payment_method_id
    
    def l10n_mx_edi_cfdi_uuid_state(self):
        for record in self:
            if record.l10n_mx_edi_cfdi_uuid:
                return 'done'
            else:
                return 'draft'
                
    def unlink_edi_document_ids(self):
        for record in self:
            if not record.l10n_mx_edi_cfdi_uuid:
                record.edi_document_ids.unlink()
                
                      
# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountPartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'
    apm_id= fields.Many2one('apply_out_invoice.payments', string='Aplicación de Pago Multiple')
    
    def unlink(self):
    # Agregar codigo de validacion aca
        if self.apm_id and self.apm_id.state == 'done':
            raise UserError(_(
                                "No se puede desaplicar el pago ya que esta relacionado a uuids de facturas específicas"
                            ))
            
        return super(AccountPartialReconcile, self).unlink()
