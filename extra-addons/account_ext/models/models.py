# -*- coding: utf-8 -*-
from odoo import models, fields, _,api
import math
from odoo.exceptions import UserError,ValidationError
from odoo.exceptions import UserError, AccessError,RedirectWarning
from collections import defaultdict
from odoo.tools import (
    float_compare,
    format_date,
    formatLang,
    get_lang
)

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    post_on_import = fields.Boolean(default=False,string='Publicar movimiento en carga')
    
    
    # def create(self, vals):
    #     # Agregar codigo de validacion aca
    #     res = super(AccountPayment, self).create(vals)
    #     if vals and isinstance(vals[0], dict) and vals[0].get('post_on_import'):
    #         res.action_post()
    #     return res

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    def update_costo_final(self):
        for po in self.with_progress(msg="Actualizando Costo Final :3"):
            for invoice_line in po.invoice_ids.invoice_line_ids:
                # Obtener el costo final de la factura
                costo_final_factura_lista =  po.order_line.filtered(lambda line: line.product_id.id == invoice_line.product_id.id
                                                                        and line.x_studio_costo_final not in [0, 0.0]).mapped('x_studio_costo_final')
                print(costo_final_factura_lista)
                if costo_final_factura_lista:
                    costo_final_factura_lista = sum(costo_final_factura_lista) / len(costo_final_factura_lista)
                    # Si la lista no está vacía, obtener el máximo valor
                    invoice_line.costo_final = costo_final_factura_lista            

class ProductCategory(models.Model):
    _inherit = 'product.category'
    property_account_expense_refund_categ_id = fields.Many2one('account.account', string='Cuenta para notas de crédito')
    
#Template hereda a product product
class ProductProduct(models.Model):
    _inherit = 'product.template'
    property_account_expense_refund_id = fields.Many2one('account.account', string='Cuenta para notas de crédito')
    

######Recategorizar cuentas#######
class AccountMove(models.Model):
    
    _inherit = 'account.move'
    is_redo_move = fields.Boolean(default=False)

    # def create(self, vals):
    #     # Llamada al método original
    #     record = super(AccountMove, self).create(vals)

    #     # Realizar acciones adicionales después de crear una nota de crédito
    #     if record.move_type == 'out_refund':
    #         # Llamar a tu método personalizado aquí
    #         record._update_line_accounts_refund()

    #     return record


