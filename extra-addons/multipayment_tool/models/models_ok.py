# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import date
#region Account Move
class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_payment_info(self):
        aml_ids = self.line_ids.filtered(
            lambda l: l.account_id.account_type in (
                'asset_receivable', 'liability_payable')
        ).ids
        
        if not aml_ids:
            return []

        query = '''
            SELECT
                part.debit_amount_currency AS amount,
                part.credit_move_id AS counterpart_line_id
            FROM account_partial_reconcile part
            WHERE part.debit_move_id IN %s

            UNION ALL

            SELECT
                part.credit_amount_currency AS amount,
                part.debit_move_id AS counterpart_line_id
            FROM account_partial_reconcile part
            WHERE part.credit_move_id IN %s
        '''

        self.env['account.partial.reconcile'].flush_model([
            'debit_move_id', 'credit_move_id', 'debit_amount_currency',
            'credit_amount_currency'
        ])
        self._cr.execute(query, (tuple(aml_ids), tuple(aml_ids)))
        result = self._cr.dictfetchall()
# payment_previus_line move_type entry
# credit_notes_previus_line out_refund
        global_lines = []
        payment_previus = []
        nc_previus = []
        if self.move_type == 'out_invoice':
            nc_previus.append((0, 0, {
                'move_id': self.id,
                'move_detailed_line_ids': [],
                'payment_origin':'prev',
                'amount_to_apply': 0.0,
                'payment_name': self.move_type
            }))
        for r in result:
            aml = self.env['account.move.line'].browse(r['counterpart_line_id'])
            
            if aml and aml.move_id and aml.move_id.id:
                detail_lines = []
                product_lines = aml.move_id.invoice_line_ids.filtered(
                    lambda line: line.display_type == 'product' and line.debit > 0.0
                )
                
                for product_line in product_lines:
                    if product_line:
                        detail_lines.append((0, 0, {
                            'name': product_line.name,
                            'amount_taxed': product_line.debit,                            
                        }))
                
                if aml.move_id.move_type == 'out_refund':
                    nc_previus.append((0, 0, {
                        'move_id': aml.move_id.id,
                        'move_detailed_line_ids': detail_lines,
                        'payment_origin':'prev',
                        'amount_to_apply':r.get('amount',0),
                        'payment_name': aml.move_id.move_type
                    }))
                
                elif aml.move_id.move_type == 'entry':
                    payment_previus.append((0, 0, {
                        'move_id': aml.move_id.id,
                        'move_detailed_line_ids': detail_lines,
                        'payment_origin':'prev',
                        'amount_to_apply': r.get('amount',0),
                        'payment_name': aml.move_id.move_type
                    }))
        
        global_vals = {
            'payments':nc_previus+payment_previus
        }        
        return global_vals
#endregion

class ModuleName(models.Model):
    _name = 'multipayment_tool.discount'
    _description = 'New Description'
    name = fields.Char(string='Descuento')
    discount = fields.Integer(string='Porcentaje de descuento')


class DetailedLine(models.Model):
    _name = 'multipayment_tool.detail_line'
    _rec_name = 'tag_name'
    tag_name = fields.Char(compute='_compute_tag_name')
    
    name = fields.Char(string='Etiqueta')
    amount_taxed = fields.Float(string='Monto')
    payment_id = fields.Many2one('multipayment_tool.payments')
    
    @api.depends('name','amount_taxed','payment_id')
    def _compute_tag_name(self):
        for record in self:
            record.tag_name = f'{record.name} ${record.amount_taxed}'
# -----------------------------------------
# Clase base para modelos con campos similares
# -----------------------------------------
class _MoveCommonFields(models.AbstractModel):
    _name = 'multipayment_tool.abstract_move'
    _description = 'Campos comunes para modelos relacionados a movimientos'
    move_id = fields.Many2one('account.move', string='Movimiento')
    move_type = fields.Selection(related='move_id.move_type', string='Tipo de Movimiento', store=True, readonly=True)
    move_date = fields.Date(related='move_id.date', string='Fecha', store=True)
    move_amount_total = fields.Monetary(related='move_id.amount_total', string='Monto Total', store=True)
    move_amount_residual = fields.Monetary(related='move_id.amount_residual', string='Saldo', store=True)
    currency_id = fields.Many2one(related='move_id.currency_id', string='Moneda')

