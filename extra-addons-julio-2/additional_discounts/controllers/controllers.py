# -*- coding: utf-8 -*-
# from odoo import http


# class AdditionalDiscounts(http.Controller):
#     @http.route('/additional_discounts/additional_discounts', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/additional_discounts/additional_discounts/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('additional_discounts.listing', {
#             'root': '/additional_discounts/additional_discounts',
#             'objects': http.request.env['additional_discounts.additional_discounts'].search([]),
#         })

#     @http.route('/additional_discounts/additional_discounts/objects/<model("additional_discounts.additional_discounts"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('additional_discounts.object', {
#             'object': obj
#         })
