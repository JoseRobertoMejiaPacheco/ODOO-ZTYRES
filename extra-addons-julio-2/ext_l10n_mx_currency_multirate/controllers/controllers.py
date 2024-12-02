# -*- coding: utf-8 -*-
# from odoo import http


# class ExtL10nMxCurrencyMultirate(http.Controller):
#     @http.route('/ext_l10n_mx_currency_multirate/ext_l10n_mx_currency_multirate', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ext_l10n_mx_currency_multirate/ext_l10n_mx_currency_multirate/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ext_l10n_mx_currency_multirate.listing', {
#             'root': '/ext_l10n_mx_currency_multirate/ext_l10n_mx_currency_multirate',
#             'objects': http.request.env['ext_l10n_mx_currency_multirate.ext_l10n_mx_currency_multirate'].search([]),
#         })

#     @http.route('/ext_l10n_mx_currency_multirate/ext_l10n_mx_currency_multirate/objects/<model("ext_l10n_mx_currency_multirate.ext_l10n_mx_currency_multirate"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ext_l10n_mx_currency_multirate.object', {
#             'object': obj
#         })
