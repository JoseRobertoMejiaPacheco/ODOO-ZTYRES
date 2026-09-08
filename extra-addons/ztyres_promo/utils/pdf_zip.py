# -*- coding: utf-8 -*-
"""Generación de un ZIP con el PDF oficial de cada factura ganadora."""
import io
import logging
import zipfile

from odoo import fields
from odoo.exceptions import UserError

from .xml_zip import build_download_action, create_zip_attachment

_logger = logging.getLogger(__name__)


def _invoice_filename(invoice):
    """Nombre estable y seguro para el archivo dentro del ZIP."""
    number = (invoice.name or invoice.display_name or str(invoice.id))
    return '%s.pdf' % number.replace('/', '_').replace('\\', '_')


def _render_invoice_pdf(env, invoice):
    """Renderiza una factura con el reporte oficial configurado en Odoo."""
    pdf_content, _content_type = env['ir.actions.report'].sudo()._render_qweb_pdf(
        'account.account_invoices',
        res_ids=[invoice.id],
    )
    if not pdf_content:
        raise UserError(
            'Odoo no generó contenido PDF para la factura %s.'
            % invoice.display_name
        )
    return pdf_content


def generate_pdf_zip_attachment(env, valid_invoices, res_model, res_id):
    """Crea un ZIP con un PDF individual por cada factura válida."""
    _logger.info(
        'Iniciando generación de ZIP PDF para %s facturas válidas',
        len(valid_invoices),
    )
    zip_buffer = io.BytesIO()
    try:
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for invoice in valid_invoices.sorted(
                key=lambda move: (move.invoice_date or fields.Date.today(), move.id)
            ):
                try:
                    zip_file.writestr(
                        _invoice_filename(invoice),
                        _render_invoice_pdf(env, invoice),
                    )
                except Exception as error:
                    _logger.exception(
                        'Error generando el PDF de la factura %s',
                        invoice.display_name,
                    )
                    raise UserError(
                        'Error al generar el PDF de la factura %s:\n%s'
                        % (invoice.display_name, error)
                    ) from error

        attachment = create_zip_attachment(
            env,
            zip_buffer.getvalue(),
            name='Facturas_PDF_%s.zip' % fields.Date.today(),
            res_model=res_model,
            res_id=res_id,
        )
        _logger.info(
            'ZIP PDF generado correctamente con %s facturas',
            len(valid_invoices),
        )
        return build_download_action(attachment)
    except UserError:
        raise
    except Exception as error:
        _logger.exception('Error al generar el ZIP de facturas PDF')
        raise UserError(
            'Error al generar el archivo ZIP de facturas PDF:\n%s' % error
        ) from error
    finally:
        zip_buffer.close()
