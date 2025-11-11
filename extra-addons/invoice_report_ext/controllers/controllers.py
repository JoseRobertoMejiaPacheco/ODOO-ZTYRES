# -*- coding: utf-8 -*-
# from odoo import http


# class InvoiceReportExt(http.Controller):
#     @http.route('/invoice_report_ext/invoice_report_ext', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/invoice_report_ext/invoice_report_ext/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('invoice_report_ext.listing', {
#             'root': '/invoice_report_ext/invoice_report_ext',
#             'objects': http.request.env['invoice_report_ext.invoice_report_ext'].search([]),
#         })

#     @http.route('/invoice_report_ext/invoice_report_ext/objects/<model("invoice_report_ext.invoice_report_ext"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('invoice_report_ext.object', {
#             'object': obj
#         })
