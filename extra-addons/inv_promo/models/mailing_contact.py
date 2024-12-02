# -*- coding: utf-8 -*-
from odoo import models, fields, api

class MailingContact(models.Model):
    _inherit = 'mailing.contact'
    partner_id = fields.Many2one('res.partner', string='Cliente')
    
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        for contact in self:
            contact.name = contact.partner_id.name
            contact.email = contact.partner_id.email
    