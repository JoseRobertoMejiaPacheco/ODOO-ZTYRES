from odoo import _, api, fields, models


class CurrentPolicyVolume(models.Model):
    _name = 'ztyres_promo.current_policy_qty'
    _description = 'Limites de descuentos / Condiciones Actuales Cantidad'
    
    lower_limit = fields.Integer(string='Límite Inferior')
    upper_limit = fields.Integer(string='Límite Superior')
    min_qty = fields.Integer(string='Cantidad mínima de llantas')
    discount = fields.Integer(string='Porcentaje de Descuento')
    notas_credito_id = fields.Many2one(comodel_name='ztyres_promo.notas_credito')

class CurrentPolicyVolumeAmount(models.Model):
    _name = 'ztyres_promo.current_policy_amount'
    _description = 'Limites de descuentos / Condiciones Actuales  Monto'
    lower_limit = fields.Integer(string='Límite Inferior')
    upper_limit = fields.Integer(string='Límite Superior')
    min_qty = fields.Integer(string='Cantidad mínima de llantas')
    discount = fields.Integer(string='Porcentaje de Descuento')
    notas_credito_id = fields.Many2one(comodel_name='ztyres_promo.notas_credito')

class CurrentPolicyCoupon(models.Model):
    _name = 'ztyres_promo.coupon'
    _description = 'Cupones'
    product_id = fields.Many2one('product.template', string='Producto')
    amount = fields.Float(string='Monto')
    notas_credito_id = fields.Many2one(comodel_name='ztyres_promo.notas_credito')