#-*- coding: utf-8 -*-
from io import BytesIO
import re
from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
from PIL import Image
from pyzbar.pyzbar import decode
from pdf2image import convert_from_bytes
from hermetrics.damerau_levenshtein import DamerauLevenshtein
from ..scripts.csf_to_dict  import get_odoo_vals

class ResPartner(models.Model):
    _inherit = 'res.partner'
    csf = fields.Char(string='Constancia de situación fiscal')
    csf_uploaded = fields.Selection(string='CSF Verificado', selection=[('draft', 'CSF Sin Verificar'), ('done', 'CSF Verificado')])
    file_one_name = fields.Char(string='Nombre de Archivo')
    file_one = fields.Binary(string='Archivo')
    
    def get_csf_link(self):
        try:            
            attachtment = self.existing_csf_attachment()
            if not attachtment.datas:
                raise UserError('No se encontró ningun archivo válido.')
            sample_string_bytes = BytesIO(base64.b64decode(attachtment.datas))
            bytes_string = sample_string_bytes.getvalue()
            first_image_PIL = self.pdf_to_image(bytes_string)
            data = decode(Image.open(first_image_PIL.fp))[0][0]
            url_csf = data.decode("utf-8")
            if not self.csf:
                self.csf = url_csf
        except:
            pass
    
    def pdf_to_image(self,bytes):
        images = convert_from_bytes(bytes)
        return images[0]

    def validate_partner_fields(self,partner):
        """
        Validate if all fields of partner have a value.
        
        :param partner: The partner object to validate.
        :return: A list of field names that don't have values.
        """
        fields_to_check = [
            'state_id',
            'city_id',
            'country_id',
            'street',
            'vat',
            'zip',
            'name',
            'l10n_mx_edi_fiscal_regime',
            'csf_uploaded'
        ]
        empty_fields = [field for field in fields_to_check if not getattr(partner, field)]
        return empty_fields


    def update_partner_from_csf(self):
        self.get_csf_link()
        for rec in self:
            if not rec.csf:
                raise UserError('Por favor agregue información válida')
            data = get_odoo_vals(rec.csf)
            partner = self.get_id_by_vat(data.get('vat'))
            partner.state_id = self.get_state_id(data.get('state_id'))
            partner.city_id = self.get_city_id_id(data.get('city_id'), partner.state_id.id)
            partner.country_id = self.get_country_id('México')
            partner.street = data.get('street')
            partner.vat = data.get('vat')
            partner.l10n_mx_edi_curp = data.get('l10n_mx_edi_curp')
            partner.zip = data.get('zip')
            partner.name = data.get('name')
            partner.l10n_mx_edi_fiscal_regime = self.get_fiscal_regime_value(data.get('l10n_mx_edi_fiscal_regime'))
            partner.csf_uploaded = 'done'
            missing_fields = self.validate_partner_fields(partner)
            if missing_fields:
                raise UserError(f"Los siguientes campos no tienen valores: {', '.join(missing_fields)}")
    
    def existing_csf_attachment(self):
        attachment = self.env['ir.attachment']
        existing_record = attachment.search([('res_id','in',[self.id]),('res_model','in',['res.partner']),('description','in',[('%s_%s'%('CSF',self.vat))])])
        return existing_record
        
    def upload_csf(self):
        attachment = self.env['ir.attachment']
        existing_record = self.existing_csf_attachment()
        if existing_record:
            raise UserError('Este cliente ya cuenta con un archivo relacionado a la constancia de situación fiscal. Si desea reemplazar los datos elimine el archivo %s'%(existing_record.mapped('name')))
            
        if self.file_one and self.file_one_name:
            attachment_file={
                                'res_id': self.id,
                                'res_model': 'res.partner',
                                'name': ('%s_%s.%s'%('CSF',self.vat,self.file_one_name.split('.')[1])),
                                'datas': self.file_one,
                                'mimetype':'application/%s'%(self.file_one_name.split('.')[1]),
                                'index_content':'application',
                                'type':'binary',
                                'description':('%s_%s'%('CSF',self.vat)),
                        }
            res = attachment.create(attachment_file)
            if res:
                self.file_one = False
               
    
    def get_id_by_vat(self,vat):
        res = self.search([('vat','in',[vat]),('parent_id','in',[False])])
        self.check_record(res)
        if not res:
            raise UserError('No se encontró ningún cliente con el rfc %s'%(vat))
        return res  
    
    def get_state_id(self,state_name):
        res = self.state_id.search([('name','=ilike',state_name)])
        self.check_record(res)
        return res.id
    
    def get_city_id_id(self,city_name,state_id_id):
        res = self.city_id.search([('name','=ilike',city_name),('state_id','in',[state_id_id])])
        self.check_record(res)
        return res.id
    
    def get_near_fiscal_regime(self,fiscal_regime):
        fiscal_regime_values = self._fields['l10n_mx_edi_fiscal_regime'].args['selection']
        key_distance = {}
        for rec in fiscal_regime_values:
            distance = DamerauLevenshtein.distance(self,fiscal_regime,rec[1])
            percent_similitude = 100-(distance * 100)/len(rec[1])
            key_distance.update({rec[0]:percent_similitude})
        return max(key_distance, key=key_distance.get)
        
    def get_fiscal_regime_value(self,fiscal_regime):
        return self.get_near_fiscal_regime(fiscal_regime)
    
    def get_country_id(self,country_name):
        res = self.country_id.search([('name','=ilike',country_name)])
        self.check_record(res)
        return res.id
    
    def check_record(self,record):
        if len(record)>1:
            raise UserError('Se han encontrado uno o más registros con el mismo nombre %s'%(record.mapped('name')))


            
        
    
            
                
