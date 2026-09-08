# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountPartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'

    apm_id = fields.Many2one(
        'apply_out_invoice.payments',
        string='Aplicación de Pago Múltiple',
        index=True,
        ondelete='set null',
    )

    # def unlink(self):
    #     """Evita romper un complemento de pago ya timbrado."""
    #     blocked = self.filtered(
    #         lambda p: p.apm_id 
    #         and p.apm_id.state == 'done'
    #         and not self.env.context.get('apm_force_unlink')
    #     )
    #     if blocked:
    #         raise UserError(_(
    #             "No se puede desaplicar el pago porque el complemento de pago "
    #             "%s ya está timbrado y está ligado a los UUID de las facturas. "
    #             "Cancele primero el CFDI de pago.",
    #             ", ".join(blocked.mapped('apm_id.name')),
    #         ))
    #     return super().unlink()
