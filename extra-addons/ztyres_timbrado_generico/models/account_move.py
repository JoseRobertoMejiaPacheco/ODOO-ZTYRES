# -- coding: utf-8 --
from odoo import models, fields, api

class account_move(models.Model):
    _inherit = 'account.move'
    generic_edi = fields.Boolean("Timbrado genérico")
    
    promo_timbrada = fields.Selection(
        string='Estado De Timbrado de Promoción',
        selection=[('draft', 'No Timbrado'), ('done', 'Timbrado')],default=False
    )
    
    edi_vat_receptor = fields.Char(compute='_compute_edi_vat_receptor', string='RFC Receptor')
    #@api.depends('')
    def _compute_edi_vat_receptor(self):
        for move in self:
            move.edi_vat_receptor = ''
            for document in  move.edi_document_ids:
                self.edi_vat_receptor = document.edi_format_id._get_rfc_from_xml(document) or 'SIN XML ADJUNTO'
                print(self.edi_vat_receptor)
    
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
                if self.edi_vat_receptor == 'XAXX010101000':
                    self.credit_note_promo.update({"l10n_mx_edi_usage": "S01"})                                
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