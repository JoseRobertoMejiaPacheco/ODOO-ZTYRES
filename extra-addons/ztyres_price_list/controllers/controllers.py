# -*- coding: utf-8 -*-
# from odoo import http


# class ZtyresPriceList(http.Controller):
#     @http.route('/ztyres_price_list/ztyres_price_list', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ztyres_price_list/ztyres_price_list/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ztyres_price_list.listing', {
#             'root': '/ztyres_price_list/ztyres_price_list',
#             'objects': http.request.env['ztyres_price_list.ztyres_price_list'].search([]),
#         })

#     @http.route('/ztyres_price_list/ztyres_price_list/objects/<model("ztyres_price_list.ztyres_price_list"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ztyres_price_list.object', {
#             'object': obj
#         })
