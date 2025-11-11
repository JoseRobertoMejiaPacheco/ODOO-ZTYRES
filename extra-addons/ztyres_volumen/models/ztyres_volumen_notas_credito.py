# -*- coding: utf-8 -*-
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo import models, fields, api
from babel.dates import format_date

class ZtyresVolumen(models.Model):
    _name = 'ztyres_volumen.notas_credito'
    _rec_name = 'nombre'
    _description = 'ztyres volumen notas de credito'

    start_date = fields.Date(string='Fecha Inicio')
    end_date = fields.Date(string='Fecha Fin')
    status = fields.Selection(string="Estado de Envio", selection=[('draft', 'Borrador'), ('approve', 'Aprobado'),('done', 'Confirmado')],default='draft')
    nombre     = fields.Char(string="Nombre", compute="_get_name_in_spanish", store=True)
    bs_discount = fields.Selection(string='Restar NC de BS', selection=[('yes', 'Calcular restando NC de BS'), ('no', 'Calcular sin restar NC de BS')])    
    pricelist_ids = fields.Char(string='Listas de Precio')
    
    
    policy_line_ids = fields.One2many(comodel_name='ztyres_volumen.current_policy', inverse_name='notas_credito_id', string='')
    
    
    line_ids = fields.One2many('ztyres_volumen.notas_credito_lines', 'definitive_nc_id', string='Notas de Crédito Definitivas',domain=[('total_nc_untaxed','>',0)])
    detailed_line_ids = fields.One2many('ztyres_volumen.lines', 'definitive_nc_id', string='Detalle')
    
    excluded_partner_ids = fields.Many2many('res.partner')
    
    # Campos contadores (mostrarán el número en el smart button)
    count_line_ids = fields.Integer(
        string="Count Notas de Crédito",
        compute="_compute_count_line_ids"
    )
    count_detailed_line_ids = fields.Integer(
        string="Count Detalle",
        compute="_compute_count_detailed_line_ids"
    )
    
    def check_sat_status(self):
        self._check_uuid()
    
    def action_approve(self):
        self.status = 'approve'
    
    def _check_uuid(self):
        for line in self.line_ids:
            line.nc_credit_id.l10n_mx_edi_update_sat_status()
            line.sat_estatus = line.nc_credit_id.l10n_mx_edi_sat_status
    
    @api.depends('start_date', 'end_date')
    def _get_name_in_spanish(self):
        for record in self:
            if record.start_date and record.end_date:
                start_date_str = format_date(record.start_date, format='long', locale='es').upper()
                end_date_str   = format_date(record.end_date, format='long', locale='es').upper()
                record.nombre = f"NC Volumen del {start_date_str} al {end_date_str}"
            else:
                record.nombre = ''
        
    def action_open_line_ids(self):
        """Retorna la acción para visualizar las 'Notas de Crédito Definitivas' (line_ids) en modo solo lectura."""
        self.ensure_one()
        action = self.env.ref('ztyres_volumen.action_ztyres_volumen_notas_credito_lines').sudo().read()[0]
        action['domain'] = [('definitive_nc_id', 'in', self.ids)]
        action['context'] = dict(
            form_view_initial_mode='readonly',
            no_create=True,
            no_edit=True,
            no_delete=True
        )
        return action
    
    def action_open_detailed_line_ids(self):
        """Retorna la acción para visualizar el 'Detalle' (detailed_line_ids) en modo solo lectura."""
        self.ensure_one()
        action = self.env.ref('ztyres_volumen.lines_action').sudo().read()[0]
        action['domain'] = [('id', 'in', self.detailed_line_ids.ids)]
        action['context'] = dict(
            form_view_initial_mode='readonly',
            no_create=True,
            no_edit=True,
            no_delete=True
        )
        return action
        
    @api.depends('line_ids')
    def _compute_count_line_ids(self):
        for record in self:
            domain = [('definitive_nc_id', 'in', self.ids)]
            record.count_line_ids = len(self.env['ztyres_volumen.notas_credito_lines'].search(domain))

    @api.depends('detailed_line_ids')
    def _compute_count_detailed_line_ids(self):
        for record in self:
            record.count_detailed_line_ids = len(record.detailed_line_ids)
    
    def _get_partner_ids(self):
        return self.env['account.move.line'].search([('move_id.invoice_date','>=',self.start_date),
            ('move_id.invoice_date','<=',self.end_date),]).mapped('partner_id')
    
    def apply_group_policy(self):
        pass

    def _get_group_id(self, partner_id):
        groups = self.env['ztyres_volumen.group'].search([])
        _group = False
        for group in groups:
            if partner_id in group.partner_ids.ids:
                _group = group.id
        return _group
    
    def get_grouped_data(self):
        lines_grouped = self.env['ztyres_volumen.notas_credito_lines'].read_group(
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
    
    def _create_nc(self):
        lines = self.line_ids.filtered(lambda line: line.total_nc_untaxed > 0)
        for line in lines:
            domain = line.action_view_details().get('domain',False)
            domain.append(('state','in',['valid']))
            uuids = self.env['ztyres_promo.lines'].search(domain).mapped('move_id').mapped('l10n_mx_edi_cfdi_uuid')
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
                "journal_id": 24,
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
    
    def _set_nc_lines(self):
        data = []

        # Para cada partner en las líneas detalladas
        for partner_id in self.detailed_line_ids.mapped('partner_id'):
            # Filtramos según la lógica que tenías
            generic = self.detailed_line_ids.filtered(
                lambda l: l.partner_id == partner_id and l.state == 'valid' and l.rfc == 'XAXX010101000'
            )
            edi_vat = self.detailed_line_ids.filtered(
                lambda l: l.partner_id == partner_id and l.state == 'valid' and l.rfc != 'XAXX010101000'
            )
            generic_nc_bs = self.detailed_line_ids.filtered(
                lambda l: l.partner_id == partner_id and l.state == 'nc bs' and l.rfc == 'XAXX010101000'
            )
            edi_vat_nc_bs = self.detailed_line_ids.filtered(
                lambda l: l.partner_id == partner_id and l.state == 'nc bs' and l.rfc != 'XAXX010101000'
            )
            
            # Cálculo de totales
            total_qty = sum(generic.mapped('quantity')) + sum(edi_vat.mapped('quantity'))
            discount = self.line_ids._get_discount_percent(self.policy_line_ids, total_qty)
            
            # -----------------------------------------------------------------
            # EJEMPLO: Para "generic"
            # -----------------------------------------------------------------
            # Supongamos que deseas un "base" para generic con:
            #   base_g = sum(generic.mapped('price_subtotal')) + sum(generic_nc_bs.mapped('price_subtotal_bs'))
            # y un "descuento_calculado" = base_g * discount / 100
            base_g = sum(generic.mapped('price_subtotal')) + sum(generic_nc_bs.mapped('price_subtotal_bs'))
            descuento_g = base_g * discount / 100
            
            _line_g = self._get_dict_data(
                partner_id.id,
                sum(generic.mapped('price_subtotal')),    # total price_subtotal en 'generic'
                sum(generic_nc_bs.mapped('price_subtotal_bs')),
                sum(generic.mapped('quantity')),
                discount,
                descuento_g,
                'XAXX010101000',        # descuento calculado
                base_g,              # base calculada
                
            )
            if _line_g:
                data.append((0, 0, _line_g))
            
            # -----------------------------------------------------------------
            # EJEMPLO: Para "edi_vat"
            # -----------------------------------------------------------------
            # Supongamos un base_v = sum(edi_vat.mapped('price_subtotal')) - sum(edi_vat_nc_bs.mapped('price_subtotal_bs'))
            # y su descuento descuento_v = base_v * discount / 100
            base_v = sum(edi_vat.mapped('price_subtotal')) - sum(edi_vat_nc_bs.mapped('price_subtotal_bs'))
            descuento_v = base_v * discount / 100
            #_get_dict_data(nc_amount,rfc,base,group_id=False)
            _line_v = self._get_dict_data(
                partner_id.id,                             # ID del partner (entero)
                sum(edi_vat.mapped('price_subtotal')),            # total price_subtotal en 'edi_vat'
                sum(edi_vat_nc_bs.mapped('price_subtotal_bs')),
                sum(edi_vat.mapped('quantity')),
                discount,
                descuento_v,
                partner_id.vat,      # descuento calculado
                base_v,           # base calculada
                
            )
            if _line_v:
                data.append((0, 0, _line_v))
        
        # Importante: return (data) FUERA de todos los 'for'
        return data

    def action_calcular_nc(self):
        self.line_ids.search([('definitive_nc_id', 'in', self.ids)]).unlink()
        self.detailed_line_ids.search([('definitive_nc_id', 'in', self.ids)]).unlink()
        detailed_data = []
        for partner_id in self._get_partner_ids():
            # discount = self.line_ids._get_discount_percent(self.policy_line_ids,valid_qty)
            invalid_lines = self.line_ids._invalid_lines(partner_id,self.start_date,self.end_date,[x.strip() for x in self.pricelist_ids.split(",")] )
            nc_bs = self.line_ids._nc_bridgestone(partner_id,self.start_date,self.end_date)
            valid_lines = self.line_ids._valid_lines(partner_id,self.start_date,self.end_date,[x.strip() for x in self.pricelist_ids.split(",")] )
            result = self._get_dict_detailed_data(nc_bs, valid_lines, invalid_lines)
            detailed_data.extend(result or [])
        
        self.detailed_line_ids = detailed_data
        self.line_ids = self._set_nc_lines()
        for group_id,quantity_sum in self.get_grouped_data():
            group_discount = self.line_ids._get_discount_percent(self.policy_line_ids,quantity_sum)
            self.line_ids.filtered(lambda line: line.group_id.id == group_id).write({'reward_percent': group_discount})
        self._set_nc_amount()
        print(self._get_name_in_spanish())
        """Método vacío temporalmente"""
        return True
    
    def _set_nc_amount(self):
        for line in self.line_ids:
            line.total_nc_untaxed = line.base * (line.reward_percent/100)
    
    def _get_dict_data(self,partner_id,valid_amount,nc_bs_amount,valid_qty,reward_percent,nc_amount,rfc,base,group_id=False):
        if not base:
            return False
        return {
                    'partner_id':partner_id,
                    'group_id': self._get_group_id(partner_id),
                    'price_subtotal':valid_amount,
                    'quantity':valid_qty,
                    'price_subtotal_bs':nc_bs_amount,
                    'base': valid_amount-nc_bs_amount,
                    'total_nc_untaxed': nc_amount,
                    'reward_percent': reward_percent,
                    'rfc':rfc,
                    'base':base
            }

    def _get_dict_detailed_data(self, bs_lines, valid_lines, invalid_lines):
        data = []
        if self.bs_discount == 'yes':
            # Linhas "nc bs"
            for line in bs_lines:
                quantity = line.quantity if line.move_id.move_type == 'out_invoice' else -line.quantity
                data.append((0,0,{
                    'rfc':line.move_id.edi_vat_receptor,
                    'group_id': self._get_group_id(line.partner_id),
                    'move_type': line.move_id.move_type,
                    'move_id': line.move_id.id,
                    'product_name': line.product_id.name,
                    'name': line.name,
                    'product_code': line.product_id.default_code,
                    'product_brand': line.product_id.brand_id.name if line.product_id.brand_id else '',
                    'date': line.move_id.invoice_date,
                    'quantity': line.quantity,
                    'price_subtotal': 0,
                    'price_subtotal_bs': line.price_subtotal,
                    'partner_id': line.partner_id.id,
                    'partner_name': line.partner_id.name,
                    'sale_origin': line.sale_line_ids.mapped('order_id.name') if line.sale_line_ids else '',
                    'list_origin': line.sale_line_ids.list_origin if line.sale_line_ids else '',
                    'state': 'nc bs'
                }))
        
        # Linhas "valid"
        
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
                'price_subtotal_bs': 0,
                'partner_id': line.partner_id.id,
                'partner_name': line.partner_id.name,
                'sale_origin': line.sale_line_ids.mapped('order_id.name') if line.sale_line_ids else '',
                'list_origin': line.sale_line_ids.list_origin if line.sale_line_ids else '',
                'state': 'valid'
            }
            if line.partner_id.id in self.excluded_partner_ids.ids:
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
                'price_subtotal_bs': 0,
                'partner_id': line.partner_id.id,
                'partner_name': line.partner_id.name,
                'sale_origin': line.sale_line_ids.mapped('order_id.name') if line.sale_line_ids else '',
                'list_origin': line.sale_line_ids.list_origin if line.sale_line_ids else '',
                'state': 'invalid'
            }))
        
        return (data)
    
    def action_confirmar_nc(self):
        self._create_nc()
        self.status = 'done'
        """Método vacío temporalmente"""
        return True