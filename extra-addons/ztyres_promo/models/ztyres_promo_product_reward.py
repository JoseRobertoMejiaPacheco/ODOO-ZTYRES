from odoo import _, api, fields, models


class ProductReward(models.Model):
    _name = 'ztyres_promo.product_reward'
    _description = 'Premio en especia'
    
    name = fields.Char(string='Premio')
