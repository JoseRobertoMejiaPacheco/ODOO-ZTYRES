from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def write(self, vals):
        address_fields = {
            'city_id', 'state_id', 'city', 'country_id',
            'l10n_mx_edi_locality_id',
        }
        changed = bool(address_fields & set(vals))
        result = super().write(vals)
        if not changed:
            return result

        SaleOrder = self.env['sale.order']
        orders = SaleOrder.search([
            ('partner_shipping_id', 'in', self.ids),
            ('state', '!=', 'cancel'),
        ])
        drafts = orders.filtered(lambda order: order.state in ('draft', 'sent'))
        if drafts:
            drafts.with_context(
                paqueteria_update=True)._update_paqueteria_line()
        embarques = orders.mapped('picking_ids.embarque_ids').filtered(
            lambda shipment: not shipment.is_delivered)
        if embarques:
            embarques.action_calculate_discount()
        return result
