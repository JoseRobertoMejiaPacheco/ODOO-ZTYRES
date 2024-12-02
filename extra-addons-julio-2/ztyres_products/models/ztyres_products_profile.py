from odoo import _, api, fields, models


class Profile(models.Model):
    _name = 'ztyres_products.profile'
    _description = 'New Description'

    name = fields.Char(string='Nombre',compute='_compute_rec_name',store=True)
    number = fields.Float(string='Perfil')

    @api.depends('number')
    def _compute_rec_name(self):
        for record in self:
            if record.number.is_integer():
                record.name = str(int(record.number))
            else:
                record.name = "{:.2f}".format(record.number)
    
