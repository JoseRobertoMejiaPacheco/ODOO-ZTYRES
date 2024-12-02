# -*- coding: utf-8 -*-
# from odoo import http


# class ZtyresTicket(http.Controller):
#     @http.route('/ztyres_ticket/ztyres_ticket', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ztyres_ticket/ztyres_ticket/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ztyres_ticket.listing', {
#             'root': '/ztyres_ticket/ztyres_ticket',
#             'objects': http.request.env['ztyres_ticket.ztyres_ticket'].search([]),
#         })

#     @http.route('/ztyres_ticket/ztyres_ticket/objects/<model("ztyres_ticket.ztyres_ticket"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ztyres_ticket.object', {
#             'object': obj
#         })
