# -*- coding: utf-8 -*-
from odoo import _, models

from .account_move_line import RECEIVABLE_TYPES


class AccountMove(models.Model):
    _inherit = 'account.move'

    def get_open_receivable_lines(self):
        """Apuntes de cliente/proveedor aún no conciliados del documento."""
        return self.line_ids.filtered(
            lambda r: not r.reconciled
            and r.account_id.account_type in RECEIVABLE_TYPES
        )

    def get_debit_move_id(self):
        """Apunte por cobrar de la factura pendiente de conciliar.

        Nombre original conservado (multipayment_tool lo llama), pero ahora
        valida que sea un único apunte en lugar de devolver un recordset que
        reventaba con "Expected singleton" al leer `amount_residual`.
        """
        self.ensure_one()
        return self.get_open_receivable_lines().apm_check_singleton(
            _("la factura %s", self.display_name))
