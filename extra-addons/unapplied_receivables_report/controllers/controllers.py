# -*- coding: utf-8 -*-
# from odoo import http


# class UnappliedReceivablesReport(http.Controller):
#     @http.route('/unapplied_receivables_report/unapplied_receivables_report', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/unapplied_receivables_report/unapplied_receivables_report/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('unapplied_receivables_report.listing', {
#             'root': '/unapplied_receivables_report/unapplied_receivables_report',
#             'objects': http.request.env['unapplied_receivables_report.unapplied_receivables_report'].search([]),
#         })

#     @http.route('/unapplied_receivables_report/unapplied_receivables_report/objects/<model("unapplied_receivables_report.unapplied_receivables_report"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('unapplied_receivables_report.object', {
#             'object': obj
#         })
