# -*- coding: utf-8 -*-
import logging

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

RECEIVABLE_TYPES = ('liability_payable', 'asset_receivable')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # ------------------------------------------------------------------
    # Compatibilidad hacia atrás
    # ------------------------------------------------------------------
    def get_balance(self):
        """Saldo pendiente del apunte, en positivo (moneda de la compañía)."""
        self.ensure_one()
        return abs(self.amount_residual)

    # ------------------------------------------------------------------
    # Helpers de saldo
    # ------------------------------------------------------------------
    def apm_residual(self):
        """Saldo pendiente en positivo, expresado en la moneda del apunte.

        Se usa ``amount_residual_currency`` cuando el apunte tiene moneda
        (siempre en Odoo 16) para no perder centavos al convertir.
        """
        self.ensure_one()
        if self.currency_id:
            return abs(self.amount_residual_currency)
        return abs(self.amount_residual)

    def apm_residual_signed(self):
        """Saldo pendiente con signo (positivo = deudor / factura)."""
        self.ensure_one()
        return self.amount_residual

    def apm_check_singleton(self, label):
        """Valida que el filtrado de apuntes por conciliar devuelva uno solo."""
        if len(self) == 1:
            return self
        if not self:
            raise UserError(_(
                "No se encontró un apunte por conciliar en %s. "
                "Verifique que el documento esté publicado y sin conciliar.",
                label,
            ))
        raise UserError(_(
            "Se encontraron %(count)s apuntes por conciliar en %(label)s. "
            "Este caso debe resolverse manualmente desde la contabilidad.",
            count=len(self), label=label,
        ))

    # ------------------------------------------------------------------
    # Cierre de conciliación total
    # ------------------------------------------------------------------
    def apm_close_full_reconcile(self):
        """Crea el ``account.full.reconcile`` cuando todo quedó en cero.

        Al crear parciales a mano, Odoo recalcula bien los saldos y la bandera
        ``reconciled``, pero no genera el registro de conciliación total. Esto
        lo completa para que la vista de asientos y los reportes se vean
        consistentes. Nunca debe bloquear la aplicación del pago, por eso va
        protegido.
        """
        try:
            involved = self._apm_collect_involved_lines()
            if not involved:
                return
            if any(not line.reconciled for line in involved):
                return
            if involved.mapped('full_reconcile_id'):
                return
            partials = involved.matched_debit_ids | involved.matched_credit_ids
            partials = partials.filtered(
                lambda p: p.debit_move_id in involved and p.credit_move_id in involved
            )
            if not partials:
                return
            self.env['account.full.reconcile'].create({
                'partial_reconcile_ids': [(6, 0, partials.ids)],
                'reconciled_line_ids': [(6, 0, involved.ids)],
            })
        except Exception:  # pragma: no cover - nunca debe frenar el proceso
            _logger.warning(
                "apply_payments: no se pudo crear la conciliación total para %s",
                self.ids, exc_info=True,
            )

    def _apm_collect_involved_lines(self):
        """Recorre el grafo de conciliaciones parciales y devuelve los apuntes."""
        visited = set()
        pending = set(self.ids)
        while pending:
            batch = self.browse(list(pending))
            visited |= pending
            partials = batch.matched_debit_ids | batch.matched_credit_ids
            linked = set(partials.mapped('debit_move_id').ids)
            linked |= set(partials.mapped('credit_move_id').ids)
            pending = linked - visited
        return self.browse(list(visited)).exists()
