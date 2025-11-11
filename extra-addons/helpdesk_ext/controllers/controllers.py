# -*- coding: utf-8 -*-
# from odoo import http


# class HelpdeskExt(http.Controller):
#     @http.route('/helpdesk_ext/helpdesk_ext', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/helpdesk_ext/helpdesk_ext/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('helpdesk_ext.listing', {
#             'root': '/helpdesk_ext/helpdesk_ext',
#             'objects': http.request.env['helpdesk_ext.helpdesk_ext'].search([]),
#         })

#     @http.route('/helpdesk_ext/helpdesk_ext/objects/<model("helpdesk_ext.helpdesk_ext"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('helpdesk_ext.object', {
#             'object': obj
#         })
