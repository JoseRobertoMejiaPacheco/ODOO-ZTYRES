# -*- coding: utf-8 -*-
# from odoo import http


# class ZtyresProductSearch(http.Controller):
#     @http.route('/ztyres_product_search/ztyres_product_search', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ztyres_product_search/ztyres_product_search/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ztyres_product_search.listing', {
#             'root': '/ztyres_product_search/ztyres_product_search',
#             'objects': http.request.env['ztyres_product_search.ztyres_product_search'].search([]),
#         })

#     @http.route('/ztyres_product_search/ztyres_product_search/objects/<model("ztyres_product_search.ztyres_product_search"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ztyres_product_search.object', {
#             'object': obj
#         })
