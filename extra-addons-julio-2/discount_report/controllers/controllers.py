# -*- coding: utf-8 -*-
# from odoo import http


# class DiscountReport(http.Controller):
#     @http.route('/discount_report/discount_report', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/discount_report/discount_report/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('discount_report.listing', {
#             'root': '/discount_report/discount_report',
#             'objects': http.request.env['discount_report.discount_report'].search([]),
#         })

#     @http.route('/discount_report/discount_report/objects/<model("discount_report.discount_report"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('discount_report.object', {
#             'object': obj
#         })
