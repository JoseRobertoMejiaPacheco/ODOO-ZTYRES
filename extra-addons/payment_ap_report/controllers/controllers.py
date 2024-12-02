# -*- coding: utf-8 -*-
# from odoo import http


# class PaymentApReport(http.Controller):
#     @http.route('/payment_ap_report/payment_ap_report', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/payment_ap_report/payment_ap_report/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('payment_ap_report.listing', {
#             'root': '/payment_ap_report/payment_ap_report',
#             'objects': http.request.env['payment_ap_report.payment_ap_report'].search([]),
#         })

#     @http.route('/payment_ap_report/payment_ap_report/objects/<model("payment_ap_report.payment_ap_report"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('payment_ap_report.object', {
#             'object': obj
#         })
