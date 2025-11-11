# -*- coding: utf-8 -*-
from odoo import models, fields, api,_
from odoo.exceptions import ValidationError, UserError

class AccountMove(models.Model):
    _inherit = 'account.payment'

    solicitar_cancelacion = fields.Boolean(string="Solicitar Cancelación")
    firma_calidad = fields.Boolean(string="Firma Calidad")
    firma_finanzas = fields.Boolean(string="Firma Finanzas")
    
    # campos auxiliares para controlar permisos
    can_edit_solicitar_cancelacion = fields.Boolean(
        compute="_compute_permisos", store=False
    )
    can_edit_firma_calidad = fields.Boolean(
        compute="_compute_permisos", store=False
    )
    can_edit_firma_finanzas = fields.Boolean(
        compute="_compute_permisos", store=False
    )
    
    can_cancel_edi = fields.Boolean(
        compute="_compute_permisos_cancel",
        store=False
    )
    
    show_action_draft = fields.Boolean(
        compute="_compute_action_draft",
        string="Aprobar Cancelación",
        store=True
    )

    @api.depends('create_uid')
    def _compute_permisos(self):
        for rec in self:
            user = rec.env.user
            rec.can_edit_solicitar_cancelacion = user.has_group('ztyres.group_solicitud')
            rec.can_edit_firma_calidad = user.has_group('ztyres.group_calidad')
            rec.can_edit_firma_finanzas = user.has_group('ztyres.group_finanzas')
            
    @api.depends('show_action_draft')
    def _compute_permisos_cancel(self):
        for rec in self:
            rec.can_cancel_edi = rec.show_action_draft and rec.env.user.has_group('ztyres.group_cancel_edi')

    @api.depends('firma_calidad', 'firma_finanzas', 'state')
    def _compute_action_draft(self):
        for rec in self:
            rec.show_action_draft = (
                rec.firma_calidad and 
                rec.firma_finanzas and 
                rec.state in ('posted')
            )
            
    def copy(self, default=None):
        default = dict(default or {})
        # Reiniciamos los checks
        default.update({
            'solicitar_cancelacion': False,
            'firma_calidad': False,
            'firma_finanzas': False,
        })
        return super().copy(default)
            
    def action_draft(self):
        res = super().action_draft()
        for rec in self:
            rec.solicitar_cancelacion = False
            rec.firma_calidad = False
            rec.firma_finanzas = False
        return res