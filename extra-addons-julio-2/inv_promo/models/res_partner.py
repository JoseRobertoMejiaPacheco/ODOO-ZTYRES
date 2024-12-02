# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    def _get_discount_values(self, discount_type,profile=False):
        descuentos = []
        if self:
            for record in self:
                if record.financial_profile.name and discount_type == 'financiero':
                    for line in record.financial_profile.line_ids:
                        descuentos.append((line.upper_limit, line.discount)) 
                elif record.logistic_profile and discount_type == 'logistico':
                    for line in record.logistic_profile.line_ids:
                        descuentos.append((line.upper_limit, line.discount)) 
                elif record.volume_profile and discount_type == 'volumen':
                    record.append((line.percent or 0))                           
        else:                    
            if profile and discount_type == 'financiero':
                for line in profile.line_ids:
                    descuentos.append((line.upper_limit, line.discount)) 
            elif profile and discount_type == 'logistico':
                for line in profile.line_ids:
                    descuentos.append((line.upper_limit, line.discount)) 
            elif profile and discount_type == 'volumen':
                for line in profile:
                    descuentos.append((line.percent))                                                                         
        return descuentos

    def get_row_values_financiero(self,profile=False):
        return self._get_discount_values('financiero',profile)

    def get_row_values_logistico(self,profile=False):
        return self._get_discount_values('logistico',profile)
    
    def get_row_values_volumen(self,profile=False):
        return self._get_discount_values('volumen',profile)