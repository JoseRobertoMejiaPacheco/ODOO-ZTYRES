# -*- coding: utf-8 -*-
# from odoo import http


# class DiscountProfiles(http.Controller):
#     @http.route('/discount_profiles/discount_profiles', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/discount_profiles/discount_profiles/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('discount_profiles.listing', {
#             'root': '/discount_profiles/discount_profiles',
#             'objects': http.request.env['discount_profiles.discount_profiles'].search([]),
#         })

#     @http.route('/discount_profiles/discount_profiles/objects/<model("discount_profiles.discount_profiles"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('discount_profiles.object', {
#             'object': obj
#         })
