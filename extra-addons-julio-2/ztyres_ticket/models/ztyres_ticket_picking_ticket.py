from odoo import _, api, fields, models
from ..script.ticket import Ticket
import base64

class ZtyresTicketPickingTicket(models.TransientModel):
    _name = 'ztyres_ticket.picking_ticket'
    
    file_data = fields.Binary('File')
    
    def generate_ticket(self,data):
        
        pdf = Ticket(data,len(data.move_line_ids_without_package.ids)*26+(70))        
        base64data = pdf.get_base64_data()
        id = self.create({'file_data': base64data}).id
        url = "/web/content/?model=ztyres_ticket.picking_ticket&id=" + str(id) + "&field=file_data&download=true&filename=Ticket.pdf"
        action = {
            'name': 'Ticket',
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
            }
        return [action]

    
    

