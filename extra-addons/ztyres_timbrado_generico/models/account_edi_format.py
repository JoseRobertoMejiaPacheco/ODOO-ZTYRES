# -- coding: utf-8 --
from odoo import api, models, fields, tools, _
from odoo.exceptions import UserError
from lxml import etree
from base64 import b64decode

class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'
    
    def check_generic_rfc_in_edi(self, move_id):
        """
        Verifica si algún documento EDI está relacionado con un RFC genérico.
        También valida la consistencia de los valores en el campo 'generic_edi'.
        """

        # Buscar documentos EDI con archivos XML adjuntos
        edi_docs = move_id.mapped('edi_document_ids')
        
        for edi_document in edi_docs:
            rfc = self._get_rfc_from_xml(edi_document)
            if rfc == 'XAXX010101000':
                return True  # Retornar True si se encuentra un RFC genérico
            
        # Validar consistencia de valores en el campo 'generic_edi'
        return self._validate_generic_edi_values(move_id)

    def _is_generic_rfc_in_xml(self, edi_document):
        """
        Verifica si el archivo XML adjunto contiene un RFC genérico en el nodo 'Receptor'.
        """
        rfc = self._get_rfc_from_xml(edi_document)
        return rfc == 'XAXX010101000'
    
    def _get_rfc_from_xml(self, edi_document):
        """
        Retorna el valor del atributo 'Rfc' del nodo 'cfdi:Receptor' del archivo XML adjunto.
        Si no se encuentra, retorna None.
        """
        attachment = edi_document.sudo().attachment_id
        if attachment:
            try:
                # Parsear el contenido XML
                xml_content = attachment.with_context(bin_size=False).raw
                print(xml_content)
                tree = etree.fromstring(xml_content)
                
                # Buscar el nodo cfdi:Receptor y obtener el atributo 'Rfc'
                receptor_node = tree.find('.//cfdi:Receptor', namespaces={'cfdi': 'http://www.sat.gob.mx/cfd/4'})
                if receptor_node is not None:
                    return receptor_node.get('Rfc')  # Retorna el valor del atributo 'Rfc'
            except Exception as e:
                # Manejo de errores al procesar el XML
                print(f"Error procesando el archivo XML {edi_document.name}: {e}")
        return None

    def _validate_generic_edi_values(self, move_id):
        """
        Valida la consistencia de los valores en el campo 'generic_edi' de la factura.
        """
        generic_edi_values = move_id.mapped('generic_edi')
        if all(value == generic_edi_values[0] for value in generic_edi_values):
            return generic_edi_values[0]  # Retornar valor si todos son iguales
        else:
            # Lanzar un error si hay inconsistencias en los valores
            raise UserError('No se puede combinar RFC GENÉRICO con RFC de contribuyente.')
    
    def _l10n_mx_edi_export_payment_cfdi(self, move):
        ''' Create the CFDI attachment for the journal entry passed as parameter being a payment used to pay some
        invoices.
        
        :param move:    An account.move record.
        :return:        A dictionary with one of the following key:
        * cfdi_str:     A string of the unsigned cfdi of the invoice.
        * error:        An error if the cfdi was not successfully generated.
        '''
        cfdi_values = self._l10n_mx_edi_get_payment_cfdi_values(move)
        if self.check_generic_rfc_in_edi(move.payment_id.reconciled_invoice_ids):            
            cfdi_values.update(
                {
                    'customer_rfc': 'XAXX010101000',
                    'fiscal_regime': '616',
                    'customer': move.partner_id.browse(8625),
                    'customer_name': 'PÚBLICO EN GENERAL'
                }
            )
        qweb_template = self._l10n_mx_edi_get_payment_template()
        cfdi = self.env['ir.qweb']._render(qweb_template, cfdi_values)
        decoded_cfdi_values = move._l10n_mx_edi_decode_cfdi(cfdi_data=cfdi)            
        cfdi_cadena_crypted = cfdi_values['certificate'].sudo()._get_encrypted_cadena(decoded_cfdi_values['cadena'])
        decoded_cfdi_values['cfdi_node'].attrib['Sello'] = cfdi_cadena_crypted
        
        return {
            'cfdi_str': etree.tostring(decoded_cfdi_values['cfdi_node'], pretty_print=True, xml_declaration=True, encoding='UTF-8'),
        }

    def _l10n_mx_edi_export_invoice_cfdi(self, invoice):
        ''' Create the CFDI attachment for the invoice passed as parameter.

        :param move:    An account.move record.
        :return:        A dictionary with one of the following key:
        * cfdi_str:     A string of the unsigned cfdi of the invoice.
        * error:        An error if the cfdi was not successfuly generated.
        '''
        # == CFDI values ==
        cfdi_values = self._l10n_mx_edi_get_invoice_cfdi_values(invoice)
        invoice_origin = invoice.reversed_entry_id or invoice
        if self.check_generic_rfc_in_edi(invoice_origin):
            cfdi_values.update(
                {
                    'customer_rfc': 'XAXX010101000',
                    'fiscal_regime': '616',
                    'customer': invoice.partner_id.browse(8625),
                    'customer_name': 'PÚBLICO EN GENERAL'                    
                }
            )
        qweb_template, xsd_attachment_name = self._l10n_mx_edi_get_invoice_templates()
        # == Generate the CFDI ==
        cfdi = self.env['ir.qweb']._render(qweb_template, cfdi_values)
        decoded_cfdi_values = invoice._l10n_mx_edi_decode_cfdi(cfdi_data=cfdi)
        cfdi_cadena_crypted = cfdi_values['certificate'].sudo()._get_encrypted_cadena(decoded_cfdi_values['cadena'])
        decoded_cfdi_values['cfdi_node'].attrib['Sello'] = cfdi_cadena_crypted
        res = {
            'cfdi_str': etree.tostring(decoded_cfdi_values['cfdi_node'], pretty_print=True, xml_declaration=True, encoding='UTF-8'),
        }
        try:
            self.env['ir.attachment'].l10n_mx_edi_validate_xml_from_attachment(decoded_cfdi_values['cfdi_node'], xsd_attachment_name)
        except UserError as error:
            res['errors'] = str(error).split('\\n')
            
        return res