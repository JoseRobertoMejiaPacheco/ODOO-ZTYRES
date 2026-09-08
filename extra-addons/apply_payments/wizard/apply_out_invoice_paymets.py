# -*- coding: utf-8 -*-
"""Aplicación de un pago contra varias facturas (módulo base).

IMPORTANTE PARA EL MANTENIMIENTO
--------------------------------
`multipayment_tool` hereda de este módulo y depende de:

* Los nombres `_compute_amount_pending`, `_compute_outstanding_amount`,
  `_check_amount_pending`, `apply_payments`, `create_partial_reconcile`,
  `get_credit_move_id`, `get_debit_move_id`, `unlink_edi_document_ids`.
* Que `amount_pending` y `amount_applied` sigan siendo `store=True`
  (multipayment_tool escribe `amount_pending = 0.0` en `create_data`).
* Que la vista formulario conserve el botón `apply_payments` con clase
  `btn-default`, el campo `outstanding_amount` y el `tree` de `lines` con el
  campo `payment_amount` (sus xpath los referencian).

No renombrar ni mover esos elementos sin actualizar `multipayment_tool`.
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DATOS FIJOS DEL AJUSTE DE REDONDEO
# ---------------------------------------------------------------------------
# Tolerancia máxima que se salda automáticamente con un asiento de ajuste.
# El código original tenía el tope en 0.05 (`if 0.01 <= residual <= 0.05`) y
# por eso una diferencia de 7 centavos NUNCA se ajustaba: la factura o el pago
# quedaban con saldo y el complemento de pago no se podía timbrar.
ADJUSTMENT_TOLERANCE = 0.07

# Cuenta contable de diferencias por redondeo (código tal como está en la BD).
ADJUSTMENT_ACCOUNT_CODE = '888.88.8888.8888.8888'

# Diario donde se registran los asientos de ajuste.
ADJUSTMENT_JOURNAL_ID = 140
# ---------------------------------------------------------------------------


class ApplyOutInvoicePaymentsLine(models.Model):
    _name = 'apply_out_invoice.payments_line'
    _description = 'Línea de Aplicación de Pagos Múltiple'

    payment_id_to_apply = fields.Many2one(
        'apply_out_invoice.payments', string='Payment',
        ondelete='cascade', index=True)
    company_id = fields.Many2one(
        related='payment_id_to_apply.company_id', store=True, readonly=True)
    currency_id = fields.Many2one(
        related='payment_id_to_apply.currency_id', readonly=True)
    invoice_id = fields.Many2one('account.move', string='Invoice')
    payment_amount = fields.Monetary(
        string='Payment Amount', currency_field='currency_id')
    outstanding_amount = fields.Monetary(
        compute='_compute_outstanding_amount', string='Outstanding Amount',
        currency_field='currency_id',
        help="Saldo pendiente de la factura. Se calcula al vuelo: antes estaba "
             "almacenado y dependía sólo de invoice_id, por lo que mostraba "
             "saldos obsoletos en cuanto se aplicaba cualquier pago.")

    @api.depends('invoice_id', 'invoice_id.amount_residual')
    def _compute_outstanding_amount(self):
        for record in self:
            record.outstanding_amount = abs(record.invoice_id.amount_residual) \
                if record.invoice_id else 0.0


class ApplyOutInvoicePayments(models.Model):
    _name = 'apply_out_invoice.payments'
    _description = 'Aplicación de Pagos Múltiple'

    name = fields.Char(
        string='Name', copy=False, readonly=True, index=True, default='/')
    company_id = fields.Many2one(
        'res.company', string='Compañía', required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Moneda',
        compute='_compute_currency_id', store=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    payment_id = fields.Many2one('account.payment', string='Payment')
    lines = fields.One2many(
        'apply_out_invoice.payments_line', 'payment_id_to_apply',
        string="Payment Lines")

    outstanding_amount = fields.Monetary(
        compute='_compute_outstanding_amount', string='Outstanding Amount',
        currency_field='currency_id')
    amount_pending = fields.Monetary(
        compute='_compute_amount_pending', store=True, string='Amount Pending',
        currency_field='currency_id')
    amount_applied = fields.Monetary(
        compute='_compute_amount_pending', store=True, string='Amount Applied',
        currency_field='currency_id')

    l10n_mx_edi_payment_method_id = fields.Many2one(
        'l10n_mx_edi.payment.method', string='Forma de Pago')
    state = fields.Selection(
        selection=[('draft', 'Sin Timbrar'), ('done', 'Timbrado')],
        compute='_calcular_state', store=True, default='draft')

    adjustment_move_ids = fields.Many2many(
        'account.move', 'apm_adjustment_move_rel', 'apm_id', 'move_id',
        string='Asientos de ajuste generados', copy=False, readonly=True)

    # ------------------------------------------------------------------
    # ORM
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """La secuencia se consume al crear, no al declarar el campo: antes se
        quemaban folios en registros que el usuario descartaba."""
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'apply_out_invoice.sequence') or '/'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Cómputos (NO renombrar: multipayment_tool sobrescribe estos métodos)
    # ------------------------------------------------------------------
    @api.depends('payment_id', 'payment_id.currency_id', 'company_id')
    def _compute_currency_id(self):
        for record in self:
            record.currency_id = (
                record.payment_id.currency_id
                or record.company_id.currency_id
                or self.env.company.currency_id
            )

    @api.depends('payment_id', 'payment_id.move_id.line_ids.amount_residual',
                 'payment_id.move_id.line_ids.amount_residual_currency',
                 'payment_id.move_id.line_ids.reconciled')
    def _compute_outstanding_amount(self):
        for record in self:
            if not record.payment_id:
                record.outstanding_amount = 0.0
                continue
            currency = record.currency_id or record.company_id.currency_id
            # Se suma en lugar de leer el recordset directo: si había más de un
            # apunte abierto, `.amount_residual` lanzaba "Expected singleton".
            lines = record.payment_id.get_open_receivable_lines()
            record.outstanding_amount = currency.round(
                sum(line.apm_residual() for line in lines))

    @api.depends('lines.payment_amount', 'partner_id', 'payment_id.line_ids')
    def _compute_amount_pending(self):
        for record in self:
            currency = (record.currency_id or record.company_id.currency_id
                        or self.env.company.currency_id)
            applied = sum(record.lines.mapped('payment_amount'))
            # Antes: round(..., 3) sobre una moneda de 2 decimales.
            record.amount_applied = currency.round(applied)
            record.amount_pending = currency.round(
                record.outstanding_amount - applied)

    @api.depends('payment_id', 'payment_id.l10n_mx_edi_cfdi_uuid')
    def _calcular_state(self):
        for record in self:
            record.state = 'done' if (
                record.payment_id and record.payment_id.l10n_mx_edi_cfdi_uuid
            ) else 'draft'

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """En un onchange el recordset es virtual: se vacía con (5,), no con
        unlink()."""
        self.lines = [(5, 0, 0)]

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def get_partner_payments(self):
        self.ensure_one()
        domain = [
            ('payment_type', '=', 'inbound'),
            ('state', '=', 'posted'),
            ('is_reconciled', '=', False),
            ('line_ids.amount_residual', '>', 0),
            ('line_ids.account_id.account_type', '=', 'asset_receivable'),
            ('line_ids.reconciled', '=', False),
            ('partner_id', '=', self.partner_id.id),
        ]
        return {
            "type": "ir.actions.act_window",
            "name": _("Pagos de %s") % (
                self.partner_id.name or _('No hay cliente seleccionado')),
            "view_mode": "tree",
            "view_id": self.env.ref(
                'apply_payments.view_account_payment_tree_with_selection').id,
            "res_model": "account.payment",
            "context": {'create': False, 'edit': False},
            "target": "new",
            "domain": domain,
        }

    def action_view_adjustment_moves(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Asientos de ajuste'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.adjustment_move_ids.ids)],
        }

    # ------------------------------------------------------------------
    # Validaciones
    # ------------------------------------------------------------------
    def _check_amount_pending(self):
        """Nombre conservado: multipayment_tool lo invoca.

        Antes: `if not record.amount_pending == float(0)` — comparación exacta
        de floats sobre un valor redondeado a 3 decimales. Ahora se compara con
        la precisión de la moneda y se admite una diferencia dentro de la
        tolerancia, que después se salda con un asiento de ajuste.
        """
        for record in self:
            currency = record.currency_id or record.company_id.currency_id
            pending = record.amount_pending
            if currency.is_zero(pending):
                continue
            if abs(pending) <= record._get_tolerance() + currency.rounding / 2:
                continue
            raise UserError(_(
                "El pago debe ser aplicado en su totalidad y debe ser exacto.\n"
                "Diferencia: %(pending)s\n"
                "Tolerancia permitida: %(tol)s\n\n"
                "Corrija los importes o registre una nota de crédito por la "
                "diferencia.",
                pending=pending, tol=record._get_tolerance()))

    def _get_tolerance(self):
        """Tolerancia en duro: ver ADJUSTMENT_TOLERANCE arriba (0.07)."""
        self.ensure_one()
        return abs(ADJUSTMENT_TOLERANCE)

    def _get_adjustment_journal(self):
        """Diario en duro: ver ADJUSTMENT_JOURNAL_ID arriba (140)."""
        self.ensure_one()
        journal = self.env['account.journal'].browse(ADJUSTMENT_JOURNAL_ID).exists()
        if not journal:
            raise UserError(_(
                "No existe el diario de ajustes con id %s. Ajuste la constante "
                "ADJUSTMENT_JOURNAL_ID en apply_out_invoice_paymets.py.",
                ADJUSTMENT_JOURNAL_ID))
        return journal

    def _get_adjustment_account(self):
        """Cuenta en duro: ver ADJUSTMENT_ACCOUNT_CODE arriba."""
        self.ensure_one()
        account_model = self.env['account.account']
        account = account_model.search([
            ('code', '=', ADJUSTMENT_ACCOUNT_CODE),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not account:
            account = account_model.search(
                [('code', '=', ADJUSTMENT_ACCOUNT_CODE)], limit=1)
        if not account:
            raise UserError(_(
                "No existe la cuenta de diferencias por redondeo con código %s. "
                "Ajuste la constante ADJUSTMENT_ACCOUNT_CODE en "
                "apply_out_invoice_paymets.py.", ADJUSTMENT_ACCOUNT_CODE))
        return account

    # ------------------------------------------------------------------
    # Proceso (flujo base; multipayment_tool lo sobrescribe por completo)
    # ------------------------------------------------------------------
    def apply_payments(self):
        for record in self:
            if record.state == 'done':
                continue
            record._check_amount_pending()
            record.payment_id.unlink_edi_document_ids()
            record.payment_id.update({
                'l10n_mx_edi_payment_method_id':
                    record.l10n_mx_edi_payment_method_id.id
            })
            credit_line = record.payment_id.get_credit_move_id()
            for line in record.lines:
                record.create_partial_reconcile(
                    credit_move_id=credit_line.id,
                    debit_move_id=line.invoice_id.get_debit_move_id().id,
                    amount=line.payment_amount,
                )
                record.settle_residual(
                    line.invoice_id.get_open_receivable_lines()[:1],
                    _("Ajuste por redondeo - %s") % (line.invoice_id.name or ''))
            record.settle_residual(
                credit_line, _("Ajuste por redondeo - Pago %s")
                % (record.payment_id.name or ''))
            record.check_fully_applied()
            record.generate_payment_complement()
        return True

    def check_fully_applied(self):
        """Verificación final: si el pago no quedó en CERO exacto no se timbra."""
        self.ensure_one()
        currency = self.currency_id
        remaining = sum(
            line.apm_residual()
            for line in self.payment_id.get_open_receivable_lines())
        if not currency.is_zero(remaining):
            raise UserError(_(
                "El pago quedó con un saldo de %s después de aplicarlo. No se "
                "generará el complemento de pago porque el CFDI debe cuadrar "
                "al centavo.", currency.round(remaining)))

    def generate_payment_complement(self):
        self.ensure_one()
        payment = self.payment_id
        if hasattr(payment, 'action_l10n_mx_edi_force_generate_cfdi'):
            payment.action_l10n_mx_edi_force_generate_cfdi()
        if hasattr(payment, 'action_process_edi_web_services'):
            payment.action_process_edi_web_services()

    # ------------------------------------------------------------------
    # Conciliación
    # ------------------------------------------------------------------
    def create_partial_reconcile(self, credit_move_id, debit_move_id, amount):
        """Firma original conservada (multipayment_tool la llama con ids).

        Antes se ponía el mismo número en `amount`, `debit_amount_currency` y
        `credit_amount_currency`, lo que descuadra en cuanto la moneda del
        apunte no es la de la compañía. Ahora `amount` va en moneda de la
        compañía y cada `*_amount_currency` en la moneda de su apunte, y todo
        se topa al saldo real para no sobre-conciliar.
        """
        line_model = self.env['account.move.line']
        credit_line = credit_move_id if isinstance(credit_move_id, models.Model) \
            else line_model.browse(credit_move_id)
        debit_line = debit_move_id if isinstance(debit_move_id, models.Model) \
            else line_model.browse(debit_move_id)
        credit_line = credit_line[:1]
        debit_line = debit_line[:1]
        if not credit_line or not debit_line:
            return self.env['account.partial.reconcile']

        company = self.company_id or self.env.company
        company_currency = company.currency_id
        currency = self.currency_id or company_currency

        amount = currency.round(amount)
        if currency.is_zero(amount):
            return self.env['account.partial.reconcile']

        debit_amount = self._convert_to_line_currency(debit_line, amount, currency)
        credit_amount = self._convert_to_line_currency(credit_line, amount, currency)

        if currency == company_currency:
            amount_company = amount
        else:
            amount_company = currency._convert(
                amount, company_currency, company,
                max(credit_line.date, debit_line.date))

        amount_company = min(
            company_currency.round(amount_company),
            abs(debit_line.amount_residual),
            abs(credit_line.amount_residual))
        debit_amount = min(
            debit_line.currency_id.round(debit_amount), debit_line.apm_residual())
        credit_amount = min(
            credit_line.currency_id.round(credit_amount), credit_line.apm_residual())

        if company_currency.is_zero(amount_company) \
                and currency.is_zero(debit_amount):
            return self.env['account.partial.reconcile']

        return self.env['account.partial.reconcile'].create({
            'amount': amount_company,
            'debit_amount_currency': debit_amount,
            'credit_amount_currency': credit_amount,
            'debit_move_id': debit_line.id,
            'credit_move_id': credit_line.id,
            'apm_id': self.id,
        })

    def _convert_to_line_currency(self, line, amount, from_currency):
        line_currency = line.currency_id or self.company_id.currency_id
        if line_currency == from_currency:
            return amount
        return from_currency._convert(
            amount, line_currency, self.company_id,
            line.date or fields.Date.context_today(self))

    # ------------------------------------------------------------------
    # Motor de ajuste por diferencia de centavos
    # ------------------------------------------------------------------
    def settle_residual(self, target_line, label):
        """Salda el residuo de un apunte si cabe dentro de la tolerancia.

        Corazón de la corrección de los ±centavos: sin esto, una diferencia de
        0.07 deja la factura (o el pago) sin conciliar y el complemento de pago
        sale con importes que el SAT rechaza porque
        ImpSaldoInsoluto != ImpSaldoAnt - ImpPagado.
        """
        self.ensure_one()
        target_line = target_line[:1]
        if not target_line:
            return self.env['account.move']
        currency = self.currency_id
        residual = target_line.apm_residual()
        if currency.is_zero(residual):
            return self.env['account.move']
        if residual > self._get_tolerance() + currency.rounding / 2:
            # No es redondeo: es un error de captura. No se toca en automático.
            return self.env['account.move']

        move = self.create_adjustment_move(
            target_line=target_line, amount=None, label=label,
            account=self._get_adjustment_account())
        if move:
            self.adjustment_move_ids = [(4, move.id)]
        return move

    def create_adjustment_move(self, target_line, amount, label, account,
                               journal=None):
        """Crea y concilia un asiento de ajuste contra `target_line`.

        `amount=None` salda el residuo completo (caso redondeo). Con un importe,
        salda parcialmente (caso nota de crédito en modo ajuste contable).
        """
        self.ensure_one()
        journal = journal or self._get_adjustment_journal()
        company_currency = self.company_id.currency_id
        line_currency = target_line.currency_id or company_currency

        if amount is None:
            balance = -target_line.amount_residual
            amount_currency = -target_line.amount_residual_currency
        else:
            sign = -1 if target_line.amount_residual > 0 else 1
            amount_currency = sign * line_currency.round(amount)
            balance = amount_currency if line_currency == company_currency \
                else line_currency._convert(
                    amount_currency, company_currency, self.company_id,
                    target_line.date or fields.Date.context_today(self))

        balance = company_currency.round(balance)
        amount_currency = line_currency.round(amount_currency)
        if company_currency.is_zero(balance) \
                and line_currency.is_zero(amount_currency):
            return self.env['account.move']

        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'company_id': self.company_id.id,
            'date': (self.payment_id.date if self.payment_id
                     else fields.Date.context_today(self)),
            'ref': label,
            'line_ids': [
                (0, 0, {
                    'name': label,
                    'account_id': target_line.account_id.id,
                    'partner_id': target_line.partner_id.id,
                    'currency_id': line_currency.id,
                    'debit': balance if balance > 0 else 0.0,
                    'credit': -balance if balance < 0 else 0.0,
                    'amount_currency': amount_currency,
                }),
                (0, 0, {
                    'name': _("%s (contrapartida)") % label,
                    'account_id': account.id,
                    'partner_id': target_line.partner_id.id,
                    'currency_id': line_currency.id,
                    'debit': -balance if balance < 0 else 0.0,
                    'credit': balance if balance > 0 else 0.0,
                    'amount_currency': -amount_currency,
                }),
            ],
        })
        move.action_post()

        adjustment_line = move.line_ids.filtered(lambda l: l.name == label)[:1]
        if not adjustment_line:
            raise UserError(_("No se pudo identificar el apunte de ajuste."))

        self.create_partial_reconcile(
            credit_move_id=(adjustment_line if adjustment_line.credit
                            else target_line).id,
            debit_move_id=(target_line if adjustment_line.credit
                           else adjustment_line).id,
            amount=abs(amount_currency),
        )
        (target_line | adjustment_line).apm_close_full_reconcile()
        return move
