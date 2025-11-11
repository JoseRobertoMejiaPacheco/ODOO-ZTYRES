# -*- coding: utf-8 -*-
# from odoo import http


# class SupplyChainReceipt(http.Controller):
#     @http.route('/supply_chain_receipt/supply_chain_receipt', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/supply_chain_receipt/supply_chain_receipt/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('supply_chain_receipt.listing', {
#             'root': '/supply_chain_receipt/supply_chain_receipt',
#             'objects': http.request.env['supply_chain_receipt.supply_chain_receipt'].search([]),
#         })

#     @http.route('/supply_chain_receipt/supply_chain_receipt/objects/<model("supply_chain_receipt.supply_chain_receipt"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('supply_chain_receipt.object', {
#             'object': obj
#         })
