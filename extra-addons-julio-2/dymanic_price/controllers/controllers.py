# -*- coding: utf-8 -*-
# from odoo import http


# class DymanicPrice(http.Controller):
#     @http.route('/dymanic_price/dymanic_price', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/dymanic_price/dymanic_price/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('dymanic_price.listing', {
#             'root': '/dymanic_price/dymanic_price',
#             'objects': http.request.env['dymanic_price.dymanic_price'].search([]),
#         })

#     @http.route('/dymanic_price/dymanic_price/objects/<model("dymanic_price.dymanic_price"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('dymanic_price.object', {
#             'object': obj
#         })
