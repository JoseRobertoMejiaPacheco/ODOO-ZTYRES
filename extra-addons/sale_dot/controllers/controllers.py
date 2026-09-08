# -*- coding: utf-8 -*-
# from odoo import http


# class SaleDot(http.Controller):
#     @http.route('/sale_dot/sale_dot', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_dot/sale_dot/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_dot.listing', {
#             'root': '/sale_dot/sale_dot',
#             'objects': http.request.env['sale_dot.sale_dot'].search([]),
#         })

#     @http.route('/sale_dot/sale_dot/objects/<model("sale_dot.sale_dot"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_dot.object', {
#             'object': obj
#         })
