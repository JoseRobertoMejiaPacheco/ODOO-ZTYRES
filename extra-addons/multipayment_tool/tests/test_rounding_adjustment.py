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
