# -*- coding: utf-8 -*-
from odoo import models, fields, api,_
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime
import pytz

class Sale(models.TransientModel):
    _name = 'ztyres.cancel_reason'
    cancel_reason = fields.Many2many(comodel_name='ztyres.sale_reason_cancel', string='Motivo de Cancelación')
    def action_cancel_reason(self):
        sale = self.env['sale.order'].browse(self._context['active_id'])
        if sale:
            user_tz = self.env.user.tz or pytz.utc
            local = pytz.timezone(user_tz)
            display_date_result = datetime.strftime(pytz.utc.localize(datetime.now()).astimezone(local),"%m/%d/%Y, %H:%M:%S") 
            sale.with_context(tracking_disable=True)._action_cancel()
            body = """<div class="alert alert-danger" role="alert">
  Cancelado en %s.<br><br/> Motivo de cancelación %s
</div>"""%(display_date_result,self.cancel_reason.name)
            sale.message_post(body=body)
            sale.sale_reason_cancel_id=[(6,0,self.cancel_reason.ids)]
            sale._action_cancel_delete_picking_ids()
            #sale.approve_state=False


