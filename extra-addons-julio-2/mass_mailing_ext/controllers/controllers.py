# -*- coding: utf-8 -*-
# from odoo import http


# class MassMailingExt(http.Controller):
#     @http.route('/mass_mailing_ext/mass_mailing_ext', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mass_mailing_ext/mass_mailing_ext/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('mass_mailing_ext.listing', {
#             'root': '/mass_mailing_ext/mass_mailing_ext',
#             'objects': http.request.env['mass_mailing_ext.mass_mailing_ext'].search([]),
#         })

#     @http.route('/mass_mailing_ext/mass_mailing_ext/objects/<model("mass_mailing_ext.mass_mailing_ext"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mass_mailing_ext.object', {
#             'object': obj
#         })
