# -*- coding: utf-8 -*-
# from odoo import http


# class ValidateOrder(http.Controller):
#     @http.route('/validate_order/validate_order', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/validate_order/validate_order/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('validate_order.listing', {
#             'root': '/validate_order/validate_order',
#             'objects': http.request.env['validate_order.validate_order'].search([]),
#         })

#     @http.route('/validate_order/validate_order/objects/<model("validate_order.validate_order"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('validate_order.object', {
#             'object': obj
#         })
