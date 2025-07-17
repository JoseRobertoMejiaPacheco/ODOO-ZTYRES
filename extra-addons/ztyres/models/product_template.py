# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    def update_name_ztyres(self):
        for record in self:            
            name = "%s %s%s%s %s %s"%(record.tire_measure_id.name or "",record.face_id.name or "",record.layer_id.name or "",record.speed_id.name or "",record.brand_id.name or "",record.model_id.name or "")
            record.name = name
            record.display_name = name
        

    