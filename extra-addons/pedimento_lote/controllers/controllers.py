# -*- coding: utf-8 -*-
# from odoo import http


# class PedimentoLote(http.Controller):
#     @http.route('/pedimento_lote/pedimento_lote', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/pedimento_lote/pedimento_lote/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('pedimento_lote.listing', {
#             'root': '/pedimento_lote/pedimento_lote',
#             'objects': http.request.env['pedimento_lote.pedimento_lote'].search([]),
#         })

#     @http.route('/pedimento_lote/pedimento_lote/objects/<model("pedimento_lote.pedimento_lote"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('pedimento_lote.object', {
#             'object': obj
#         })
