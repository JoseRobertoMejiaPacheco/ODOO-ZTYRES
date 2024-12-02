# -*- coding: utf-8 -*-
# from odoo import http


# class SaleLog(http.Controller):
#     @http.route('/sale_log/sale_log', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_log/sale_log/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_log.listing', {
#             'root': '/sale_log/sale_log',
#             'objects': http.request.env['sale_log.sale_log'].search([]),
#         })

#     @http.route('/sale_log/sale_log/objects/<model("sale_log.sale_log"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_log.object', {
#             'object': obj
#         })
