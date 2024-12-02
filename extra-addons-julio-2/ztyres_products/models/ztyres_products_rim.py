from odoo import _, api, fields, models


class Rim(models.Model):
    _name = 'ztyres_products.rim'
    _description = 'New Description'
    _rec_name = 'rim_name'

    number = fields.Float(string='Rin', digits=(4, 2))
    rim_name = fields.Char(compute='_compute_rim_name', string='',store=True)

    @api.depends('number')
    def _compute_rim_name(self):
        for record in self:
            if record.number.is_integer():
                record.rim_name = 'R%s'%(str(int(record.number)))  
            else:
                record.rim_name = 'R%s'%("{:.2f}".format(record.number))
    

    
