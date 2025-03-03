from odoo import models, fields, api
from odoo.exceptions import UserError

class PricelistAttachment(models.Model):
    _name = 'mailing.pricelist_attachment'
    _description = 'Attachment related to pricelists for mass mailing'

    date = fields.Datetime(string='Fecha')
    partner_id = fields.Many2many('res.partner', string='Clientes')
    attachment_id = fields.Many2one('ir.attachment', string='Archivo Adjunto')
    mailing_id = fields.Many2one(
        'mailing.mailing', 
        string='Lista de Mailing', 
        ondelete='cascade'
    )  # Relación al registro padre

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'mass_list_mailing_attachment_rel',
        'mailing_list_id',
        'attachment_id',
        string='Archivos Adjuntos',
    )


class MailingList(models.Model):
    _inherit = 'mailing.mailing'

    list_date = fields.Date(string='Fecha de Lista')
    pricelist_attachment_ids = fields.One2many(
        'mailing.pricelist_attachment', 
        'mailing_id', 
        string='Adjuntos de Lista de Precios'
    )
    send_list_price = fields.Selection(
        selection=[('yes', 'Sí'), ('no', 'No')],
        string='Adjuntar Lista de Precios',
        default='no',
    )
    
    def generate_list(self):
        """Generar lista de precios y adjuntarlas al registro actual"""
        if not self.contact_list_ids:
            raise UserError("No hay una lista de contactos definida.")

        # Obtener los socios asociados a las listas de contacto
        partner_ids = self.contact_list_ids.mapped('contact_ids').mapped('partner_id')
        
        if self.send_list_price == 'yes':
            for partner in partner_ids.with_progress(msg="Generando Listas"):
                # Crear la lista de precios
                lista_de_precios = self.env['inv_promo.lista_precios_wizard'].sudo()
                price_list_id = lista_de_precios.create_attachment(self.id, partner)
                
                # Crear el registro del archivo adjunto como sudo
                pricelist_attachment = self.env['mailing.pricelist_attachment'].sudo().create({
                    'date': fields.Datetime.now(),
                    'partner_id': partner,  # Asociar directamente el ID del socio
                    'attachment_id': price_list_id.id,
                    'mailing_id': self.id,  # Asociar al registro actual
                })
                
                # Actualizar la relación many2many como sudo
                self.sudo().write({
                    'pricelist_attachment_ids': [(4, pricelist_attachment.id)],
                })

    def action_view_attachments(self):
        """Acción para el smart button de archivos adjuntos, accesible para cualquier usuario"""
        self.ensure_one()

        # Obtener los archivos adjuntos y asegurarse de que tengan access_token y sean públicos
        attachments = self.sudo().pricelist_attachment_ids.mapped('attachment_id')

        # Leer la acción de los archivos adjuntos como sudo
        action = self.env.ref('base.action_attachment').sudo().read()[0]

        # Actualizar dominio y contexto para la vista
        action.update({
            'domain': [('id', 'in', attachments.ids)],
            'context': dict(self.env.context, default_res_model=self._name, default_res_id=self.id),
        })

        return action