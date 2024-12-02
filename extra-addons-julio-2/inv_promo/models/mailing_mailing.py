# -*- coding: utf-8 -*-
import threading
from odoo import models, fields, api
import ast
import base64
import re

from odoo import _, api, fields, models, tools, Command
from odoo.exceptions import UserError
from odoo.osv import expression

class MailComposer(models.TransientModel):
    """ Generic message composition wizard. You may inherit from this wizard
        at model and view levels to provide specific features.

        The behavior of the wizard depends on the composition_mode field:
        - 'comment': post on a record. The wizard is pre-populated via ``get_record_data``
        - 'mass_mail': wizard in mass mailing mode where the mail details can
            contain template placeholders that will be merged with actual data
            before being sent to each recipient.
    """
    _inherit = 'mail.compose.message'
    def get_mail_values(self, res_ids):
        """Generate the values that will be used by send_mail to create mail_messages
        or mail_mails. """
        self.ensure_one()
        results = dict.fromkeys(res_ids, False)
        rendered_values = {}
        mass_mail_mode = self.composition_mode == 'mass_mail'
        
        list_attachment =  [(4, attachment.id) for attachment in self.attachment_ids]
        lista_de_precios = self.env['inv_promo.lista_precios_wizard']
        
        
        # render all template-based value at once
        if mass_mail_mode and self.model:
            rendered_values = self.render_message(res_ids)
        # compute alias-based reply-to in batch
        reply_to_value = dict.fromkeys(res_ids, None)
        if mass_mail_mode and not self.reply_to_force_new:
            records = self.env[self.model].browse(res_ids)
            reply_to_value = records._notify_get_reply_to(default=False)
            # when having no specific reply-to, fetch rendered email_from value
            for res_id, reply_to in reply_to_value.items():
                if not reply_to:
                    reply_to_value[res_id] = rendered_values.get(res_id, {}).get('email_from', False)
        x = 1
        for res_id in res_ids:
            
            list_attachment =  [attach.id for attach in self.attachment_ids]
            
            # static wizard (mail.message) values
            mail_values = {
                'subject': self.subject,
                'body': self.body or '',
                'parent_id': self.parent_id and self.parent_id.id,
                'partner_ids': [partner.id for partner in self.partner_ids],
                'attachment_ids': list_attachment,
                'author_id': self.author_id.id,
                'email_from': self.email_from,
                'record_name': self.record_name,
                'reply_to_force_new': self.reply_to_force_new,
                'mail_server_id': self.mail_server_id.id,
                'mail_activity_type_id': self.mail_activity_type_id.id,
                'message_type': 'email' if mass_mail_mode else self.message_type,
            }

            # mass mailing: rendering override wizard static values
            if mass_mail_mode and self.model:
                record = self.env[self.model].browse(res_id)
                
                if self.mass_mailing_id.send_list_price:
                    if record.partner_id:
                        price_list_id = lista_de_precios.create_attachment(self.id,record.partner_id)
                        if price_list_id:
                            at_id = price_list_id.id            
                            list_attachment.append(at_id)
                            mail_values.update({'attachment_ids':list_attachment})
                
                
                msggg = '%s  %s  %s'%(str(list_attachment),str(self.subject),str(x))
                print(msggg)
                mail_values['headers'] = repr(record._notify_by_email_get_headers())
                # keep a copy unless specifically requested, reset record name (avoid browsing records)
                mail_values.update(is_notification=not self.auto_delete_message, model=self.model, res_id=res_id, record_name=False)
                # auto deletion of mail_mail
                if self.auto_delete or self.template_id.auto_delete:
                    mail_values['auto_delete'] = True
                # rendered values using template
                email_dict = rendered_values[res_id]
                mail_values['partner_ids'] += email_dict.pop('partner_ids', [])
                mail_values.update(email_dict)
                if not self.reply_to_force_new:
                    mail_values.pop('reply_to')
                    if reply_to_value.get(res_id):
                        mail_values['reply_to'] = reply_to_value[res_id]
                if self.reply_to_force_new and not mail_values.get('reply_to'):
                    mail_values['reply_to'] = mail_values['email_from']
                # mail_mail values: body -> body_html, partner_ids -> recipient_ids
                mail_values['body_html'] = mail_values.get('body', '')
                mail_values['recipient_ids'] = [Command.link(id) for id in mail_values.pop('partner_ids', [])]
                # process attachments: should not be encoded before being processed by message_post / mail_mail create
                mail_values['attachments'] = [(name, base64.b64decode(enc_cont)) for name, enc_cont in email_dict.pop('attachments', list())]
                attachment_ids = []
                for attach_id in mail_values.pop('attachment_ids'):
                    new_attach_id = self.env['ir.attachment'].browse(attach_id).copy({'res_model': self._name, 'res_id': self.id})
                    attachment_ids.append(new_attach_id.id)
                attachment_ids.reverse()
                mail_values['attachment_ids'] = self.env['mail.thread'].with_context(attached_to=record)._message_post_process_attachments(
                    mail_values.pop('attachments', []),
                    attachment_ids,
                    {'model': 'mail.message', 'res_id': 0}
                )['attachment_ids']

            results[res_id] = mail_values
            x = x +1

        results = self._process_state(results)
        return results    
    
class MailingMailing(models.Model):
    _inherit = 'mailing.mailing'
    send_list_price = fields.Boolean('Enviar lista de Precios?',default=False)

    def action_send_mail(self, res_ids=None):
        author_id = self.env.user.partner_id.id

        # If no recipient is passed, we don't want to use the recipients of the first
        # mailing for all the others
        initial_res_ids = res_ids
        for mailing in self:
            if not initial_res_ids:
                res_ids = mailing._get_remaining_recipients()
            if not res_ids:
                raise UserError(_('There are no recipients selected.'))

            composer_values = {
                'author_id': author_id,
                'attachment_ids': [(4, attachment.id) for attachment in mailing.attachment_ids],
                'body': mailing._prepend_preview(mailing.body_html, mailing.preview),
                'subject': mailing.subject,
                'model': mailing.mailing_model_real,
                'email_from': mailing.email_from,
                'record_name': False,
                'composition_mode': 'mass_mail',
                'mass_mailing_id': mailing.id,
                'mailing_list_ids': [(4, l.id) for l in mailing.contact_list_ids],
                'reply_to_force_new': mailing.reply_to_mode == 'new',
                'template_id': None,
                'mail_server_id': mailing.mail_server_id.id,
            }
            if mailing.reply_to_mode == 'new':
                composer_values['reply_to'] = mailing.reply_to

            composer = self.env['mail.compose.message'].with_context(active_ids=res_ids).create(composer_values)
            extra_context = mailing._get_mass_mailing_context()
            composer = composer.with_context(active_ids=res_ids, **extra_context)
            #auto-commit except in testing mode
            auto_commit = not getattr(threading.current_thread(), 'testing', False)
            composer._action_send_mail(auto_commit=auto_commit)
            mailing.write({
                'state': 'done',
                'sent_date': fields.Datetime.now(),
                # send the KPI mail only if it's the first sending
                'kpi_mail_required': not mailing.sent_date,
            })
        return True

