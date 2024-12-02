from odoo import _, api, fields, models


class Separator(models.Model):
    _name = 'ztyres_products.separator'
    _description = 'New Description'
    _rec_name = 'character'
    character = fields.Char(string='Carácter Separador')
