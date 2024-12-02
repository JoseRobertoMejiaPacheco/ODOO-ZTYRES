from odoo import _, api, fields, models



class StockPicking(models.Model):
    _inherit = 'stock.picking'


    def generate_ticket(self):
        x = self.env['ztyres_ticket.picking_ticket'].generate_ticket(self)
        return x[0]

