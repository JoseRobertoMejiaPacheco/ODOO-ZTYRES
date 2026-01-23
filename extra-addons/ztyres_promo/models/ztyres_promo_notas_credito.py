# -*- coding: utf-8 -*-
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo import models, fields, api,_
from babel.dates import format_date
import pandas as pd
import zipfile
import base64
import io
import json
import logging
from odoo import models, api
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)

class ZtyresVolumen(models.Model):
    _name = 'ztyres_promo.notas_credito'
    
    _rec_name = 'nombre'
    _description = 'ztyres volumen notas de credito'

    start_date = fields.Date(string='Fecha Inicio')
    end_date = fields.Date(string='Fecha Fin')
    status = fields.Selection(string="Estado de Envio", selection=[('draft', 'Borrador'),('approve_p', 'Promocion Aprobada'),('approve', 'NC Aprobadas'),('done', 'Confirmado'),('cancel', 'Cancelado')],default='draft')
    nombre = fields.Char(string="Nombre")
    limite_qty = fields.Integer(string='Límite Cantidad')
    limite_amount = fields.Integer(string='Límite Monto')
    apply_on_groups = fields.Selection(
        string='Aplican Grupos',
        selection=[('si', 'Si'), ('no', 'No')]
    )
    generic_edi = fields.Selection(
        string='Incluir RFC Genérico (Mostrador)',
        selection=[('si', 'Si'), ('no', 'No')]
    )

    promo_type = fields.Selection(
        string='Tipo de Política',
        selection=[('quantity', 'Cantidad'), ('amount', 'Monto')]
    )
    apply_volume = fields.Selection(
        string='Aplica por cantidad global y descuento especifico?',
        selection=[('si', 'Si'), ('no', 'No')]
    )    
    brand_ids = fields.Many2many('ztyres_products.brand','product_brand_rel','product_id','brand_id',string='Marcas')
    tier_ids = fields.Many2many('ztyres_products.tier','product_tier_rel','product_id','tier_id',string='Tiers')
    measure_ids = fields.Many2many('ztyres_products.tire_measure','product_measure_rel','product_id','measure_id',string='Medidas')
    segment_ids = fields.Many2many('ztyres_products.segment','product_segment_rel','product_id','segment_id',string='Segmentos')
    product_ids = fields.Many2many('product.template', string='Productos')
    
    policy_line_qty_ids = fields.One2many(comodel_name='ztyres_promo.current_policy_qty', inverse_name='notas_credito_id')
    policy_line_amount_ids = fields.One2many(comodel_name='ztyres_promo.current_policy_amount', inverse_name='notas_credito_id')
    #line_ids = fields.One2many('ztyres_promo.notas_credito_lines', 'definitive_nc_id', string='Notas de Crédito Definitivas')
    line_ids = fields.One2many('ztyres_promo.notas_credito_lines', 'definitive_nc_id', string='Notas de Crédito Definitivas',domain=[('total_nc_untaxed','>',0)])
    detailed_line_ids = fields.One2many('ztyres_promo.lines', 'definitive_nc_id', string='Detalle')
    
    excluded_partner_ids = fields.Many2many('res.partner')
    not_found = fields.Text(string='Códigos no encontrados')
    # Campos contadores (mostrarán el número en el smart button)
    count_line_ids = fields.Integer(
        string="Count Notas de Crédito",
        compute="_compute_count_line_ids"
    )
    count_detailed_line_ids = fields.Integer(
        string="Count Detalle",
        compute="_compute_count_detailed_line_ids"
    )
    excluded_invoice_ids = fields.Many2many(
        'account.move',
        string='Facturas Excluidas'
    )
    excluded_invoice_ids_domain = fields.Char(
        compute="_compute_excluded_invoice_ids_domain",
        readonly=True,
        store=False
    )
    
    @api.depends('start_date', 'end_date')
    def _compute_excluded_invoice_ids_domain(self):
        for record in self:
            domain = [
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted')
            ]

            if record.start_date:
                domain.append(('invoice_date', '>=', record.start_date))
            if record.end_date:
                domain.append(('invoice_date', '<=', record.end_date))

            # 🔴 CLAVE: siempre un string válido
            record.excluded_invoice_ids_domain = str(domain or [])
    
    @api.depends('line_ids')
    def _compute_count_line_ids(self):
        for record in self:
            domain = [('definitive_nc_id', 'in', self.ids)]
            record.count_line_ids = len(self.env['ztyres_promo.notas_credito_lines'].search(domain))

    @api.depends('detailed_line_ids')
    def _compute_count_detailed_line_ids(self):
        for record in self:
            record.count_detailed_line_ids = len(record.detailed_line_ids)

    def action_open_detailed_line_ids(self):
        """Retorna la acción para visualizar el 'Detalle' (detailed_line_ids) en modo solo lectura."""
        self.ensure_one()
        action = self.env.ref('ztyres_promo.lines_action').sudo().read()[0]
        action['domain'] = [('id', 'in', self.detailed_line_ids.ids)]
        action['context'] = dict(
            form_view_initial_mode='readonly',
            no_create=True,
            no_edit=True,
            no_delete=True
        )
        return action
    
    def action_approve(self):
        self.status = 'approve'
        
    def action_approve_p(self):
        self.status = 'approve_p'    
    
    def _get_valid_invoices(self,invoice_type):
        if invoice_type == 'out_invoice':
            domain = [('id', 'in', self.detailed_line_ids.ids), ('state', 'in', ['valid']),('move_type','in',['out_invoice'])]
            invoices = self.detailed_line_ids.search(domain).mapped('move_id')
        elif invoice_type == 'out_refund':
            invoices = self.line_ids.mapped('nc_credit_id')
        return invoices
    
    def _set_nc_amount(self):
        for line in self.line_ids:
            line.total_nc_untaxed = line.price_subtotal * (line.reward_percent/100)

    def get_grouped_data(self):
        lines_grouped = self.env['ztyres_promo.notas_credito_lines'].read_group(
            domain=[('id','in',self.line_ids.ids)],
            fields=['group_id', 'quantity:sum'],
            groupby=['group_id'],
            orderby='group_id'
        )
        
        result = []
        for data in lines_grouped:
            # 'group_id' es una tupla (id, nombre), por eso data['group_id'][0] es el ID del grupo
            group_id_data = data.get('group_id')
            if isinstance(group_id_data, (list, tuple)) and len(group_id_data) > 0:
                group_id = group_id_data[0]  # Accede de forma segura al primer elemento
            else:
                group_id = False            
            quantity_sum = data['quantity']
            if group_id:
                # Agrega una tupla (group_id, quantity_sum) a la lista
                result.append((group_id, quantity_sum))
        
        return result

    def get_grouped_data_volume(self):
        lines_grouped = self.env['ztyres_promo.lines'].read_group(
            domain=[('id','in',self.detailed_line_ids.ids)],
            fields=['group_id', 'quantity:sum'],
            groupby=['group_id'],
            orderby='group_id'
        )
        
        result = []
        for data in lines_grouped:
            # 'group_id' es una tupla (id, nombre), por eso data['group_id'][0] es el ID del grupo
            group_id_data = data.get('group_id')
            if isinstance(group_id_data, (list, tuple)) and len(group_id_data) > 0:
                group_id = group_id_data[0]  # Accede de forma segura al primer elemento
            else:
                group_id = False            
            quantity_sum = data['quantity']
            if group_id:
                # Agrega una tupla (group_id, quantity_sum) a la lista
                result.append((group_id, quantity_sum))
        
        return result

    def action_calcular_nc(self):
        detailed_data = []
        self.line_ids.search([('definitive_nc_id', 'in', self.ids)]).unlink()
        self.detailed_line_ids.search([('definitive_nc_id', 'in', self.ids)]).unlink()
        for partner_id in self._get_partner_ids():
            valid_lines = self.line_ids._domain_lines(self._get_domain(partner_id,self.start_date,self.end_date))
            invalid_lines = self.line_ids._domain_lines(self._get_invalid_domain(valid_lines,partner_id,self.start_date,self.end_date))
            result = self._get_dict_detailed_data(valid_lines, invalid_lines) or []
            detailed_data.extend(result or [])
        self.detailed_line_ids = detailed_data
        res_2 = self._set_nc_lines()
        self.line_ids = res_2
        
        if self.apply_volume == 'si' and self.apply_on_groups == 'si':
            for group_id,quantity_sum in self.get_grouped_data_volume():
                group_discount = self.line_ids._get_discount_percent(self.policy_line_qty_ids,quantity_sum)
                self.line_ids.filtered(lambda line: line.group_id.id == group_id).write({'reward_percent': group_discount})            
        
        elif self.apply_on_groups == 'si':
            for group_id,quantity_sum in self.get_grouped_data():
                group_discount = self.line_ids._get_discount_percent(self.policy_line_qty_ids,quantity_sum)
                self.line_ids.filtered(lambda line: line.group_id.id == group_id).write({'reward_percent': group_discount})
        
        self._set_nc_amount()

    def _get_partner_ids(self):
        lines = self.env['account.move.line'].search([
            ('move_id.invoice_date', '>=', self.start_date),
            ('move_id.invoice_date', '<=', self.end_date),
            ('move_id.move_type', 'in', ['out_invoice', 'out_refund']),
            ('partner_id', '!=', False),
        ])
        return lines.mapped('partner_id')
    
    def _get_invalid_domain(self,records,partner_id,start_date,end_date):
        # --- Condiciones obligatorias (AND) ---
        domain = [
            ('move_id.move_type', 'in', ['out_invoice', 'out_refund']),
            ('move_id.state', '=', 'posted'),
            ('product_id.detailed_type', 'in', ['product']),
            ('display_type', 'in', ['product']),
            ('move_id.invoice_date', '>=', start_date),
            ('move_id.invoice_date', '<=', end_date),
            ('partner_id', 'in', partner_id.ids)
        ]
        domain.append(('id', 'not in', records.ids))
        return domain
    
    def _get_domain(self, partner_id, start_date, end_date):
        domain = [
            ('move_id.move_type', 'in', ['out_invoice', 'out_refund']),
            ('move_id.state', '=', 'posted'),
            ('product_id.detailed_type', 'in', ['product']),
            ('display_type', 'in', ['product']),
            ('move_id.invoice_date', '>=', start_date),
            ('move_id.invoice_date', '<=', end_date),
            ('partner_id', 'in', partner_id.ids)
        ]
        
        # Condiciones OR (brand_ids O product_ids)
        or_conditions = []
        if self.brand_ids:
            or_conditions.append(('product_id.brand_id', 'in', self.brand_ids.ids))
        if self.product_ids:
            or_conditions.append(('product_id', 'in', self.product_ids.product_variant_id.ids))
        
        # Solo agregar OR si hay condiciones
        if or_conditions:
            if len(or_conditions) > 1:
                domain.append('|')  # Operador OR solo si hay 2+ condiciones
            domain.extend(or_conditions)
        return domain

    def _get_dict_data(self,partner_id,valid_amount,valid_qty,rfc,discount,total_nc_untaxed):
        return {
                    'partner_id':partner_id,
                    'group_id': self._get_group_id(partner_id),
                    'price_subtotal':valid_amount,
                    'quantity':valid_qty,
                    'rfc':rfc,
                    'reward_percent':discount,
                    'total_nc_untaxed':total_nc_untaxed
                    
            }
    

    def _get_dict_detailed_data(self,valid_lines, invalid_lines):
        
        data = []
        for line in valid_lines:
            price_subtotal = line.price_subtotal if line.move_id.move_type == 'out_invoice' else -line.price_subtotal
            quantity = line.quantity if line.move_id.move_type == 'out_invoice' else -line.quantity
            vals = {
                'rfc':line.move_id.edi_vat_receptor,
                'group_id': self._get_group_id(line.partner_id.id),
                'move_type': line.move_id.move_type,
                'move_id': line.move_id.id,
                'product_name': line.product_id.name,
                'name': line.name,
                'product_code': line.product_id.default_code,
                'product_brand': line.product_id.brand_id.name if line.product_id.brand_id else '',
                'date': line.move_id.invoice_date,
                'quantity': quantity,
                'price_subtotal': price_subtotal,
                'partner_id': line.partner_id.id,
                'sale_origin': line.sale_line_ids.mapped('order_id.name') if line.sale_line_ids else '',
                'list_origin': line.sale_line_ids.list_origin if line.sale_line_ids else '',
                'state': 'valid'
            }
            if line.partner_id.id in self.excluded_partner_ids.ids or (self.generic_edi == 'no' and line.move_id.edi_vat_receptor== 'XAXX010101000'):
                vals.update({
                    'state': 'invalid'
                })
            if line.move_id.id in self.excluded_invoice_ids.ids:
                vals.update({
                    'state': 'invalid'
                })                
            data.append((0,0,vals))
        
        # Linhas "invalid"
        for line in invalid_lines:
            price_subtotal = line.price_subtotal if line.move_id.move_type == 'out_invoice' else -line.price_subtotal
            quantity = line.quantity if line.move_id.move_type == 'out_invoice' else -line.quantity
            data.append((0,0,{
                'rfc':line.move_id.edi_vat_receptor,
                'group_id': self._get_group_id(line.partner_id.id),
                'move_type': line.move_id.move_type,
                'move_id': line.move_id.id,
                'product_name': line.product_id.name,
                'name': line.name,
                'product_code': line.product_id.default_code,
                'product_brand': line.product_id.brand_id.name if line.product_id.brand_id else '',
                'date': line.move_id.invoice_date,
                'quantity': quantity,
                'price_subtotal': price_subtotal,
                'partner_id': line.partner_id.id,
                'sale_origin': line.sale_line_ids.mapped('order_id.name') if line.sale_line_ids else '',
                'list_origin': line.sale_line_ids.list_origin if line.sale_line_ids else '',
                'state': 'invalid'
            }))
        
        return (data)
    
    def _set_nc_lines(self): 
        data = []
        # Para cada partner en las líneas detalladas
        partners = self.detailed_line_ids.mapped('partner_id')
        for partner_id in self.detailed_line_ids.mapped('partner_id'):
            edi_vat = self.detailed_line_ids.filtered(
                lambda l: l.partner_id.id == partner_id.id and l.state == 'valid'  and l.rfc != 'XAXX010101000'
            )
            edi_vat_generic = self.detailed_line_ids.filtered(
                lambda l: l.partner_id.id == partner_id.id and l.state == 'valid' and l.rfc == 'XAXX010101000'
            )            
            total_amount =  sum(edi_vat.mapped('price_subtotal')) + sum(edi_vat_generic.mapped('price_subtotal'))
            if self.apply_volume == 'no':
                total_qty =  sum(edi_vat.mapped('quantity')) + sum(edi_vat_generic.mapped('quantity'))
            if self.apply_volume == 'si':
                total_qty =  sum(              
                self.detailed_line_ids.filtered(
                lambda l: l.partner_id.id == partner_id.id
            ).mapped('quantity'))
            print(total_qty)
            discount = 0
            if self.promo_type == 'quantity':
                discount = self.line_ids._get_discount_percent(self.policy_line_qty_ids, total_qty)
            if self.promo_type == 'amount':
                discount = self.line_ids._get_discount_percent(self.policy_line_amount_ids, total_amount)
            
            base_v = sum(edi_vat.mapped('price_subtotal'))
            descuento_v = base_v * discount / 100
            #def _get_dict_data(self,partner_id,valid_amount,valid_qty,rfc,discount,total_nc_untaxed):
            _line_v = self._get_dict_data(
                partner_id.id,                             # ID del partner (entero)
                sum(edi_vat.mapped('price_subtotal')),            # total price_subtotal en 'edi_vat'
                sum(edi_vat.mapped('quantity')),
                partner_id.vat,      # descuento calculado
                discount,
                descuento_v
            )
            if _line_v:
                data.append((0, 0, _line_v))
            base_g = sum(edi_vat_generic.mapped('price_subtotal'))
            descuento_g = base_g * discount / 100
            #def _get_dict_data(self,partner_id,valid_amount,valid_qty,rfc,discount,total_nc_untaxed):
            _line_v = self._get_dict_data(
                partner_id.id,                             # ID del partner (entero)
                sum(edi_vat_generic.mapped('price_subtotal')),            # total price_subtotal en 'edi_vat'
                sum(edi_vat_generic.mapped('quantity')),
                'XAXX010101000',
                discount,
                descuento_g
            )
            if _line_v:
                data.append((0, 0, _line_v))
        # Importante: return (data) FUERA de todos los 'for'
        return data
    
    def _get_group_id(self, partner_id):
        groups = self.env['ztyres_volumen.group'].search([])
        _group = False
        for group in groups:
            if partner_id in group.partner_ids.ids:
                _group = group.id
        return _group

    def check_sat_status(self):
        self._check_uuid()
    
    def _check_uuid(self):
        for line in self.line_ids:
            line.nc_credit_id.l10n_mx_edi_update_sat_status()
            line.sat_estatus = line.nc_credit_id.l10n_mx_edi_sat_status
    

    def action_open_line_ids(self):
        """Retorna la acción para visualizar las 'Notas de Crédito Definitivas' (line_ids) en modo solo lectura."""
        self.ensure_one()
        action = self.env.ref('ztyres_promo.action_ztyres_promo_notas_credito_lines').sudo().read()[0]
        action['domain'] = [('definitive_nc_id', 'in', self.ids)]
        action['context'] = dict(
            form_view_initial_mode='readonly',
            no_create=True,
            no_edit=True,
            no_delete=True
        )
        return action

    def _create_nc(self):
        lines = self.line_ids.filtered(lambda line: line.total_nc_untaxed > 0)
        for line in lines:
            domain = line.action_view_details().get('domain',False)
            domain.append(('state','in',['valid']))
            uuids = self.env['ztyres_promo.lines'].search(domain).mapped('move_id').mapped('l10n_mx_edi_cfdi_uuid') or ""
            try:
                uuids_string = '01|' + ','.join(uuids)
            except:
                uuids_string = False
                print("Error")
            generic = line.rfc == 'XAXX010101000'
            credit_note_vals = {                
                'move_type': 'out_refund',
                "x_studio_tipo": "Bonificación",
                "generic_edi": generic,
                "invoice_date": fields.Date.today().strftime(DEFAULT_SERVER_DATE_FORMAT),
                "journal_id": 148,
                "l10n_mx_edi_payment_method_id": 11,  # Condonacion
                "l10n_mx_edi_usage": "G02",  # Devoluciones y Bonificaciones
                "currency_id": self.env.company.currency_id.id,
                "partner_id": line.partner_id.id,
                "partner_shipping_id": line.partner_id.id,
                "invoice_line_ids": [(0, 0, {
                    "product_id": 50785,
                    "quantity": 1,
                    "name": self.nombre,
                    "price_unit": round(line.total_nc_untaxed, 2),
                })],
            }
            if uuids:
                credit_note_vals.update({'l10n_mx_edi_origin':uuids_string })
            if generic:
                credit_note_vals.update({'edi_vat_receptor':'XAXX010101000'})
            credit_note = line.nc_credit_id.sudo().create(credit_note_vals)
            credit_note.sudo().action_post()
            docs = credit_note.edi_document_ids.filtered(lambda d: d.state in ('to_send', 'to_cancel') and d.blocking_level != 'error')
            if docs:
                docs._process_documents_web_services(with_commit=True)
            line.nc_credit_id = credit_note.id
    
    def action_confirmar_nc(self):
        self._create_nc()
        self.status = 'done'
        """Método vacío temporalmente"""
        return True
    
    def action_open_excel_import(self):
        return {
            'name': _('Importar Productos desde Excel'),
            'type': 'ir.actions.act_window',
            'res_model': 'ztyres_promo.product_excel_wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
            },
        }
    
    def clear_product_relations(self):
        """Elimina todas las relaciones con productos (deja la relación vacía)"""
        for record in self:
            # Esta es la forma correcta de limpiar una relación Many2many
            record.write({'product_ids': [(5, 0, 0)],'not_found':False})
    

    def download_zip_xmls(self):
        """
        Descarga un ZIP con todos los XMLs de facturas válidas
        Valida que exista un XML por cada factura válida
        """
        # Obtener facturas válidas
        valid_invoices = self._get_valid_invoices(self._context.get('move_type'))
        if not valid_invoices:
            raise UserError("No se encontraron facturas válidas para procesar")
        
        _logger.info(f"Iniciando generación de ZIP para {len(valid_invoices)} facturas")
        
        # Buscar documentos EDI con archivos adjuntos (con sudo() para evitar problemas de permisos)
        edi_documents = self.env['account.edi.document'].sudo().search([
            ('move_id', 'in', valid_invoices.ids),
            ('attachment_id', '!=', False)
        ])
        
        # Validación exhaustiva
        invoices_with_xml = edi_documents.mapped('move_id')
        missing_invoices = valid_invoices - invoices_with_xml
        if missing_invoices:
            missing_names = "\n• ".join(missing_invoices.mapped('name'))
            raise UserError(
                "¡Validación fallida!\n\n"
                f"Facturas válidas encontradas: {len(valid_invoices)}\n"
                f"Archivos XML encontrados: {len(edi_documents)}\n\n"
                "Las siguientes facturas no tienen XML asociado:\n"
                f"• {missing_names}\n\n"
                "Por favor genere los XML faltantes antes de continuar."
            )
        
        # Crear ZIP en memoria
        zip_buffer = io.BytesIO()
        try:
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for doc in edi_documents:
                    try:
                        xml_content = base64.b64decode(doc.attachment_id.sudo().datas)
                        filename = f"{doc.move_id.name.replace('/', '_')}.xml"
                        zip_file.writestr(filename, xml_content)
                        _logger.debug(f"Archivo añadido: {filename}")
                    except Exception as e:
                        _logger.error(f"Error procesando XML para {doc.move_id.name}: {str(e)}")
                        raise UserError(
                            f"Error al procesar el XML de la factura {doc.move_id.name}:\n{str(e)}"
                        ) from e
            
            zip_buffer.seek(0)
            zip_data = zip_buffer.read()
            
            # Crear registro de attachment
            attachment = self.env['ir.attachment'].sudo().create({
                'name': f"{self._context.get('move_type')}_XML_{fields.Date.today()}.zip",
                'datas': base64.b64encode(zip_data),
                'type': 'binary',
                'public': True,
                'res_model': self._name,
                'res_id': self.id,
            })
            
            _logger.info(f"ZIP generado correctamente con {len(edi_documents)} archivos")
            
            # Retornar acción de descarga
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }
        
        except Exception as e:
            _logger.error(f"Error al generar ZIP: {str(e)}")
            raise UserError(f"Error al generar el archivo ZIP:\n{str(e)}")
        finally:
            zip_buffer.close() 