# -*- coding: utf-8 -*-
# from odoo import http


# class ZtyresPartnerLedger(http.Controller):
#     @http.route('/ztyres_partner_ledger/ztyres_partner_ledger', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ztyres_partner_ledger/ztyres_partner_ledger/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ztyres_partner_ledger.listing', {
#             'root': '/ztyres_partner_ledger/ztyres_partner_ledger',
#             'objects': http.request.env['ztyres_partner_ledger.ztyres_partner_ledger'].search([]),
#         })

#     @http.route('/ztyres_partner_ledger/ztyres_partner_ledger/objects/<model("ztyres_partner_ledger.ztyres_partner_ledger"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ztyres_partner_ledger.object', {
#             'object': obj
#         })
