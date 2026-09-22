# -*- coding: utf-8 -*-
from odoo import _, models


class AccountPayment(models.Model):
    """El original heredaba con `models.AbstractModel`, lo cual es incorrecto
    para extender un modelo persistente."""
    _inherit = 'account.payment'

    def get_open_receivable_lines(self):
        self.ensure_one()
        return self.move_id.get_open_receivable_lines()

    def get_credit_move_id(self):
        """Apunte del pago pendiente de aplicar. Nombre original conservado."""
        self.ensure_one()
        return self.get_open_receivable_lines().apm_check_singleton(
            _("el pago %s", self.display_name))

    def update_l10n_mx_edi_payment_method_id(self, payment_method_id):
        for record in self:
            record.l10n_mx_edi_payment_method_id = payment_method_id

    def l10n_mx_edi_cfdi_uuid_state(self):
        """Antes hacía `return` dentro del `for`: con varios registros sólo
        evaluaba el primero y devolvía None con recordset vacío."""
        self.ensure_one()
        return 'done' if self.l10n_mx_edi_cfdi_uuid else 'draft'

    def unlink_edi_document_ids(self):
        for record in self:
            if not record.l10n_mx_edi_cfdi_uuid:
                record.edi_document_ids.unlink()