class paymentsform(models.Model):
    _name = 'multipayment_tool.payment_form'
    _rec_name = 'partner_id'
    payments_line_id = fields.Many2one(comodel_name='apply_out_invoice.payments_line', string='Payment Line')
    payment_ids = fields.One2many('multipayment_tool.payments','payment_form_id', string='Payments')
    invoice_amount_total = fields.Float(compute='_compute_amounts', digits=(16, 2),string='Total Factura')
    total_payments = fields.Float(compute='_compute_amounts', digits=(16, 2),string='Total de Pagos Previos')
    total_nc = fields.Float(compute='_compute_amounts', digits=(16, 2),string='Total de NC Previas')
    amount_residual = fields.Float(compute='_compute_amounts', digits=(16, 2),string='Saldo')
    payment_amount_pending = fields.Monetary(compute='_compute_amounts',string='Pendiente por aplicar')
    #TODO Check Currency
    currency_id = fields.Many2one( 'res.currency', string='Moneda', default=lambda self: self.env.company.currency_id )
    # payment_partner_id = fields.Many2one(related='payments_line_id.move_id.payment_partner_id', string='Cliente', store=True)
    elapsed_days = fields.Char(compute='_compute_elapsed_days', string='Días transcurridos')
    payment_id = fields.Many2one(related='payments_line_id.payment_id_to_apply.payment_id', string='Pago')
    payment_amount = fields.Monetary(related='payments_line_id.payment_id_to_apply.payment_id.amount', string='Pago')
    partner_id = fields.Many2one(related='payments_line_id.payment_id_to_apply.partner_id', string='Cliente')
    
    @api.depends('payment_ids')
    def _compute_elapsed_days(self):
        for record in self:
            payment_date = record.payments_line_id.payment_id_to_apply.payment_id.date 
            date_due = record.payments_line_id.invoice_id.invoice_date_due  # Usar invoice_date_due en lugar de invoice_date
            
            if not payment_date or not date_due:
                record.elapsed_days = "Sin fecha definida"
                continue
            
            delta = (payment_date - date_due).days
            
            if delta == 0:
                record.elapsed_days = "Pagado a tiempo"
            elif delta > 0:
                record.elapsed_days = f"Pagado {delta} días después"
            else:
                record.elapsed_days = f"Pagado {abs(delta)} días antes"       
    
    @api.depends('payment_ids.amount_to_apply')
    def _compute_amounts(self):
        for record in self:
            record.invoice_amount_total = record.payments_line_id.invoice_id.amount_total
            record.total_payments = sum(record.payment_ids.filtered(lambda l : l.payment_name == 'entry').mapped('amount_to_apply'))
            print(record.payment_ids.filtered(lambda l : l.payment_name == 'entry'))
            record.total_nc = sum(record.payment_ids.filtered(lambda l : l.payment_name == 'out_refund').mapped('amount_to_apply'))
            record.amount_residual = record.invoice_amount_total - record.total_payments - record.total_nc
            record.payment_amount_pending = record.payments_line_id.payment_id_to_apply.payment_id.amount - sum(record.payments_line_id.payment_id_to_apply.lines.payment_form_id.payment_ids.filtered(lambda l : l.payment_name == 'entry' and l.payment_origin == 'new').mapped('amount_to_apply'))

    
    @api.constrains('payment_amount_pending')
    def _check_payment_amount_pending(self):
        for record in self:
            if record.payment_amount_pending <0 or record.amount_residual <0:
                raise UserError('No se puede agregar un monto mayor al saldo pendiente por aplicar o al Saldo')
    
