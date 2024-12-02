from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def create_invoices(self):
        if len(self)>1:
            raise UserError(_('No es posible realizar una factura de varios pedidos, solicite ayuda a soporte.'))
        self._create_invoices(self.sale_order_ids)

        if self.env.context.get('open_invoices'):
            return self.sale_order_ids.action_view_invoice()

        return {'type': 'ir.actions.act_window_close'}
