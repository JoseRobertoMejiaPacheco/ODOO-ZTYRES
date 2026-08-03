# -*- coding: utf-8 -*-
"""
Utilidades para generar un ZIP con los XMLs (CFDI) de un conjunto de
facturas, y publicarlo como adjunto descargable.

Este módulo NO define modelos de Odoo: son funciones auxiliares puras
(reciben lo que necesitan como parámetros) para que la lógica de
construcción del ZIP pueda reutilizarse y probarse por separado de
`ztyres_promo.notas_credito`.

Se extrae 1:1 desde el método `download_zip_xmls` original: mismo
comportamiento, mismos mensajes, mismos logs.
"""
import base64
import io
import logging
import zipfile

from odoo import fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def get_edi_documents_with_attachment(env, invoice_ids):
    """Busca los documentos EDI (con adjunto) asociados a las facturas dadas."""
    return env['account.edi.document'].sudo().search([
        ('move_id', 'in', invoice_ids),
        ('attachment_id', '!=', False),
    ])


def ensure_all_invoices_have_xml(valid_invoices, edi_documents):
    """Valida que exista un XML por cada factura válida.

    Lanza UserError con el mismo mensaje detallado del método original
    si faltan XMLs.
    """
    invoices_with_xml = edi_documents.mapped('move_id')
    missing_invoices = valid_invoices - invoices_with_xml
    if missing_invoices:
        missing_names = "\n• ".join(missing_invoices.mapped('name'))
        raise UserError(
            "¡Validación fallida!\n\n"
            f"Facturas válidas encontradas: {len(valid_invoices)}\n"
            f"Archivos XML encontrados: {len(edi_documents)}\n\n"
            "Las siguientes facturas no tienen XML asociado:\n"
            f"• {missing_names}\n\n"
            "Por favor genere los XML faltantes antes de continuar."
        )


def _write_xml_entries(zip_file, edi_documents):
    """Escribe cada XML dentro del ZIP ya abierto. Misma validación por
    documento que el método original."""
    for doc in edi_documents:
        try:
            xml_content = base64.b64decode(doc.attachment_id.sudo().datas)
            filename = f"{doc.move_id.name.replace('/', '_')}.xml"
            zip_file.writestr(filename, xml_content)
            _logger.debug(f"Archivo añadido: {filename}")
        except Exception as e:
            _logger.error(f"Error procesando XML para {doc.move_id.name}: {str(e)}")
            raise UserError(
                f"Error al procesar el XML de la factura {doc.move_id.name}:\n{str(e)}"
            ) from e


def create_zip_attachment(env, zip_data, name, res_model, res_id):
    """Crea el ir.attachment público con el ZIP generado."""
    return env['ir.attachment'].sudo().create({
        'name': name,
        'datas': base64.b64encode(zip_data),
        'type': 'binary',
        'public': True,
        'res_model': res_model,
        'res_id': res_id,
    })


def build_download_action(attachment):
    """Arma la acción de descarga del adjunto."""
    return {
        'type': 'ir.actions.act_url',
        'url': f'/web/content/{attachment.id}?download=true',
        'target': 'self',
    }


def generate_xml_zip_attachment(env, valid_invoices, move_type, res_model, res_id):
    """Orquesta el flujo completo (equivalente al cuerpo de
    `download_zip_xmls` original): valida, construye el ZIP, crea el
    adjunto y retorna la acción de descarga.

    Mantiene exactamente el mismo manejo de errores que el original:
    cualquier excepción producida al construir el ZIP o el adjunto
    (incluyendo el UserError levantado por un XML puntual) se
    re-envuelve como un único UserError genérico de "Error al generar
    el archivo ZIP".
    """
    _logger.info(f"Iniciando generación de ZIP para {len(valid_invoices)} facturas")

    edi_documents = get_edi_documents_with_attachment(env, valid_invoices.ids)
    ensure_all_invoices_have_xml(valid_invoices, edi_documents)

    # Crear ZIP en memoria
    zip_buffer = io.BytesIO()
    try:
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            _write_xml_entries(zip_file, edi_documents)

        zip_buffer.seek(0)
        zip_data = zip_buffer.read()

        # Crear registro de attachment
        attachment = create_zip_attachment(
            env,
            zip_data,
            name=f"{move_type}_XML_{fields.Date.today()}.zip",
            res_model=res_model,
            res_id=res_id,
        )

        _logger.info(f"ZIP generado correctamente con {len(edi_documents)} archivos")

        # Retornar acción de descarga
        return build_download_action(attachment)

    except Exception as e:
        _logger.error(f"Error al generar ZIP: {str(e)}")
        raise UserError(f"Error al generar el archivo ZIP:\n{str(e)}")
    finally:
        zip_buffer.close()
