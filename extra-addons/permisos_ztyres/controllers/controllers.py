# -*- coding: utf-8 -*-
# from odoo import http


# class PermisosZtyres(http.Controller):
#     @http.route('/permisos_ztyres/permisos_ztyres', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/permisos_ztyres/permisos_ztyres/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('permisos_ztyres.listing', {
#             'root': '/permisos_ztyres/permisos_ztyres',
#             'objects': http.request.env['permisos_ztyres.permisos_ztyres'].search([]),
#         })

#     @http.route('/permisos_ztyres/permisos_ztyres/objects/<model("permisos_ztyres.permisos_ztyres"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('permisos_ztyres.object', {
#             'object': obj
#         })
