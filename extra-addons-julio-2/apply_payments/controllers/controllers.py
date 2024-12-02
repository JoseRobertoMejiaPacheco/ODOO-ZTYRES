# -*- coding: utf-8 -*-
# from odoo import http


# class ApplyPayments(http.Controller):
#     @http.route('/apply_payments/apply_payments', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/apply_payments/apply_payments/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('apply_payments.listing', {
#             'root': '/apply_payments/apply_payments',
#             'objects': http.request.env['apply_payments.apply_payments'].search([]),
#         })

#     @http.route('/apply_payments/apply_payments/objects/<model("apply_payments.apply_payments"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('apply_payments.object', {
#             'object': obj
#         })
