# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request, content_disposition
import base64
import os, os.path
import csv
from os import listdir
import sys

class Download_xls(http.Controller):
    
    @http.route('/web/binary/download_document', type='http', auth="public")
    def download_document(self,model,id, **kw):

        Model = request.env[model]
        res = Model.browse(int(id)).sudo()

        if res.sample_option == 'xls':
            invoice_xls = request.env['ir.attachment'].sudo().search([('name','=','import_lines.xls')])
            filecontent = invoice_xls.datas
            filename = 'import_lines.xls'
            filecontent = base64.b64decode(filecontent)

        elif res.sample_option == 'csv':
            invoice_xls = request.env['ir.attachment'].sudo().search([('name','=','import_lines.csv')])
            filecontent = invoice_xls.datas
            filename = 'Import Lines.csv'
            filecontent = base64.b64decode(filecontent)
            

        return request.make_response(filecontent,
            [('Content-Type', 'application/octet-stream'),
            ('Content-Disposition', content_disposition(filename))])