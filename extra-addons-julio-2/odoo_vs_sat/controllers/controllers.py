# -*- coding: utf-8 -*-
# from odoo import http


# class OdooVsSat(http.Controller):
#     @http.route('/odoo_vs_sat/odoo_vs_sat', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/odoo_vs_sat/odoo_vs_sat/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('odoo_vs_sat.listing', {
#             'root': '/odoo_vs_sat/odoo_vs_sat',
#             'objects': http.request.env['odoo_vs_sat.odoo_vs_sat'].search([]),
#         })

#     @http.route('/odoo_vs_sat/odoo_vs_sat/objects/<model("odoo_vs_sat.odoo_vs_sat"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('odoo_vs_sat.object', {
#             'object': obj
#         })
