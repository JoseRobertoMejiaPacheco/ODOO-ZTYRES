from odoo import models, fields, api
from odoo.exceptions import ValidationError
import math
START_LOCATION = '1-A-1'
class StockLocation(models.Model):
    _inherit = 'stock.location'

    pos_x = fields.Integer(string='Fila',required=True)
    pos_z = fields.Selection(string='Nivel', selection=[('1', 'A'), ('2', 'B'),('3', 'C'), ('4', 'D'), ('5', 'E')],required=False)
    pos_y = fields.Integer(string='Columna',required=True)
    name = fields.Char(string='Nombre', compute='_compute_name', store=True,readonly=False)
    distance = fields.Float(string='Distancia',readonly=True,
    digits=(16, 5)
    )
    # vender = fields.Boolean(string="Vender", default=True)
    @api.depends('pos_x', 'pos_y', 'pos_z')
    def _compute_name(self):
        for location in self:
            if location.pos_x and location.pos_x and location.pos_z:
                location.name = '%s-%s-%s'%(location.pos_x, self.position_to_letter(int(location.pos_z)),location.pos_y)
                location.distance = self.calculate_distance()
            else:
                location.name = location.name
    def position_to_letter(self,number):
        if 1 <= number <= 26:
            posicion_letra = chr(number + 64)
            return posicion_letra
        else:
            return ""
        


    
    def calculate_distance(self,coord1=[1,1,1]):
        coord2 = [self.pos_x,self.pos_z,self.pos_y]
        distance = math.sqrt(
            (int(coord1[0]) - int(coord2[0])) ** 2 +
            (int(coord1[1]) - int(coord2[1])) ** 2 +
            (int(coord1[2]) - int(coord2[2])) ** 2
        )
        return distance
    
    
#python3 -m ptvsd --host localhost --port 5678 /usr/bin/odoo -d ZTYRES_TEST --config /etc/odoo/odoo.conf --xmlrpc-port=8001 --workers=0
