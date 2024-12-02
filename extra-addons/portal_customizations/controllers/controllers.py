# -*- coding: utf-8 -*-
# from odoo import http


# class PortalCustomizations(http.Controller):
#     @http.route('/portal_customizations/portal_customizations', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/portal_customizations/portal_customizations/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('portal_customizations.listing', {
#             'root': '/portal_customizations/portal_customizations',
#             'objects': http.request.env['portal_customizations.portal_customizations'].search([]),
#         })

#     @http.route('/portal_customizations/portal_customizations/objects/<model("portal_customizations.portal_customizations"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('portal_customizations.object', {
#             'object': obj
#         })
