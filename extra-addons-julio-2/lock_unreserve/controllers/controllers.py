# -*- coding: utf-8 -*-
# from odoo import http


# class LockUnreserve(http.Controller):
#     @http.route('/lock_unreserve/lock_unreserve', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/lock_unreserve/lock_unreserve/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('lock_unreserve.listing', {
#             'root': '/lock_unreserve/lock_unreserve',
#             'objects': http.request.env['lock_unreserve.lock_unreserve'].search([]),
#         })

#     @http.route('/lock_unreserve/lock_unreserve/objects/<model("lock_unreserve.lock_unreserve"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('lock_unreserve.object', {
#             'object': obj
#         })
