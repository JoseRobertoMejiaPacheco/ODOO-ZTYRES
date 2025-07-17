# -*- coding: utf-8 -*-
# from odoo import http


# class ZtyresPromo(http.Controller):
#     @http.route('/ztyres_promo/ztyres_promo', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ztyres_promo/ztyres_promo/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ztyres_promo.listing', {
#             'root': '/ztyres_promo/ztyres_promo',
#             'objects': http.request.env['ztyres_promo.ztyres_promo'].search([]),
#         })

#     @http.route('/ztyres_promo/ztyres_promo/objects/<model("ztyres_promo.ztyres_promo"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ztyres_promo.object', {
#             'object': obj
#         })
