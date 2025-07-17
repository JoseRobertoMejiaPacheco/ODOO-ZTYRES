# -*- coding: utf-8 -*-
# from odoo import http


# class ZtyresPromoElige(http.Controller):
#     @http.route('/ztyres_promo_elige/ztyres_promo_elige', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ztyres_promo_elige/ztyres_promo_elige/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ztyres_promo_elige.listing', {
#             'root': '/ztyres_promo_elige/ztyres_promo_elige',
#             'objects': http.request.env['ztyres_promo_elige.ztyres_promo_elige'].search([]),
#         })

#     @http.route('/ztyres_promo_elige/ztyres_promo_elige/objects/<model("ztyres_promo_elige.ztyres_promo_elige"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ztyres_promo_elige.object', {
#             'object': obj
#         })
