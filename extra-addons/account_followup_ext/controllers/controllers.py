# -*- coding: utf-8 -*-
# from odoo import http


# class AccountFollowupExt(http.Controller):
#     @http.route('/account_followup_ext/account_followup_ext', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/account_followup_ext/account_followup_ext/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('account_followup_ext.listing', {
#             'root': '/account_followup_ext/account_followup_ext',
#             'objects': http.request.env['account_followup_ext.account_followup_ext'].search([]),
#         })

#     @http.route('/account_followup_ext/account_followup_ext/objects/<model("account_followup_ext.account_followup_ext"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('account_followup_ext.object', {
#             'object': obj
#         })
