# -*- coding: utf-8 -*-
# from odoo import http


# class ZtyresTimbradoGenerico(http.Controller):
#     @http.route('/ztyres_timbrado_generico/ztyres_timbrado_generico', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ztyres_timbrado_generico/ztyres_timbrado_generico/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ztyres_timbrado_generico.listing', {
#             'root': '/ztyres_timbrado_generico/ztyres_timbrado_generico',
#             'objects': http.request.env['ztyres_timbrado_generico.ztyres_timbrado_generico'].search([]),
#         })

#     @http.route('/ztyres_timbrado_generico/ztyres_timbrado_generico/objects/<model("ztyres_timbrado_generico.ztyres_timbrado_generico"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ztyres_timbrado_generico.object', {
#             'object': obj
#         })
