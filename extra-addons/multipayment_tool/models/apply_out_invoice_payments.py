# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ApplyOutInvoicePaymentsLine(models.Model):
    _inherit = 'apply_out_invoice.payments_line'

    payment_form_id = fields.One2many(
        'multipayment_tool.payment_form', 'payments_line_id',
        string='Payment Form', ondelete='cascade')
    payment_amount = fields.Monetary(
        compute='_compute_payment_amount', string='Pago Aplicado',
        currency_field='currency_id')
    currency_id = fields.Many2one(
        related='payment_id_to_apply.payment_id.currency_id', string='Moneda')

    def create_data(self):
        for record in self:
            data = []
            payment_form_vals = {}
            # Se lee la columna directamente porque `payment_amount` pasó a ser
            # un campo calculado no almacenado en este módulo.
            self.env.cr.execute(
                "SELECT payment_amount FROM apply_out_invoice_payments_line "
                "WHERE id = %s", (record.id,))
            result = self.env.cr.fetchone()
            if not result or not result[0]:
                continue

            record.payment_id_to_apply.move_ids = [(4, record.invoice_id.id)]
            data.append((0, 0, {
                'move_id': record.invoice_id.id,
                'move_detailed_line_ids': [],
                'payment_origin': 'prev',
                'amount_to_apply': 0,
                'payment_name': record.invoice_id.move_type,
            }))
            data.append((0, 0, {
                'move_id': record.payment_id_to_apply.payment_id.move_id.id,
                'payment_origin': 'new',
                'amount_to_apply': result[0],
                'payment_name': record.payment_id_to_apply.payment_id.move_id.move_type,
            }))
            payment_form_vals['payment_ids'] = data
            payment_form = self.env['multipayment_tool.payment_form'].create(
                payment_form_vals)
            payment_form.payments_line_id = record.id
            record.payment_id_to_apply.amount_pending = 0.0

    @api.depends('payment_form_id.total_payments')
    def _compute_payment_amount(self):
        for record in self:
            record.payment_amount = sum(
                record.payment_form_id.payment_ids
                .filtered(lambda x: x.payment_origin == 'new'
                          and x.payment_name == 'entry')
                .mapped('amount_to_apply'))

    def get_payments_line(self):
        self.ensure_one()
        if self.payment_form_id:
            return {
                'name': 'Pago Aplicado',
                'type': 'ir.actions.act_window',
                'res_model': 'multipayment_tool.payment_form',
                'view_mode': 'form',
                'res_id': self.payment_form_id[0].id,
                'target': 'current',
            }
        return {'type': 'ir.actions.act_window_close'}


class ApplyOutInvoicePayments(models.Model):
    _inherit = 'apply_out_invoice.payments'
    _order = 'create_date desc'

    move_ids = fields.Many2many('account.move', string='Facturas a pagar')
    payment_amount = fields.Monetary(related='payment_id.amount', string='Monto del Pago')
    amount_resudual_payments = fields.Monetary(
        compute='_compute_amount_resudual_payments', string='Importe residual')

    @api.depends('lines.payment_form_id.amount_residual')
    def _compute_amount_resudual_payments(self):
        for record in self:
            record.amount_resudual_payments = sum(
                record.lines.payment_form_id.mapped('amount_residual'))

    @api.depends('lines.payment_amount', 'partner_id', 'payment_id.line_ids')
    def _compute_amount_pending(self):
        """Antes: `round(..., 2)` con float nativo. Ahora se redondea con la
        precisión de la moneda del pago."""
        for record in self:
            currency = (record.currency_id or record.company_id.currency_id
                        or self.env.company.currency_id)
            applied = sum(record.lines.mapped('payment_amount'))
            record.amount_applied = currency.round(applied)
            record.amount_pending = currency.round(
                record.outstanding_amount - applied)

    def get_detailed_info(self):
        for record in self:
            record.lines.unlink()

            lines_to_create = []
            for move in record.move_ids:
                payment_form_vals = {}
                valss = move._get_payment_info()
                if valss and valss.get('payments'):
                    payment_form_vals['payment_ids'] = valss['payments']
                payment_form = self.env['multipayment_tool.payment_form'].create(
                    payment_form_vals)

                lines_to_create.append((0, 0, {
                    'invoice_id': move.id,
                    'payment_form_id': [(4, payment_form.id)],
                }))

            record.write({'lines': lines_to_create})

    def _update_payment(self):
        for record in self:
            if record.state != 'done':
                record.payment_id.unlink_edi_document_ids()
                record.payment_id.update({
                    'l10n_mx_edi_payment_method_id':
                        record.l10n_mx_edi_payment_method_id.id
                })

    def _check_payment_state(self):
        for record in self:
            if record.payment_id.state not in ['posted']:
                raise ValidationError(_('El pago debe estar confirmado'))

    def _check_amounts_to_apply(self):
        """Antes sólo hacía `print()` de tres totales: no validaba nada.

        Ahora comprueba que ninguna factura quede sobrepagada entre pagos y
        notas de crédito, y que no se aplique más de lo que trae el pago.
        """
        for record in self:
            record.lines.payment_form_id._check_amounts()

    def _settle_all_residuals(self):
        """Salda las diferencias de centavos que queden tras conciliar.

        `_create_adjustment_entry` cubre las facturas; aquí se cubre además el
        residuo del PAGO, que en la versión anterior nunca se ajustaba: por eso
        cuando *sobraban* centavos el pago quedaba sin conciliar y el
        complemento no se podía timbrar.
        """
        for record in self:
            target = record.payment_id.get_open_receivable_lines()[:1]
            record.settle_residual(target, _(
                "Ajuste por redondeo - Pago %s") % (record.payment_id.name or ''))

    def apply_payments(self):
        for record in self:
            if record.state == 'done':
                continue
            record._check_amounts_to_apply()
            record._check_payment_state()
            record._check_amount_pending()
            record.payment_id.unlink_edi_document_ids()
            record._update_payment()

            all_payments = record.lines.payment_form_id.payment_ids
            all_payments._create_credit_notes()
            all_payments._reconcile_nc()
            all_payments._reconcile_payment()
            # Ajuste de centavos: primero las facturas, luego el pago.
            all_payments._create_adjustment_entry()
            record._settle_all_residuals()
            all_payments._generate_edi_docs()

            # El pago debe quedar en CERO exacto o no se timbra.
            record.check_fully_applied()
            record.generate_payment_complement()

            if not record.name or record.name == '/':
                record.name = self.env['ir.sequence'].next_by_code(
                    'apply_out_invoice.sequence') or '/'
        return True
