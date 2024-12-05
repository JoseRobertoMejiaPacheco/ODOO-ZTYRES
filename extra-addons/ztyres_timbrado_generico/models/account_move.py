# -- coding: utf-8 --
from odoo import models, fields, api

class account_move(models.Model):
    _inherit = 'account.move'
    generic_edi = fields.Boolean("Timbrado genérico")
    
    promo_timbrada = fields.Selection(
        string='Estado De Timbrado de Promoción',
        selection=[('draft', 'No Timbrado'), ('done', 'Timbrado')],default=False
    )
    
    def action_post(self):
        res = super().action_post()
        if self.move_type:
            if self.move_type in ('out_invoice') and not any(self.line_ids.sale_line_ids.mapped('order_id').mapped('is_expo')):
                self.sudo().discount_increase()
                action = self.with_context(discard_logo_check=True).action_invoice_sent()
                action_context = action['context']
                invoice_send_wizard = self.env['account.invoice.send'].with_context(
                    action_context,
                    active_ids=self.ids
                ).create({'is_print': False})
                invoice_send_wizard.template_id.auto_delete = False
                invoice_send_wizard.send_and_print_action()            
                # Process credit note promotion
                if self.credit_note_promo:
                    action_nc = self.credit_note_promo.with_context(discard_logo_check=True).action_invoice_sent()
                    ctx = action_nc['context']
                    invoice_send_wizard_nc = self.env['account.invoice.send'].with_context(
                        ctx,
                        active_ids=self.credit_note_promo.ids
                    ).create({'is_print': False})
                    invoice_send_wizard_nc.template_id.auto_delete = False
                    invoice_send_wizard_nc.send_and_print_action()                 
        return res
    
    def action_process_edi_web_services(self, with_commit=True):
        if not self.l10n_mx_edi_cfdi_uuid:
            # Filtrar documentos que necesitan ser procesados
            docs = self.edi_document_ids.filtered(lambda d: d.state in ('to_send', 'to_cancel') and d.blocking_level != 'error')
            
            if docs:
                docs._process_documents_web_services(with_commit=with_commit)
            
            # Procesar notas de crédito promocionales si existen
            if self.l10n_mx_edi_cfdi_uuid and self.credit_note_promo:
                if self.generic_edi:
                    self.credit_note_promo#._l10n_mx_edi_export_invoice_cfdi()
                
                self.credit_note_promo.l10n_mx_edi_origin = f'01|{self.l10n_mx_edi_cfdi_uuid or ""}'
                docs_nc = self.credit_note_promo.edi_document_ids.filtered(lambda d: d.state in ('to_send', 'to_cancel') and d.blocking_level != 'error')
                
                if docs_nc:
                    docs_nc._process_documents_web_services(with_commit=with_commit)
                
                # Actualizar estado de la nota de crédito promocional
                if self.credit_note_promo.l10n_mx_edi_cfdi_uuid:
                    self.promo_timbrada = 'done'
                else:
                    self.promo_timbrada = 'draft'
                    if self.move_type != 'out_invoice':
                        self.promo_timbrada = False
        else:
            docs = self.edi_document_ids.filtered(lambda d: d.state in ('to_cancel') and d.blocking_level != 'error')
            if docs:
                docs._process_documents_web_services(with_commit=with_commit)                        
        
# -- coding: utf-8 --
from odoo import api, models, fields, tools, _
from odoo.exceptions import UserError
from lxml import etree

class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def check_generic_rfc_in_edi(self,move_id):
        """
        Verifica si alguno de los XML en edi_document_ids contiene el nodo <cfdi:Receptor> 
        con el atributo Rfc="XAXX010101000".

        Args:
            move_id (int): ID del registro account.move.

        Returns:
            bool: True si se encuentra, False en caso contrario.
        """
        # Obtener el registro de account.move
        
        # Iterar sobre los edi_document_ids
        for edi_document in move_id.edi_document_ids:
            if edi_document.attachment_id:  # Filtrar solo archivos XML
                xml_content = edi_document.attachment_id.raw
                try:
                    # Parsear el contenido XML
                    tree = etree.fromstring(xml_content)
                    
                    # Buscar el nodo cfdi:Receptor
                    receptor_node = tree.find('.//cfdi:Receptor', namespaces={'cfdi': 'http://www.sat.gob.mx/cfd/4'})
                    if receptor_node is not None:
                        rfc = receptor_node.get('Rfc')  # Obtener el atributo Rfc
                        if rfc == 'XAXX010101000':
                            return True  # Retornar True si se encuentra
                except Exception as e:
                    # Puedes registrar el error si lo consideras necesario
                    print(f"Error procesando el archivo XML {edi_document.name}: {e}")
        
        return move_id.generic_edi  # Retornar False si no se encontró
    
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
        if self.check_generic_rfc_in_edi(invoice.reversed_entry_id or invoice):
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

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_process_edi_web_services(self):
        res = self.move_id.action_process_edi_web_services()
        self.action_send_payment_receipt()
        return res

    def action_retry_edi_documents_error(self):
        self.ensure_one()
        res = self.move_id.action_retry_edi_documents_error()
        self.action_send_payment_receipt()
        return res
    
    def action_send_payment_receipt(self):
        """
        Envía el recibo de pago automáticamente por correo electrónico sin abrir el asistente.
        """
        self.ensure_one()  # Asegurarse de que solo se envíe un recibo a la vez

        # Obtener la plantilla de correo
        template = self.env.ref('account.mail_template_data_payment_receipt')

        # Componer y enviar el mensaje de correo
        if template:
            template.with_context(
                default_model='account.payment',
                default_res_id=self.id,
                default_partner_ids=[self.partner_id.id],
            ).send_mail(self.id, force_send=False)