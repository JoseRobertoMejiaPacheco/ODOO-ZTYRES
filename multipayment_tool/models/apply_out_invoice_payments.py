from odoo import _, api, fields, models

class ApplyOutInvoicePaymentsLine(models.Model):
    _inherit = 'apply_out_invoice.payments_line'
    _description = 'apply_out_invoice_payments_line'
    
    payment_form_id = fields.One2many('multipayment_tool.payment_form','payments_line_id',string='Payment Form',ondelete='cascade')
    payment_amount = fields.Monetary(compute='_compute_payment_amount', string='Pago Aplicado',currency_field='currency_id')
    currency_id = fields.Many2one(related='payment_id_to_apply.payment_id.currency_id', string='Moneda')
    
    def create_data(self):
        for record in self:
            print(record.payment_id_to_apply)
            data = []
            lines_to_create = []
            payment_form_vals = {}            
            self.env.cr.execute("""
                SELECT payment_amount FROM apply_out_invoice_payments_line WHERE id = %s""", (record.id,))
            result = self.env.cr.fetchone()  # O fetchall() si esperas múltiples registros
            if result:
                if not result[0]:
                    continue
            else:
                continue
            record.payment_id_to_apply.move_ids = [(4, record.invoice_id.id)]
            data.append((0, 0, {
                            'move_id': record.invoice_id.id,
                            'move_detailed_line_ids': [],
                            'payment_origin':'prev',
                            'amount_to_apply':0,
                            'payment_name': record.invoice_id.move_type
                        }))
            data.append((0, 0, {
                    'move_id': record.payment_form_id.payment_id.move_id.id,                        
                    'payment_origin':'new',
                    'amount_to_apply': result[0],
                    'payment_name': record.payment_id_to_apply.payment_id.move_id.move_type
                }))
            payment_form_vals['payment_ids'] = data
            payment_form = self.env['multipayment_tool.payment_form'].create(payment_form_vals)
            payment_form.payments_line_id = record.id
            record.payment_id_to_apply.amount_pending = 0.0
            print(record.payment_id_to_apply)
        
    @api.depends('payment_form_id.total_payments')
    def _compute_payment_amount(self):
        for record in self:
            record.payment_amount = sum(record.payment_form_id.payment_ids.filtered(lambda x : x.payment_origin == 'new' and x.payment_name =='entry').mapped('amount_to_apply'))
    
    def get_payments_line(self):
        self.ensure_one()
        if self.payment_form_id:
            return {
                'name': 'Pago Aplicado',
                'type': 'ir.actions.act_window',
                'res_model': 'multipayment_tool.payment_form',
                'view_mode': 'form',
                'res_id': self.payment_form_id[0].id,
                'target': 'current'
            }
        else:
            return {'type': 'ir.actions.act_window_close'}
        
class ApplyOutInvoicePayments(models.Model):
    _inherit = 'apply_out_invoice.payments'
    _description = 'apply_out_invoice_payments'
    _order = 'name desc'
    
    move_ids = fields.Many2many('account.move', string='Facturas a pagar')
    payment_amount = fields.Monetary(related='payment_id.amount', string='Monto del Pago')
    currency_id = fields.Many2one(related='payment_id.move_id.currency_id', string='Moneda')

    @api.depends('lines.payment_amount','partner_id','payment_id.line_ids')
    def _compute_amount_pending(self):
        for record in self:
            record.amount_pending = round(record.outstanding_amount - sum(record.lines.mapped('payment_amount')), 2)
            record.amount_applied = sum(record.lines.mapped('payment_amount'))
    
    def get_detailed_info(self):
        for record in self:
            # Eliminamos todas las líneas existentes
            record.lines.unlink()
            
            lines_to_create = []
            for move in record.move_ids:
                # Creamos el formulario de pagos (payment_form)
                payment_form_vals = {}
                valss = move._get_payment_info()
                if valss.get('payments'):
                    payment_form_vals['payment_ids'] = valss['payments']
                payment_form = self.env['multipayment_tool.payment_form'].create(payment_form_vals)
                
                # Creamos la línea de pago global, asociando el formulario
                line_vals = {
                    'invoice_id': move.id,
                    'payment_form_id': [(4, payment_form.id)],  # Relación inversa
                }
                
                lines_to_create.append((0, 0, line_vals))
            
            record.write({
                'lines': lines_to_create
            })
    
    def _update_payment(self):
        for record in self:
            if record.state != 'done':
                #record._check_amount_pending()
                record.payment_id.unlink_edi_document_ids()
                # record.payment_id.action_draft()
                record.payment_id.update({
                    'l10n_mx_edi_payment_method_id': record.l10n_mx_edi_payment_method_id.id
                })
    
    
    
    def apply_payments(self):
        for record in self:
            if record.state != 'done':
                record._check_amount_pending()
                record.payment_id.unlink_edi_document_ids()
                record._update_payment()
                record.lines.payment_form_id.payment_ids._create_credit_notes()
                record.lines.payment_form_id.payment_ids._reconcile_nc()
                record.lines.payment_form_id.payment_ids._reconcile_payment()
                record.lines.payment_form_id.payment_ids._create_adjustment_entry()
                record.lines.payment_form_id.payment_ids._generate_edi_docs()
                record.payment_id.action_l10n_mx_edi_force_generate_cfdi()
                record.payment_id.action_process_edi_web_services()
                if not record.name:
                    record.name = self.env['ir.sequence'].next_by_code('apply_out_invoice.sequence') or '/' 