# -*- coding: utf-8 -*-
"""
Extiende `ztyres_promo.notas_credito` (mismo _name/tabla, vía _inherit)
con la acción de descarga del ZIP de XMLs. La construcción del ZIP en
sí (armado del archivo, validaciones, adjunto) vive en
`ztyres_promo/utils/xml_zip.py`, separada del modelo.
"""
from odoo import models
from odoo.exceptions import UserError

from ..utils import pdf_zip, xml_zip


class ZtyresVolumenZip(models.Model):
    _inherit = 'ztyres_promo.notas_credito'

    def download_zip_xmls(self):
        """
        Descarga un ZIP con todos los XMLs de facturas válidas
        Valida que exista un XML por cada factura válida
        """
        # Obtener facturas válidas
        valid_invoices = self._get_valid_invoices(self._context.get('move_type'))
        if not valid_invoices:
            raise UserError("No se encontraron facturas válidas para procesar")

        return xml_zip.generate_xml_zip_attachment(
            self.env,
            valid_invoices,
            move_type=self._context.get('move_type'),
            res_model=self._name,
            res_id=self.id,
        )

    def download_zip_pdfs(self):
        """Descarga los PDF de las mismas facturas válidas del ZIP XML."""
        self.ensure_one()
        valid_invoices = self._get_valid_invoices('out_invoice')
        if not valid_invoices:
            raise UserError(
                'No se encontraron facturas con productos participantes '
                'que hayan ganado la promoción.'
            )

        return pdf_zip.generate_pdf_zip_attachment(
            self.env,
            valid_invoices,
            res_model=self._name,
            res_id=self.id,
        )
