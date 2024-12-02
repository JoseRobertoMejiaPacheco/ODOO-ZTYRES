#-*- coding: utf-8 -*-

from odoo import models, fields, api


class mass_mailing_ext(models.Model):
    _name = 'mailing.lists'
    _description = 'mass_mailing_ext.mass_mailing_ext'
    date = fields.Datetime(string='Fecha')
    partner_id = fields.Many2many('res.partner', string='Cliente')
    attachment_id = fields.Many2one('ir.attachment', string='Archivo Adjunto')
    attachment_ids = fields.Many2many(
        'ir.attachment', 
        'mass_list_mailing_attachment_rel',  # Nombre de la tabla relacional
        'mailing_lists_id',               # Campo que referencia a odoo_vs_sat.reconcilie
        'attachment_id',               # Campo que referencia a ir.attachment
        string='Archivos Adjuntos',
        required=False,
    )


class mailing_list(models.Model):
    _inherit = 'mailing.list'
    list_date = fields.Date(string='Fecha de Lista')
    def generate_list(self):
        pass
    
    
