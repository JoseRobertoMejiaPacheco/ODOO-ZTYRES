# -*- coding: utf-8 -*-
# from odoo import http


# class PyDiscounts(http.Controller):
#     @http.route('/py_discounts/py_discounts', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/py_discounts/py_discounts/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('py_discounts.listing', {
#             'root': '/py_discounts/py_discounts',
#             'objects': http.request.env['py_discounts.py_discounts'].search([]),
#         })

#     @http.route('/py_discounts/py_discounts/objects/<model("py_discounts.py_discounts"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('py_discounts.object', {
#             'object': obj
#         })
