# -*- coding: utf-8 -*-
# from odoo import http


# class ZtyresVolumen(http.Controller):
#     @http.route('/ztyres_volumen/ztyres_volumen', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ztyres_volumen/ztyres_volumen/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ztyres_volumen.listing', {
#             'root': '/ztyres_volumen/ztyres_volumen',
#             'objects': http.request.env['ztyres_volumen.ztyres_volumen'].search([]),
#         })

#     @http.route('/ztyres_volumen/ztyres_volumen/objects/<model("ztyres_volumen.ztyres_volumen"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ztyres_volumen.object', {
#             'object': obj
#         })
