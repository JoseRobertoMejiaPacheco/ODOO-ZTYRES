# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import content_disposition, request

XLSX_MIMETYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

MODELS = {
    'assignment': 'ztyres.it.assignment',
    'equipment': 'ztyres.it.equipment',
}


class ItResguardoController(http.Controller):

    @http.route(
        '/ztyres_it_assets/resguardo/<string:kind>/<int:record_id>',
        type='http', auth='user')
    def download_resguardo(self, kind, record_id, **kwargs):
        model = MODELS.get(kind)
        if not model:
            return request.not_found()
        record = request.env[model].browse(record_id).exists()
        if not record:
            return request.not_found()
        # Respeta permisos del usuario (lanza AccessError si no puede leer)
        record.check_access_rights('read')
        record.check_access_rule('read')

        filename, content = request.env['ztyres.it.resguardo'].build_xlsx(record)
        return request.make_response(content, headers=[
            ('Content-Type', XLSX_MIMETYPE),
            ('Content-Disposition', content_disposition(filename)),
            ('Content-Length', len(content)),
        ])
