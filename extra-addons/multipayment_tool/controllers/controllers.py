# -*- coding: utf-8 -*-
# from odoo import http


# class MultipaymentTool(http.Controller):
#     @http.route('/multipayment_tool/multipayment_tool', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/multipayment_tool/multipayment_tool/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('multipayment_tool.listing', {
#             'root': '/multipayment_tool/multipayment_tool',
#             'objects': http.request.env['multipayment_tool.multipayment_tool'].search([]),
#         })

#     @http.route('/multipayment_tool/multipayment_tool/objects/<model("multipayment_tool.multipayment_tool"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('multipayment_tool.object', {
#             'object': obj
#         })
