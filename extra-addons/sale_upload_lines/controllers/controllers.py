# -*- coding: utf-8 -*-
# from odoo import http


# class SaleUploadLines(http.Controller):
#     @http.route('/sale_upload_lines/sale_upload_lines', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/sale_upload_lines/sale_upload_lines/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('sale_upload_lines.listing', {
#             'root': '/sale_upload_lines/sale_upload_lines',
#             'objects': http.request.env['sale_upload_lines.sale_upload_lines'].search([]),
#         })

#     @http.route('/sale_upload_lines/sale_upload_lines/objects/<model("sale_upload_lines.sale_upload_lines"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sale_upload_lines.object', {
#             'object': obj
#         })
