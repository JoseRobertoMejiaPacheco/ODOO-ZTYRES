# -*- coding: utf-8 -*-
# from odoo import http


# class InventoryPositions(http.Controller):
#     @http.route('/inventory_positions/inventory_positions', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/inventory_positions/inventory_positions/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('inventory_positions.listing', {
#             'root': '/inventory_positions/inventory_positions',
#             'objects': http.request.env['inventory_positions.inventory_positions'].search([]),
#         })

#     @http.route('/inventory_positions/inventory_positions/objects/<model("inventory_positions.inventory_positions"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('inventory_positions.object', {
#             'object': obj
#         })
