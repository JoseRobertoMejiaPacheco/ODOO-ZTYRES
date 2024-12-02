# -*- coding: utf-8 -*-
# from odoo import http


# class ZtyresProducts(http.Controller):
#     @http.route('/ztyres_products/ztyres_products', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ztyres_products/ztyres_products/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ztyres_products.listing', {
#             'root': '/ztyres_products/ztyres_products',
#             'objects': http.request.env['ztyres_products.ztyres_products'].search([]),
#         })

#     @http.route('/ztyres_products/ztyres_products/objects/<model("ztyres_products.ztyres_products"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ztyres_products.object', {
#             'object': obj
#         })
