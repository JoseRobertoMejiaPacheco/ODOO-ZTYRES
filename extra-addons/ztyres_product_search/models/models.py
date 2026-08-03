from odoo import models, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if name:
            product_ids = list(self._search(
                [('default_code', '=like', f'{name}%')] + args,
                limit=limit,
                access_rights_uid=name_get_uid
            ))

            if product_ids:
                return product_ids
        
        return super()._name_search(
            name=name,
            args=args,
            operator=operator,
            limit=limit,
            name_get_uid=name_get_uid
        )