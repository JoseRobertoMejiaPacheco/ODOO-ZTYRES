# -*- coding: utf-8 -*-
# from odoo import http


# class SaleCustomizations(http.Controller):
#     @http.route('/sale_customizations/sale_customizations', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_customizations/sale_customizations/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_customizations.listing', {
#             'root': '/sale_customizations/sale_customizations',
#             'objects': http.request.env['sale_customizations.sale_customizations'].search([]),
#         })

#     @http.route('/sale_customizations/sale_customizations/objects/<model("sale_customizations.sale_customizations"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_customizations.object', {
#             'object': obj
#         })
