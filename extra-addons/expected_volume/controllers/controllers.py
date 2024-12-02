# -*- coding: utf-8 -*-
# from odoo import http


# class ExpectedVolume(http.Controller):
#     @http.route('/expected_volume/expected_volume', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/expected_volume/expected_volume/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('expected_volume.listing', {
#             'root': '/expected_volume/expected_volume',
#             'objects': http.request.env['expected_volume.expected_volume'].search([]),
#         })

#     @http.route('/expected_volume/expected_volume/objects/<model("expected_volume.expected_volume"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('expected_volume.object', {
#             'object': obj
#         })
