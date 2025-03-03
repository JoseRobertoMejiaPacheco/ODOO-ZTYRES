# -*- coding: utf-8 -*-
# from odoo import http


# class ZtyresExata(http.Controller):
#     @http.route('/ztyres_exata/ztyres_exata', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ztyres_exata/ztyres_exata/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ztyres_exata.listing', {
#             'root': '/ztyres_exata/ztyres_exata',
#             'objects': http.request.env['ztyres_exata.ztyres_exata'].search([]),
#         })

#     @http.route('/ztyres_exata/ztyres_exata/objects/<model("ztyres_exata.ztyres_exata"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ztyres_exata.object', {
#             'object': obj
#         })
