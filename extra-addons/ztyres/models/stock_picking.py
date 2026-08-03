# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo import models,fields

class StockPicking(models.Model):
    _inherit = ['stock.picking']

    def l10n_mx_edi_action_send_delivery_guide(self):
        
        self.move_ids._cal_move_weight()

        # Ejecutar método original
        return super().l10n_mx_edi_action_send_delivery_guide()

    def fix_weigth(self):
        pass

    def action_cancel(self):
        # if self.state_sale_id:
        #     self.state_sale_id = 'cancel'
        result = super(StockPicking, self).action_cancel()
        return result
    
    def separation_status_done(self):
        for rec in self:
            rec.separation_status='done'

    def separation_status_draft(self):
        for rec in self:
            rec.separation_status='draft'
    
    def button_validate(self):
        self.scheduled_date = fields.Datetime.now()            
        return super(StockPicking, self).button_validate()