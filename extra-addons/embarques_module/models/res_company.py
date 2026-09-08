from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    paqueteria_product_id = fields.Many2one(
        'product.product', string='Producto de Paquetería',
        domain=[('type', '=', 'service')],
        help='Producto de servicio con el que se cobra la paquetería en el '
             'pedido de venta. Sin él, no se cobra nada.')
    embarque_logistic_nc_product_id = fields.Many2one(
        'product.product', string='Producto para NC Logística',
        domain=[('type', '=', 'service')],
        help='Producto de servicio usado exclusivamente para la nota de '
             'crédito logística generada por Embarques.')

    @api.constrains('paqueteria_product_id', 'embarque_logistic_nc_product_id')
    def _check_service_products(self):
        for company in self:
            for product, label in (
                (company.paqueteria_product_id, _('paquetería')),
                (company.embarque_logistic_nc_product_id, _('NC logística')),
            ):
                if product and product.type != 'service':
                    raise ValidationError(_(
                        'El producto de %s de %s debe ser de tipo Servicio.') % (
                            label, company.display_name))