#Descomentar
    def write(self, vals):
        #Refactorizar para que las modificaciones se hagan en el write y no repita la operacion
        # Realizar acciones adicionales después de crear una nota de crédito
        res = super().write(vals)
        for record in self:
            if record.move_type == 'out_refund':
                record._update_line_accounts_refund()
        return res
                
                
            


                
    def redo_assets(self):
        for move in self:
            if move.move_type == 'out_invoice':
                move._recategorize_accounts_invoice()
            elif move.move_type == 'out_refund':
                move._recategorize_accounts_refund()
            else:
                raise ValidationError("Solo se pueden regenerar notas de crédito o facturas de cliente")

    def _recategorize_accounts_invoice(self):
        self._validate_invoice_accounts()
        self._unlink_reconciles()
        self.with_context(is_redo_move=True, validate_analytic=True)._post_account_ext(True)

    def _recategorize_accounts_refund(self):
        self._unlink_reconciles()
        self._update_line_accounts_refund()
        self.with_context(is_redo_move=True)._post_account_ext(True)

    def _validate_invoice_accounts(self):
        line_products = self.line_ids.filtered(lambda line: line.display_type == 'product')
        for line in line_products:
            if not line.product_id.categ_id.property_account_income_categ_id:
                raise ValidationError("El producto %s no tiene cuenta de ingresos en su categoría" % (line.product_id.name))
            line.account_id = line.product_id.categ_id.property_account_income_categ_id.id

    def _unlink_reconciles(self):
        apr = self.env['account.partial.reconcile']
        lines = self.line_ids.filtered(lambda line: line.display_type not in ['product', 'tax', 'payment_term'])
        lines.full_reconcile_id.unlink()
        apr.search([('debit_move_id', 'in', lines.ids)]).unlink()
        apr.search([('credit_move_id', 'in', lines.ids)]).unlink()
        lines.with_context(force_delete=True).unlink()

    def _update_line_accounts_refund(self):
        line_products = self.line_ids.filtered(lambda line: line.display_type == 'product')
        for line in line_products:
            if line.product_id.categ_id.property_account_expense_refund_categ_id:
                line.with_context(is_redo_move=True).write({'account_id': line.product_id.categ_id.property_account_expense_refund_categ_id.id })
            elif line.product_id.categ_id.property_account_expense_categ_id:
                line.with_context(is_redo_move=True).write({'account_id': line.product_id.categ_id.property_account_expense_categ_id.id })
        
                                
                                
    @api.constrains('ref', 'move_type', 'partner_id', 'journal_id', 'invoice_date', 'state')
    def _check_duplicate_supplier_reference(self):
        """ Assert the move which is about to be posted isn't a duplicated move from another posted entry"""
        move_to_duplicate_moves = self.filtered(lambda m: m.state == 'posted')._fetch_duplicate_supplier_reference(only_posted=True)
        if any(duplicate_move for duplicate_move in move_to_duplicate_moves.values()):
            if not self.env.context.get('is_redo_move'):
                duplicate_move_ids = list(set(
                    move_id
                    for move_ids in (move.ids + duplicate.ids for move, duplicate in move_to_duplicate_moves.items() if duplicate)
                    for move_id in move_ids
                ))
                action = self.env['ir.actions.actions']._for_xml_id('account.action_move_line_form')
                action['domain'] = [('id', 'in', duplicate_move_ids)]
                action['views'] = [((view_id, 'list') if view_type == 'tree' else (view_id, view_type)) for view_id, view_type in action['views']]
                raise RedirectWarning(
                    message=_("Duplicated vendor reference detected. You probably encoded twice the same vendor bill/credit note."),
                    action=action,
                    button_text=_("Open list"),
                )

    def _post_account_ext(self, soft=True):

        """Post/Validate the documents.

        Posting the documents will give it a number, and check that the document is
        complete (some fields might not be required if not posted but are required
        otherwise).
        If the journal is locked with a hash table, it will be impossible to change
        some fields afterwards.

        :param soft (bool): if True, future documents are not immediately posted,
            but are set to be auto posted automatically at the set accounting date.
            Nothing will be performed on those documents before the accounting date.
        :return Model<account.move>: the documents that have been posted
        """
        if not self.env.su and not self.env.user.has_group('account.group_account_invoice'):
            raise AccessError(_("You don't have the access rights to post an invoice."))

        for invoice in self.filtered(lambda move: move.is_invoice(include_receipts=True)):
            if (
                invoice.quick_edit_mode
                and invoice.quick_edit_total_amount
                and invoice.currency_id.compare_amounts(invoice.quick_edit_total_amount, invoice.amount_total) != 0
            ):
                raise UserError(_(
                    "The current total is %s but the expected total is %s. In order to post the invoice/bill, "
                    "you can adjust its lines or the expected Total (tax inc.).",
                    formatLang(self.env, invoice.amount_total, currency_obj=invoice.currency_id),
                    formatLang(self.env, invoice.quick_edit_total_amount, currency_obj=invoice.currency_id),
                ))
            if invoice.partner_bank_id and not invoice.partner_bank_id.active:
                raise UserError(_(
                    "The recipient bank account linked to this invoice is archived.\n"
                    "So you cannot confirm the invoice."
                ))
            if float_compare(invoice.amount_total, 0.0, precision_rounding=invoice.currency_id.rounding) < 0:
                raise UserError(_(
                    "You cannot validate an invoice with a negative total amount. "
                    "You should create a credit note instead. "
                    "Use the action menu to transform it into a credit note or refund."
                ))

            if not invoice.partner_id:
                if invoice.is_sale_document():
                    raise UserError(_("The field 'Customer' is required, please complete it to validate the Customer Invoice."))
                elif invoice.is_purchase_document():
                    raise UserError(_("The field 'Vendor' is required, please complete it to validate the Vendor Bill."))

            # Handle case when the invoice_date is not set. In that case, the invoice_date is set at today and then,
            # lines are recomputed accordingly.
            if not invoice.invoice_date:
                if invoice.is_sale_document(include_receipts=True):
                    invoice.invoice_date = fields.Date.context_today(self)
                elif invoice.is_purchase_document(include_receipts=True):
                    if not self.env.context.get('is_redo_move'):
                        raise UserError(_("The Bill/Refund date is required to validate this document."))

        for move in self:
            if move.state == 'posted':
                if not self.env.context.get('is_redo_move'):
                    raise UserError(_('The entry %s (id %s) is already posted.') % (move.name, move.id))
            if not move.line_ids.filtered(lambda line: line.display_type not in ('line_section', 'line_note')):
                raise UserError(_('You need to add a line before posting.'))
            if not soft and move.auto_post != 'no' and move.date > fields.Date.context_today(self):
                date_msg = move.date.strftime(get_lang(self.env).date_format)
                raise UserError(_("This move is configured to be auto-posted on %s", date_msg))
            if not move.journal_id.active:
                if not self.env.context.get('is_redo_move'):
                    raise UserError(_(
                        "You cannot post an entry in an archived journal (%(journal)s)",
                        journal=move.journal_id.display_name,
                    ))
            if move.display_inactive_currency_warning:
                raise UserError(_(
                    "You cannot validate a document with an inactive currency: %s",
                    move.currency_id.name
                ))

            if move.line_ids.account_id.filtered(lambda account: account.deprecated):
                if not self.env.context.get('is_redo_move'):
                    raise UserError(_("A line of this move is using a deprecated account, you cannot post it."))

        if soft:
            future_moves = self.filtered(lambda move: move.date > fields.Date.context_today(self))
            for move in future_moves:
                if move.auto_post == 'no':
                    move.auto_post = 'at_date'
                msg = _('This move will be posted at the accounting date: %(date)s', date=format_date(self.env, move.date))
                move.message_post(body=msg)
            to_post = self - future_moves
        else:
            to_post = self

        for move in to_post:
            affects_tax_report = move._affect_tax_report()
            lock_dates = move._get_violated_lock_dates(move.date, affects_tax_report)
            if lock_dates:
                move.date = move._get_accounting_date(move.invoice_date or move.date, affects_tax_report)

        # Create the analytic lines in batch is faster as it leads to less cache invalidation.
        to_post.line_ids._create_analytic_lines()

        # Trigger copying for recurring invoices
        to_post.filtered(lambda m: m.auto_post not in ('no', 'at_date'))._copy_recurring_entries()

        for invoice in to_post:
            # Fix inconsistencies that may occure if the OCR has been editing the invoice at the same time of a user. We force the
            # partner on the lines to be the same as the one on the move, because that's the only one the user can see/edit.
            wrong_lines = invoice.is_invoice() and invoice.line_ids.filtered(lambda aml:
                aml.partner_id != invoice.commercial_partner_id
                and aml.display_type not in ('line_note', 'line_section')
            )
            if wrong_lines:
                wrong_lines.write({'partner_id': invoice.commercial_partner_id.id})

        to_post.write({
            'state': 'posted',
            'posted_before': True,
        })

        for invoice in to_post:
            invoice.message_subscribe([
                p.id
                for p in [invoice.partner_id]
                if p not in invoice.sudo().message_partner_ids
            ])

            if (
                invoice.is_sale_document()
                and invoice.journal_id.sale_activity_type_id
                and (invoice.journal_id.sale_activity_user_id or invoice.invoice_user_id).id not in (self.env.ref('base.user_root').id, False)
            ):
                invoice.activity_schedule(
                    date_deadline=min((date for date in invoice.line_ids.mapped('date_maturity') if date), default=invoice.date),
                    activity_type_id=invoice.journal_id.sale_activity_type_id.id,
                    summary=invoice.journal_id.sale_activity_note,
                    user_id=invoice.journal_id.sale_activity_user_id.id or invoice.invoice_user_id.id,
                )

        customer_count, supplier_count = defaultdict(int), defaultdict(int)
        for invoice in to_post:
            if invoice.is_sale_document():
                customer_count[invoice.partner_id] += 1
            elif invoice.is_purchase_document():
                supplier_count[invoice.partner_id] += 1
            elif invoice.move_type == 'entry':
                sale_amls = invoice.line_ids.filtered(lambda line: line.partner_id and line.account_id.account_type == 'asset_receivable')
                for partner in sale_amls.mapped('partner_id'):
                    customer_count[partner] += 1
                purchase_amls = invoice.line_ids.filtered(lambda line: line.partner_id and line.account_id.account_type == 'liability_payable')
                for partner in purchase_amls.mapped('partner_id'):
                    supplier_count[partner] += 1
        for partner, count in customer_count.items():
            (partner | partner.commercial_partner_id)._increase_rank('customer_rank', count)
        for partner, count in supplier_count.items():
            (partner | partner.commercial_partner_id)._increase_rank('supplier_rank', count)

        # Trigger action for paid invoices if amount is zero
        to_post.filtered(
            lambda m: m.is_invoice(include_receipts=True) and m.currency_id.is_zero(m.amount_total)
        )._invoice_paid_hook()

        return to_post

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    costo_final = fields.Monetary(string='Costo Final',compute='_compute_costo_final', store=True, currency_field='currency_id')

    @api.depends('product_id')
    def _compute_costo_final(self):
        for line in self:
            costo_final_factura = line.move_id.purchase_id.order_line.filtered(lambda x: x.product_id.id == line.product_id.id).mapped('x_studio_costo_final')
            line.costo_final = costo_final_factura[0] if costo_final_factura else 0

    def write(self, vals):
        if not vals:
            return True
        protected_fields = self._get_lock_date_protected_fields()
        account_to_write = self.env['account.account'].browse(vals['account_id']) if 'account_id' in vals else None
        # Check writing a deprecated account.
        if account_to_write and account_to_write.deprecated:
            raise UserError(_('You cannot use a deprecated account.'))
        inalterable_fields = set(self._get_integrity_hash_fields()).union({'inalterable_hash', 'secure_sequence_number'})
        hashed_moves = self.move_id.filtered('inalterable_hash')
        violated_fields = set(vals) & inalterable_fields
        if hashed_moves and violated_fields:
            raise UserError(_(
                "You cannot edit the following fields: %s.\n"
                "The following entries are already hashed:\n%s",
                ', '.join(f['string'] for f in self.fields_get(violated_fields).values()),
                '\n'.join(hashed_moves.mapped('name')),
            ))
        line_to_write = self
        vals = self._sanitize_vals(vals)
        for line in self:
            if not any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in vals):
                line_to_write -= line
                continue

            if line.parent_state == 'posted':
                if not self.env.context.get('is_redo_move'):
                    if any(key in vals for key in ('tax_ids', 'tax_line_id')):
                        raise UserError(_('You cannot modify the taxes related to a posted journal item, you should reset the journal entry to draft to do so.'))

            # Check the lock date.
            if line.parent_state == 'posted' and any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in protected_fields['fiscal']):
                line.move_id._check_fiscalyear_lock_date()

            # Check the tax lock date.
            if line.parent_state == 'posted' and any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in protected_fields['tax']):
                line._check_tax_lock_date()

            # Check the reconciliation.
            if any(self.env['account.move']._field_will_change(line, vals, field_name) for field_name in protected_fields['reconciliation']):
                line._check_reconciliation()

        move_container = {'records': self.move_id}
        with self.move_id._check_balanced(move_container),\
             self.move_id._sync_dynamic_lines(move_container),\
             self._sync_invoice({'records': self}):
            self = line_to_write
            if not self:
                return True
            # Tracking stuff can be skipped for perfs using tracking_disable context key
            if not self.env.context.get('tracking_disable', False):
                # Get all tracked fields (without related fields because these fields must be manage on their own model)
                tracking_fields = []
                for value in vals:
                    field = self._fields[value]
                    if hasattr(field, 'related') and field.related:
                        continue # We don't want to track related field.
                    if hasattr(field, 'tracking') and field.tracking:
                        tracking_fields.append(value)
                ref_fields = self.env['account.move.line'].fields_get(tracking_fields)

                # Get initial values for each line
                move_initial_values = {}
                for line in self.filtered(lambda l: l.move_id.posted_before): # Only lines with posted once move.
                    for field in tracking_fields:
                        # Group initial values by move_id
                        if line.move_id.id not in move_initial_values:
                            move_initial_values[line.move_id.id] = {}
                        move_initial_values[line.move_id.id].update({field: line[field]})

            result = super().write(vals)
            self.move_id._synchronize_business_models(['line_ids'])
            if any(field in vals for field in ['account_id', 'currency_id']):
                if not self.env.context.get('is_redo_move'):
                    self._check_constrains_account_id_journal_id()

            if not self.env.context.get('tracking_disable', False):
                # Log changes to move lines on each move
                for move_id, modified_lines in move_initial_values.items():
                    for line in self.filtered(lambda l: l.move_id.id == move_id):
                        tracking_value_ids = line._mail_track(ref_fields, modified_lines)[1]
                        if tracking_value_ids:
                            msg = _(
                                "Journal Item %s updated",
                                line._get_html_link(title=f"#{line.id}")
                            )
                            line.move_id._message_log(
                                body=msg,
                                tracking_value_ids=tracking_value_ids
                            )
        return result


class RedoWizard(models.TransientModel):
    _name = 'account_ext.redo.wizard'
    
    def redo(self):
        active_ids = self._context.get('active_ids', [])
        am = self.env['account.move'].search(
            [('id','in',active_ids)]
        )
        for move in am.with_progress(msg="Regenerando Asientos :3"):
            move.redo_assets()
            self.env.cr.commit()    
            self.env['account.move.line'].create(move._stock_account_prepare_anglo_saxon_out_lines_vals())
            move.is_redo_move = True

# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    order_id = fields.Char(compute='_compute_order_id', string='Pedido')
    
    def _compute_order_id(self):
        for record in self:
            record.order_id = ''#self.sale_line_ids.order_id.name 56965
        
    