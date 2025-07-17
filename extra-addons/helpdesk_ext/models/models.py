# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class helpdesk(models.Model):
    _inherit = 'helpdesk.ticket'
    
    @api.constrains('stage_id')
    def _check_creator_close(self):
        for rec in self:
            if rec.stage_id.id  == 4 and rec.create_uid != self.env.user:
                raise ValidationError("Solo el creador del ticket lo puede cerrar.")