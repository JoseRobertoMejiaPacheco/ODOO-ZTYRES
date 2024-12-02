# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class SaleOrderVisitLog(models.Model):
    _name = 'sale.order.visit.log'
    _description = 'Visit Log for Sale Order'

    order_id = fields.Many2one('sale.order', string='Sale Order')
    user_id = fields.Many2one('res.users', string='User')
    visit_date = fields.Datetime(string='Visit Date')
    visit_count = fields.Integer(string='Visit Count')


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    user_visit_logs = fields.One2many('sale.order.visit.log', 'order_id', string='Visit Logs', readonly=True)


    def read(self, fields=None, load='_classic_read'):
        if not self._context.get('visited_sale_order'):
            # Marcamos el registro para evitar recursión
            self = self.with_context(visited_sale_order=True)

            # Llamada al método read
            res = super(SaleOrder, self).read(fields=fields, load=load)
            if self:
                if self._name == 'sale.order' and len(self)==1:
                    current_datetime = datetime.now()
                    self.write({'user_visit_logs': [(0, 0, {
                        'user_id': self.env.user.id,
                        'visit_date': current_datetime,
                        'visit_count': 1,
                    })]})
        else:
            # Si ya se ha visitado, simplemente llamamos al método read sin modificaciones
            res = super(SaleOrder, self).read(fields=fields, load=load)

        return res
    # @api.model
    # def read(self, fields=None, load='_classic_read'):
    #     res = super(SaleOrder, self).read(fields=None, load=load)
    #     if isinstance(res, list):
    #         for record in res:
    #             self._create_visit_log(record.get('id'), self._context.get('params', {}).get('model') == 'sale.order')
    #     else:
    #         self._create_visit_log(res.get('id'), self._context.get('params', {}).get('model') == 'sale.order')
    #     return res

    def _create_visit_log(self, order_id, is_form_view=False):
        if order_id and is_form_view:
            order = order_id
            order.write({'user_visit_logs': [(0, 0, {
                'user_id': self.env.user.id,
                'visit_date': fields.Datetime.now(),
                'visit_count': 1,
            })]})
