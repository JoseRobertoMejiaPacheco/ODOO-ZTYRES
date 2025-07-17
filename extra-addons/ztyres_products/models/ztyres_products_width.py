from odoo import _, api, fields, models

class Width(models.Model):
    _name = 'ztyres_products.width'
    _description = 'Ancho'

    # name = fields.Char(string='Nombre', compute='_compute_rec_name')
    name = fields.Char(string='Nombre',compute='_compute_rec_name',store=True)
    number = fields.Float(string='Ancho')

    @api.depends('number')
    def _compute_rec_name(self):
        for record in self:
            if record.number.is_integer():
                record.name = str(int(record.number))
            else:
                record.name = "{:.2f}".format(record.number)

