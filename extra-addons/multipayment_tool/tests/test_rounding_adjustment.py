# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests.common import TransactionCase, tagged
from unittest.mock import patch


@tagged('post_install', '-at_install')
class TestRoundingAdjustment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.currency = cls.company.currency_id
        cls.partner = cls.env['res.partner'].with_user(2).create({
            'name': 'APP40037 TEST CUSTOMER',
            'company_type': 'company',
        })
        cls.sale_journal = cls.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', cls.company.id),
        ], limit=1)
        cls.bank_journal = cls.env['account.journal'].search([
            ('type', 'in', ('bank', 'cash')),
            ('company_id', '=', cls.company.id),
        ], limit=1)
        cls.income_account = cls.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('deprecated', '=', False),
            ('company_id', '=', cls.company.id),
        ], limit=1)
        cls.receivable_account = cls.env['account.account'].search([
            ('account_type', '=', 'asset_receivable'),
            ('deprecated', '=', False),
            ('company_id', '=', cls.company.id),
        ], limit=1)
        cls.assertTrue(cls.sale_journal, 'Se requiere un diario de ventas')
        cls.assertTrue(cls.bank_journal, 'Se requiere un diario de banco/caja')
        cls.assertTrue(cls.income_account, 'Se requiere una cuenta de ingresos')
        cls.assertTrue(
            cls.receivable_account, 'Se requiere una cuenta por cobrar activa')
        cls.partner.with_user(2).write({
            'property_account_receivable_id': cls.receivable_account.id,
        })

    def _create_invoice(self, amount):
        invoice = self.env['account.move'].with_user(2).create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.sale_journal.id,
            'invoice_date': fields.Date.context_today(self.env.user),
            'invoice_line_ids': [(0, 0, {
                'name': 'APP40037 invoice shape',
                'quantity': 1.0,
                'price_unit': amount,
                'account_id': self.income_account.id,
                'tax_ids': [(6, 0, [])],
            })],
        })
        invoice.action_post()
        return invoice

    def _create_payment(self, amount):
        payment = self.env['account.payment'].with_user(2).create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner.id,
            'amount': amount,
            'currency_id': self.currency.id,
            'journal_id': self.bank_journal.id,
            'date': fields.Date.context_today(self.env.user),
        })
        payment.action_post()
        return payment

    def _create_payment_form(self, apm, invoice, payment, pay_amount,
                             requested_refund, reason):
        payment_line = apm.lines.filtered(lambda line: line.invoice_id == invoice)[:1]
        form = self.env['multipayment_tool.payment_form'].create({
            'payments_line_id': payment_line.id,
        })
        self.env['multipayment_tool.payments'].create({
            'payment_form_id': form.id,
            'move_id': invoice.id,
            'payment_name': 'out_invoice',
            'payment_origin': 'prev',
            'amount_to_apply': 0.0,
        })
        pay_line = self.env['multipayment_tool.payments'].create({
            'payment_form_id': form.id,
            'move_id': payment.move_id.id,
            'payment_name': 'entry',
            'payment_origin': 'new',
            'amount_to_apply': pay_amount,
        })
        refund_line = self.env['multipayment_tool.payments'].create({
            'payment_form_id': form.id,
            'payment_name': 'out_refund',
            'payment_origin': 'new',
            'nc_mode': 'amount',
            'nc_value': requested_refund,
            'amount_to_apply': requested_refund,
            'nc_reason': reason,
        })
        return form, pay_line, refund_line

    def _create_empty_payment_form(self, apm, invoice):
        payment_line = apm.lines.filtered(lambda line: line.invoice_id == invoice)[:1]
        form = self.env['multipayment_tool.payment_form'].create({
            'payments_line_id': payment_line.id,
        })
        self.env['multipayment_tool.payments'].create({
            'payment_form_id': form.id,
            'move_id': invoice.id,
            'payment_name': 'out_invoice',
            'payment_origin': 'prev',
            'amount_to_apply': 0.0,
        })
        return form

    def test_payment_line_does_not_default_to_preconfigured_discount(self):
        invoice = self._create_invoice(1000.00)
        payment = self._create_payment(900.00)
        apm = self.env['apply_out_invoice.payments'].create({
            'partner_id': self.partner.id,
            'payment_id': payment.id,
            'lines': [(0, 0, {'invoice_id': invoice.id})],
        })
        form = self._create_empty_payment_form(apm, invoice)

        pay_line = self.env['multipayment_tool.payments'].new({
            'payment_form_id': form.id,
            'payment_name': 'entry',
            'payment_origin': 'new',
            'amount_to_apply': 900.00,
        })
        pay_line._onchange_discount_id()

        self.assertFalse(pay_line.nc_mode)
        self.assertFalse(pay_line.discount_id)

    def test_new_credit_note_defaults_to_preconfigured_discount(self):
        invoice = self._create_invoice(1000.00)
        payment = self._create_payment(900.00)
        apm = self.env['apply_out_invoice.payments'].create({
            'partner_id': self.partner.id,
            'payment_id': payment.id,
            'lines': [(0, 0, {'invoice_id': invoice.id})],
        })
        form = self._create_empty_payment_form(apm, invoice)

        refund_line = self.env['multipayment_tool.payments'].new({
            'payment_form_id': form.id,
            'payment_name': 'out_refund',
            'payment_origin': 'new',
        })
        refund_line._onchange_discount_id()

        self.assertEqual(refund_line.nc_mode, 'discount')

    def test_preconfigured_discount_uses_invoice_base_not_new_payment(self):
        invoice = self._create_invoice(1000.00)
        payment = self._create_payment(1000.00)
        apm = self.env['apply_out_invoice.payments'].create({
            'partner_id': self.partner.id,
            'payment_id': payment.id,
            'lines': [(0, 0, {'invoice_id': invoice.id})],
        })
        form = self._create_empty_payment_form(apm, invoice)
        self.env['multipayment_tool.payments'].create({
            'payment_form_id': form.id,
            'move_id': payment.move_id.id,
            'payment_name': 'entry',
            'payment_origin': 'new',
            'amount_to_apply': 1000.00,
        })
        discount_2 = self.env['multipayment_tool.discount'].create({
            'name': 'TEST 2%',
            'discount': 2,
        })
        discount_4 = self.env['multipayment_tool.discount'].create({
            'name': 'TEST 4%',
            'discount': 4,
        })

        refund_line = self.env['multipayment_tool.payments'].create({
            'payment_form_id': form.id,
            'payment_name': 'out_refund',
            'payment_origin': 'new',
            'nc_mode': 'discount',
            'discount_id': discount_2.id,
        })
        refund_line.onchange_discount_id()
        amount_2 = refund_line.amount_to_apply

        refund_line.discount_id = discount_4
        refund_line.onchange_discount_id()

        self.assertEqual(self.currency.round(amount_2), 20.00)
        self.assertEqual(self.currency.round(refund_line.amount_to_apply), 40.00)
        self.assertIn('TEST 4%', refund_line.nc_reason)
        self.assertIn('4%', refund_line.nc_reason)
        self.assertEqual(self.currency.round(pay_line.nc_value), 0.0)

    def test_nc_amount_recalculates_when_payment_was_entered_first(self):
        invoice = self._create_invoice(1000.00)
        payment = self._create_payment(900.00)
        apm = self.env['apply_out_invoice.payments'].create({
            'partner_id': self.partner.id,
            'payment_id': payment.id,
            'lines': [(0, 0, {'invoice_id': invoice.id})],
        })
        form = self._create_empty_payment_form(apm, invoice)
        self.env['multipayment_tool.payments'].create({
            'payment_form_id': form.id,
            'move_id': payment.move_id.id,
            'payment_name': 'entry',
            'payment_origin': 'new',
            'amount_to_apply': 900.00,
        })
        refund_line = self.env['multipayment_tool.payments'].create({
            'payment_form_id': form.id,
            'payment_name': 'out_refund',
            'payment_origin': 'new',
            'nc_mode': 'amount',
            'nc_value': 100.00,
            'amount_to_apply': 100.00,
            'nc_reason': 'TEST NC DESPUES DE PAGO',
        })

        form._compute_amounts()
        self.assertEqual(self.currency.round(form.total_payments), 900.00)
        self.assertEqual(self.currency.round(form.total_nc), 100.00)
        self.assertEqual(self.currency.round(form.amount_residual), 0.0)

        refund_line.amount_to_apply = 80.00
        form._compute_amounts()
        self.assertEqual(self.currency.round(form.total_nc), 80.00)
        self.assertEqual(self.currency.round(form.amount_residual), 20.00)

    def test_nc_before_payment_and_later_amount_change_keeps_totals_live(self):
        invoice = self._create_invoice(1000.00)
        payment = self._create_payment(900.00)
        apm = self.env['apply_out_invoice.payments'].create({
            'partner_id': self.partner.id,
            'payment_id': payment.id,
            'lines': [(0, 0, {'invoice_id': invoice.id})],
        })
        form = self._create_empty_payment_form(apm, invoice)
        refund_line = self.env['multipayment_tool.payments'].create({
            'payment_form_id': form.id,
            'payment_name': 'out_refund',
            'payment_origin': 'new',
            'nc_mode': 'amount',
            'nc_value': 100.00,
            'amount_to_apply': 100.00,
            'nc_reason': 'TEST NC ANTES DE PAGO',
        })
        self.env['multipayment_tool.payments'].create({
            'payment_form_id': form.id,
            'move_id': payment.move_id.id,
            'payment_name': 'entry',
            'payment_origin': 'new',
            'amount_to_apply': 900.00,
        })

        form._compute_amounts()
        self.assertEqual(self.currency.round(form.amount_residual), 0.0)

        refund_line.amount_to_apply = 75.00
        form._compute_amounts()
        self.assertEqual(self.currency.round(form.total_nc), 75.00)
        self.assertEqual(self.currency.round(form.amount_residual), 25.00)

    def test_manual_percent_nc_recalculates_when_percentage_changes(self):
        invoice = self._create_invoice(1000.00)
        payment = self._create_payment(900.00)
        apm = self.env['apply_out_invoice.payments'].create({
            'partner_id': self.partner.id,
            'payment_id': payment.id,
            'lines': [(0, 0, {'invoice_id': invoice.id})],
        })
        form = self._create_empty_payment_form(apm, invoice)
        self.env['multipayment_tool.payments'].create({
            'payment_form_id': form.id,
            'move_id': payment.move_id.id,
            'payment_name': 'entry',
            'payment_origin': 'new',
            'amount_to_apply': 900.00,
        })
        refund_line = self.env['multipayment_tool.payments'].new({
            'payment_form_id': form.id,
            'payment_name': 'out_refund',
            'payment_origin': 'new',
            'nc_mode': 'percent',
            'nc_base': 'total',
            'nc_value': 10.00,
            'nc_reason': 'TEST PORCENTAJE MANUAL',
        })

        refund_line.onchange_discount_id()
        self.assertEqual(self.currency.round(refund_line.amount_to_apply), 100.00)

        refund_line.nc_value = 5.00
        refund_line.onchange_discount_id()
        self.assertEqual(self.currency.round(refund_line.amount_to_apply), 50.00)

    def test_manual_percent_nc_can_use_residual_after_payment(self):
        invoice = self._create_invoice(1000.00)
        payment = self._create_payment(900.00)
        apm = self.env['apply_out_invoice.payments'].create({
            'partner_id': self.partner.id,
            'payment_id': payment.id,
            'lines': [(0, 0, {'invoice_id': invoice.id})],
        })
        form = self._create_empty_payment_form(apm, invoice)
        self.env['multipayment_tool.payments'].create({
            'payment_form_id': form.id,
            'move_id': payment.move_id.id,
            'payment_name': 'entry',
            'payment_origin': 'new',
            'amount_to_apply': 900.00,
        })
        refund_line = self.env['multipayment_tool.payments'].new({
            'payment_form_id': form.id,
            'payment_name': 'out_refund',
            'payment_origin': 'new',
            'nc_mode': 'percent',
            'nc_base': 'residual',
            'nc_value': 10.00,
            'nc_reason': 'TEST PORCENTAJE SOBRE SALDO',
        })

        refund_line.onchange_discount_id()
        self.assertEqual(self.currency.round(refund_line.amount_to_apply), 10.00)

    def _assert_cent_difference_goes_to_credit_note(self, payment_amount,
                                                    expected_nc_amount):
        invoice = self._create_invoice(1000.00)
        payment = self._create_payment(payment_amount)
        apm = self.env['apply_out_invoice.payments'].create({
            'partner_id': self.partner.id,
            'payment_id': payment.id,
            'lines': [(0, 0, {'invoice_id': invoice.id})],
        })
        form, pay_line, refund_line = self._create_payment_form(
            apm, invoice, payment, payment_amount, 100.00,
            'TEST DIFERENCIA CENTAVOS A NC')
        before_adjustments = apm.adjustment_move_ids

        payments_model = self.env['multipayment_tool.payments']
        with patch.object(type(payments_model), '_generate_edi_docs',
                          return_value=True), \
                patch.object(type(apm), 'generate_payment_complement',
                             return_value=True):
            apm.apply_payments()

        self.assertEqual(
            self.currency.round(refund_line.amount_to_apply),
            expected_nc_amount)
        self.assertEqual(
            self.currency.round(refund_line.move_id.amount_total),
            expected_nc_amount)
        self.assertEqual(self.currency.round(form.amount_residual), 0.0)
        self.assertEqual(self.currency.round(invoice.amount_residual), 0.0)
        self.assertEqual(
            self.currency.round(sum(
                line.apm_residual()
                for line in payment.get_open_receivable_lines())),
            0.0)
        self.assertFalse(
            apm.adjustment_move_ids - before_adjustments,
            'La diferencia de centavos debe absorberse en la NC, no en ajuste')

    def test_two_cents_overpayment_reduces_credit_note_without_adjustment(self):
        """Factura 1000, pago 900.02, NC capturada 100.00 -> NC 99.98."""
        self._assert_cent_difference_goes_to_credit_note(900.02, 99.98)

    def test_two_cents_underpayment_increases_credit_note_without_adjustment(self):
        """Factura 1000, pago 899.98, NC capturada 100.00 -> NC 100.02."""
        self._assert_cent_difference_goes_to_credit_note(899.98, 100.02)

    def test_app40463_shape_distributes_global_two_cents_to_last_nc(self):
        """APP40463: dos lineas suman 0.02 mas que el pago real.

        La NC no debe topar en 0.02 por el pendiente del pago. Debe cubrir el
        saldo de factura y la ultima NC absorbe el diferencial global.
        """
        discount_3 = self.env['multipayment_tool.discount'].create({
            'name': 'TEST 3% Financiero',
            'discount': 3,
        })
        discount_2 = self.env['multipayment_tool.discount'].create({
            'name': 'TEST 2% Financiero',
            'discount': 2,
        })
        invoice_1 = self._create_invoice(50762.32)
        invoice_2 = self._create_invoice(3824.60)
        payment = self._create_payment(47911.31)
        apm = self.env['apply_out_invoice.payments'].create({
            'partner_id': self.partner.id,
            'payment_id': payment.id,
            'lines': [
                (0, 0, {'invoice_id': invoice_1.id}),
                (0, 0, {'invoice_id': invoice_2.id}),
            ],
        })
        form_1 = self._create_empty_payment_form(apm, invoice_1)
        form_2 = self._create_empty_payment_form(apm, invoice_2)
        self.env['multipayment_tool.payments'].create({
            'payment_form_id': form_1.id,
            'payment_name': 'out_refund',
            'payment_origin': 'prev',
            'amount_to_apply': 5076.23,
        })
        nc_1 = self.env['multipayment_tool.payments'].create({
            'payment_form_id': form_1.id,
            'payment_name': 'out_refund',
            'payment_origin': 'new',
            'nc_mode': 'discount',
            'discount_id': discount_3.id,
            'amount_to_apply': 1522.87,
            'nc_reason': 'TEST APP40463 NC 1',
        })
        nc_2 = self.env['multipayment_tool.payments'].create({
            'payment_form_id': form_2.id,
            'payment_name': 'out_refund',
            'payment_origin': 'new',
            'nc_mode': 'discount',
            'discount_id': discount_2.id,
            'amount_to_apply': 76.49,
            'nc_reason': 'TEST APP40463 NC 2',
        })
        self.env['multipayment_tool.payments'].create({
            'payment_form_id': form_1.id,
            'move_id': payment.move_id.id,
            'payment_name': 'entry',
            'payment_origin': 'new',
            'amount_to_apply': 44163.22,
        })
        self.env['multipayment_tool.payments'].create({
            'payment_form_id': form_2.id,
            'move_id': payment.move_id.id,
            'payment_name': 'entry',
            'payment_origin': 'new',
            'amount_to_apply': 3748.11,
        })

        amount_1 = nc_1._balance_global_payment_cents(
            nc_1._cap_new_nc_amount(nc_1._balance_new_nc_amount(
                nc_1.amount_to_apply)))
        amount_2 = nc_2._balance_global_payment_cents(
            nc_2._cap_new_nc_amount(nc_2._balance_new_nc_amount(
                nc_2.amount_to_apply)))

        self.assertEqual(self.currency.round(amount_1), 1522.87)
        self.assertEqual(self.currency.round(amount_2), 76.51)

    def test_app40037_two_invoice_shape_balances_to_zero(self):
        """APP40037 completo: un pago aplicado a dos facturas con dos NC.

        Segunda línea: el usuario puede capturar/calcular 745.78, pero si el
        remanente real de la factura después del pago es 745.77, la NC nueva
        debe nacer por 745.77. No debe quedar el caso inválido de factura
        745.77 + pago 745.77 + NC 745.77 = saldo -745.77.
        """
        invoice_1 = self._create_invoice(2666.77)
        invoice_2 = self._create_invoice(37288.53)
        payment = self._create_payment(39156.19)
        apm = self.env['apply_out_invoice.payments'].create({
            'partner_id': self.partner.id,
            'payment_id': payment.id,
            'lines': [
                (0, 0, {'invoice_id': invoice_1.id}),
                (0, 0, {'invoice_id': invoice_2.id}),
            ],
        })
        form_1, pay_line_1, refund_line_1 = self._create_payment_form(
            apm, invoice_1, payment, 2613.43, 53.34, 'APP40037 TEST 2% FINAN')
        form_2, pay_line_2, refund_line_2 = self._create_payment_form(
            apm, invoice_2, payment, 36542.76, 745.78, 'APP40037 TEST 2% FINAN')

        (form_1 | form_2)._check_amounts()
        self.assertEqual(self.currency.round(apm.amount_applied), 39156.19)
        self.assertEqual(self.currency.round(apm.amount_pending), 0.0)
        before_adjustments = apm.adjustment_move_ids

        payments_model = self.env['multipayment_tool.payments']
        with patch.object(type(payments_model), '_generate_edi_docs',
                          return_value=True), \
                patch.object(type(apm), 'generate_payment_complement',
                             return_value=True):
            apm.apply_payments()

        self.assertEqual(self.currency.round(form_1.invoice_amount_total), 2666.77)
        self.assertEqual(self.currency.round(form_1.total_payments), 2613.43)
        self.assertEqual(self.currency.round(form_1.total_nc), 53.34)
        self.assertEqual(self.currency.round(form_1.amount_residual), 0.0)
        self.assertEqual(self.currency.round(form_2.invoice_amount_total), 37288.53)
        self.assertEqual(self.currency.round(form_2.total_payments), 36542.76)
        self.assertEqual(self.currency.round(form_2.total_nc), 745.77)
        self.assertEqual(self.currency.round(form_2.amount_residual), 0.0)
        self.assertEqual(self.currency.round(refund_line_1.move_id.amount_total), 53.34)
        self.assertEqual(self.currency.round(refund_line_2.move_id.amount_total), 745.77)
        self.assertEqual(self.currency.round(invoice_1.amount_residual), 0.0)
        self.assertEqual(self.currency.round(invoice_2.amount_residual), 0.0)
        self.assertEqual(
            self.currency.round(sum(
                line.apm_residual()
                for line in payment.get_open_receivable_lines())),
            0.0)
        self.assertEqual(apm.state, 'done')
        self.assertEqual(self.currency.round(apm.amount_pending), 0.0)
        apm.apply_payments()
        self.assertEqual(self.currency.round(apm.amount_pending), 0.0)
        self.assertFalse(
            apm.adjustment_move_ids - before_adjustments,
            'APP40037 exacto no debe generar ajuste 888',
        )
