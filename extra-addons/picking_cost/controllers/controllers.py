# -*- coding: utf-8 -*-
# from odoo import http


# class PickingCost(http.Controller):
#     @http.route('/picking_cost/picking_cost', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/picking_cost/picking_cost/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('picking_cost.listing', {
#             'root': '/picking_cost/picking_cost',
#             'objects': http.request.env['picking_cost.picking_cost'].search([]),
#         })

#     @http.route('/picking_cost/picking_cost/objects/<model("picking_cost.picking_cost"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('picking_cost.object', {
#             'object': obj
#         })
