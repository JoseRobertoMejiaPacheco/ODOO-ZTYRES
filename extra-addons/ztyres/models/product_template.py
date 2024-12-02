# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'


    
    def update_name_ztyres(self):
        for record in self:            
            name = "%s %s%s%s %s %s"%(self.x_studio_medida_1 or "",self.x_studio_cara or "",self.x_studio_capas or "",self.x_studio_ndice_de_velocidad or "",self.x_studio_marca or "",self.x_studio_modelo_1 or "")
            record.name = name
            record.display_name = name
        

    