# -- coding: utf-8 --
from odoo import _, api, fields, models

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    edi_vat_receptor = fields.Char(
        string="RFC Receptor",
        related='move_id.edi_vat_receptor'
    )
    
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