class payments(models.Model):
    _name = 'multipayment_tool.payments'
    _inherit = 'multipayment_tool.abstract_move'
    discount_id = fields.Many2one('multipayment_tool.discount', string='Porcentaje de Descuento')
    amount_to_apply = fields.Monetary(string='Pago')
    move_detailed_line_ids = fields.One2many('multipayment_tool.detail_line', 'payment_id', string="Líneas de detalle")
    
    payment_origin = fields.Selection(
        string='Origen',
        selection=[('prev', 'Previo'), ('new', 'Nuevo')],default='new'
    )
    payment_name = fields.Selection(
        string='Documento',
        selection=[('entry', 'Pago'),('out_refund', 'Nota de Crédito'),('out_invoice', 'Factura de Cliente')]
    )
    payment_form_id = fields.Many2one(comodel_name='multipayment_tool.payment_form', string='Payment Form')
    
    def _reconcile_nc(self):
        for record in self:
            if record.payment_name == 'out_refund' and record.payment_origin == 'new':
                invoice = record.payment_form_id.payment_ids.filtered(lambda l : l.payment_name == 'out_invoice')
                nc_credit_id = record.move_id.mapped('line_ids').filtered(lambda line: line.account_type == 'asset_receivable')
                invoice_debit_id = invoice.move_id.get_debit_move_id()            
                apply_out_invoice = self.env['apply_out_invoice.payments']
                amount = 0
                if record.discount_id:
                    amount = nc_credit_id.credit
                else:
                    amount = record.amount_to_apply
                apply_out_invoice.sudo().create_partial_reconcile(
                    credit_move_id=nc_credit_id.id,
                    debit_move_id=invoice_debit_id.id,
                    amount=amount
                )
                print('done')
    
    def _create_adjustment_entry(self):
        for record in self:
            if record.payment_name == 'out_invoice' and record.payment_origin == 'prev':            
                record.ensure_one()
                if 0.01 <= record.move_id.amount_residual <= 0.05:
                    adjustment_account = self.env['account.account'].search([('code', '=', '888.88.8888.8888.8888')], limit=1)
                    journal = self.env['account.journal'].search([('id', '=',140)], limit=1)  # Buscar el diario bancario (ajústalo según tu caso)
                    account_asset_receivable = record.move_id.get_debit_move_id()
                    adjustment_entry = {
                        'journal_id': journal.id,
                        'date': fields.Date.today(),
                        'line_ids': [(0, 0, {
                            'account_id': adjustment_account.id,
                            'debit': record.move_id.amount_residual,  # Ajuste debito si es un ajuste negativo
                            'credit': 0.0,
                            'name': 'Ajuste de redondeo por saldo residual',
                        }),
                        (0, 0, {
                            'account_id': account_asset_receivable.account_id.id,  # Cuenta asociada a la factura
                            'debit': 0.0,
                            'credit': record.move_id.amount_residual,  # Ajuste crédito
                            'name': 'Ajuste de redondeo por saldo residual',
                        })],
                    }
                    # Crear la entrada contable
                    adjustment_move = self.env['account.move'].create(adjustment_entry)
                    adjustment_move.action_post()
                    debit_line = adjustment_move.invoice_line_ids.filtered(lambda x: x.account_id.id == adjustment_account.id)
                    apply_out_invoice = self.env['apply_out_invoice.payments']
                    apply_out_invoice.sudo().create_partial_reconcile(
                        credit_move_id=debit_line.id,
                        debit_move_id=account_asset_receivable.id,
                        amount=record.move_id.amount_residual
                    )
    
    def _reconcile_payment(self):
        for record in self:
            if record.payment_name == 'entry' and record.payment_origin == 'new':
                apply_out_invoice = self.env['apply_out_invoice.payments']
                invoice = record.payment_form_id.payment_ids.filtered(lambda l : l.payment_name == 'out_invoice')
                apply_out_invoice.sudo().create_partial_reconcile(
                    credit_move_id=record.payment_form_id.payments_line_id.payment_id_to_apply.payment_id.get_credit_move_id().id,
                    debit_move_id=invoice.move_id.get_debit_move_id().id,
                    amount=record.amount_to_apply
                )
                print('done')
    
    def _generate_edi_docs(self):
        for record in self:
            if record.payment_name == 'out_refund' and record.payment_origin == 'new':
                if record.move_id:
                    docs = record.move_id.edi_document_ids.filtered(lambda d: d.state in ('to_send', 'to_cancel') and d.blocking_level != 'error')
                    if docs:
                        docs._process_documents_web_services(with_commit=True)
    
    
    def _create_credit_notes(self):
        for record in self:
            if record.payment_name == 'out_refund' and record.payment_origin == 'new' and record.discount_id and not record.move_id:
                record.ensure_one()
                invoice = record.payment_form_id.payment_ids.filtered(lambda l : l.payment_name == 'out_invoice')
                invoice.ensure_one()
                generic = invoice.move_id.generic_edi
                price_unit = 0
                if invoice.move_id.amount_tax > 0:
                    tax_id = self.env['account.tax'].browse(2)
                    n = record.amount_to_apply
                    n = n/1.16
                    res = tax_id.compute_all(n)
                    price_unit = res.get('total_excluded',0)                    
                    
                else:
                    price_unit = record.amount_to_apply
                print(round(price_unit,2))
                credit_note_vals = {                
                    'l10n_mx_edi_origin': f'01|{invoice.move_id.l10n_mx_edi_cfdi_uuid or ""}',
                    'move_type': 'out_refund',
                    "x_studio_tipo": "Bonificación",
                    "generic_edi": generic,
                    "invoice_date": fields.Date.today().strftime(DEFAULT_SERVER_DATE_FORMAT),
                    "journal_id": 24,
                    "l10n_mx_edi_payment_method_id": 11,  # Condonacion
                    "l10n_mx_edi_usage": "G02",  # Devoluciones y Bonificaciones
                    "currency_id": invoice.move_id.currency_id.id,
                    "partner_id": invoice.move_id.partner_id.id,
                    "partner_shipping_id": invoice.move_id.partner_id.id,
                    "invoice_line_ids": [(0, 0, {
                        "product_id": 50785,
                        "quantity": 1,
                        "name": record.discount_id.name,
                        "price_unit": price_unit,
                    })],
                }
                if generic:
                    credit_note_vals.update({'edi_vat_receptor':'XAXX010101000'})
                credit_note = record.move_id.sudo().create(credit_note_vals)
                credit_note.sudo().action_post()
                record.move_id = credit_note.id
                print('done')
    
    @api.ondelete(at_uninstall=False)
    def _check_delete_payment_prev(self):
        for rec in self:
            if rec.payment_origin == 'prev':
                raise UserError("No se puede eliminar un pago aplicado previamente'.")
    
    @api.onchange('amount_to_apply', 'payment_name', 'payment_origin')
    def _onchange_anything(self):
        if self.payment_form_id:
            # solo para que el formulario padre refresque
            self.payment_form_id.payment_amount_pending = self.payment_form_id.payment_amount_pending
    
    @api.onchange('discount_id')
    def onchange_discount_id(self):
        for rec in self:
            invoice = rec.payment_form_id.payment_ids.filtered(lambda l : l.payment_name == 'out_invoice')
            invoice.ensure_one()        
            if rec.payment_name == 'out_refund' and rec.discount_id and invoice.move_id.amount_total:
                porcentaje = rec.discount_id.discount
                tax_id = self.env['account.tax'].browse(2)
                n = tax_id.compute_all((invoice.move_id.amount_total - invoice.move_id.amount_total * (1 - (porcentaje / 100.0)))  /(1.16) )
                n = n.get('total_included',0)
                res = tax_id.compute_all(n/(1.16))
                rec.amount_to_apply = res.get('total_included',0)
            else:
                rec.amount_to_apply = 0
                rec.discount_id = False
    
    @api.onchange('payment_name','move_id')
    def _onchange_discount_id(self):
        for rec in self:
            if rec.payment_form_id.payment_amount_pending == 0.0 and  rec.payment_form_id.amount_residual == 0.0:
                raise UserError('No es posible agregar más lineas ya que el saldo es 0 por aplicar o la factura está saldada')
            
            rec.discount_id = False
            if rec.payment_name != rec.move_id.move_type:
                rec.move_id = False
            if rec.payment_name == 'out_invoice':
                raise UserError('Caracteristica en desarrollo... no es posible agregar facturas')
            if not self.payment_name:
                # Notas de crédito con saldo
                return {
                    'domain': {
                        'move_id': [
                           ('id','in',-1)
                        ]
                    }
                }
            if self.payment_name == 'out_refund':
                # Notas de crédito con saldo
                return {
                    'domain': {
                        'move_id': [
                            ('move_type', '=', 'out_refund'),
                            ('payment_state', '!=', 'paid'),
                            ('amount_residual', '>', 0),
                            ('state', '=', 'posted'),
                            ('partner_id','in',rec.payment_form_id.payments_line_id.payment_id_to_apply.partner_id.ids)
                        ]
                    }
                }
            elif self.payment_name == 'entry' and self.payment_origin == 'new':
                # Pagos disponibles del contexto
                rec.move_id = rec.payment_form_id.payments_line_id.payment_id_to_apply.payment_id.move_id or False
                return {
                    'domain': {
                        'move_id': [('id', 'in', rec.move_id.ids)]
                    }
                }
            return {}
