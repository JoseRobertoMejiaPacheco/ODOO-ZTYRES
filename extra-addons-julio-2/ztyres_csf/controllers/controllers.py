# -*- coding: utf-8 -*-
# from odoo import http


# class ZtyresCsf(http.Controller):
#     @http.route('/ztyres_csf/ztyres_csf', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ztyres_csf/ztyres_csf/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ztyres_csf.listing', {
#             'root': '/ztyres_csf/ztyres_csf',
#             'objects': http.request.env['ztyres_csf.ztyres_csf'].search([]),
#         })

#     @http.route('/ztyres_csf/ztyres_csf/objects/<model("ztyres_csf.ztyres_csf"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ztyres_csf.object', {
#             'object': obj
#         })
