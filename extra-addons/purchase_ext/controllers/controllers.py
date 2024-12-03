# -*- coding: utf-8 -*-
# from odoo import http


# class PurchaseExt(http.Controller):
#     @http.route('/purchase_ext/purchase_ext', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/purchase_ext/purchase_ext/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('purchase_ext.listing', {
#             'root': '/purchase_ext/purchase_ext',
#             'objects': http.request.env['purchase_ext.purchase_ext'].search([]),
#         })

#     @http.route('/purchase_ext/purchase_ext/objects/<model("purchase_ext.purchase_ext"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('purchase_ext.object', {
#             'object': obj
#         })
