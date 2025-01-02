# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT,DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime,timedelta
from odoo.tools.safe_eval import safe_eval
import calendar
from odoo.exceptions import  ValidationError


class PyDiscountLimits(models.Model):
    _name = 'py_discounts.limits'
    name = fields.Char(string='Tipo')
    limit_type = fields.Many2one(comodel_name='py_discounts.limit.type', string='Tipo de Límite')
    lower_limit = fields.Integer(string='De')
    upper_limit = fields.Integer(string='A')
    nc_amount = fields.Integer(string='Monto en NC')
    percent = fields.Integer(string='Porcentaje de Descuento')
    reward_name = fields.Integer(string='Premio')
    
class PyDiscountLimitType(models.Model):
    _name = 'py_discounts.limit.type'
    name = fields.Char(string='Tipo')    

class PyDiscountInternalType(models.Model):
    _name = 'py_discounts.internal_type'
    name = fields.Char(string='Tipo')

class PyDiscountType(models.Model):
    _name = 'py_discounts.type'
    name = fields.Char(string='Tipo')
    
class PyDiscounts(models.Model):
    _name = 'py_discounts.py_discounts'
    _description = 'Descuentos Python'
    name = fields.Char(string='Nombre')
    active = fields.Boolean(string='Activo', default=True)
    descripcion = fields.Char(string="Descripción")
    codigo = fields.Char(string="Código")
    code = fields.Text(string='Código Python')
    
    discount_type = fields.Many2one('py_discounts.type', string='Tipo de descuento')
    date_start = fields.Datetime(string='Fecha Inicio')
    date_end = fields.Datetime(string='Fecha Fin')
    product_ids = fields.Many2many('product.product', string='Productos')
    pricelist_ids = fields.Many2many(comodel_name='product.pricelist', string='Aplica en:')
    internal_type = fields.Many2many(comodel_name='py_discounts.internal_type', string='Descuentos Aplicables')

    
    # def compute(self):
        
    #     ProductTemplate
    #     ResPartner
    #     BrandQty
    #     TierQty
    #     LogisticDiscount
    #     Volume
        
        
    #     class BrowsableObject(object):
    #         def __init__(self, env):
    #             self.env = env
    #     instance = BrowsableObject(self.env)
    #     baselocaldict = {'instance': instance,'line':current_config,'calendar':calendar,'datetime':datetime,'timedelta':timedelta,
    #     'DEFAULT_SERVER_DATE_FORMAT':DEFAULT_SERVER_DATE_FORMAT,'DEFAULT_SERVER_DATETIME_FORMAT':DEFAULT_SERVER_DATETIME_FORMAT,'flujo_de_efectivo':flujo_de_efectivo}
    #     localdict = dict(baselocaldict)
    #     try:
    #         safe_eval(config.code, localdict, mode='exec', nocopy=True)
    #     except Exception as e:
    #         raise ValidationError("Error en la configuración %s %s     %s" % (config.id,config.categoria,e))        