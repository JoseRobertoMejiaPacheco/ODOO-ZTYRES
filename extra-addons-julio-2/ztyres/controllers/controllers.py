# -*- coding: utf-8 -*-
# from odoo import http


# class SaleZtyres(http.Controller):
#     @http.route('/ztyres/ztyres/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ztyres/ztyres/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('ztyres.listing', {
#             'root': '/ztyres/ztyres',
#             'objects': http.request.env['ztyres.ztyres'].search([]),
#         })

#     @http.route('/ztyres/ztyres/objects/<model("ztyres.ztyres"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ztyres.object', {
#             'object': obj
#         })
