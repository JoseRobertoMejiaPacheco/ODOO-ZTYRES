# -*- coding: utf-8 -*-
# from odoo import http


# class AccountExt(http.Controller):
#     @http.route('/account_ext/account_ext', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/account_ext/account_ext/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('account_ext.listing', {
#             'root': '/account_ext/account_ext',
#             'objects': http.request.env['account_ext.account_ext'].search([]),
#         })

#     @http.route('/account_ext/account_ext/objects/<model("account_ext.account_ext"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('account_ext.object', {
#             'object': obj
#         })
