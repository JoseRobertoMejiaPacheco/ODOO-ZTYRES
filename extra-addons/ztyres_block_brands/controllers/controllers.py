# -*- coding: utf-8 -*-
# from odoo import http


# class ZtyresBlockBrands(http.Controller):
#     @http.route('/ztyres_block_brands/ztyres_block_brands', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ztyres_block_brands/ztyres_block_brands/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ztyres_block_brands.listing', {
#             'root': '/ztyres_block_brands/ztyres_block_brands',
#             'objects': http.request.env['ztyres_block_brands.ztyres_block_brands'].search([]),
#         })

#     @http.route('/ztyres_block_brands/ztyres_block_brands/objects/<model("ztyres_block_brands.ztyres_block_brands"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ztyres_block_brands.object', {
#             'object': obj
#         })
