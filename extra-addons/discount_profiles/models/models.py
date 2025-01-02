# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import timedelta, date,datetime
import calendar
from odoo import models, fields, api
from collections import defaultdict
import math
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.fields import Command
class DiscountProfilesLine(models.Model):
    _name = 'discount_profiles.discount.line'
    _description = 'Limites de descuentos / Condiciones'
    lower_limit = fields.Integer(string='Límite Inferior')
    upper_limit = fields.Integer(string='Límite Superior')
    min_qty = fields.Integer(string='Cantidad mínima de llantas')
    discount = fields.Integer(string='Porcentaje de Descuento')
    profile_financial_discount_id = fields.Many2one('discount_profiles.financial.discount')
    profile_logistic_discount_id = fields.Many2one('discount_profiles.logistic.discount')
    profile_volume_discount_id = fields.Many2one('discount_profiles.volume.discount')
    name = fields.Char(string='Name', compute='_compute_name', store=True)
    @api.depends('lower_limit', 'upper_limit', 'min_qty', 'discount')
    def _compute_name(self):
        for record in self:
            if record.profile_financial_discount_id:
                record.name = f"De {record.lower_limit} a {record.upper_limit} días {record.discount}%"    
            if record.profile_logistic_discount_id:
                record.name = f"De {record.lower_limit} a {record.upper_limit} llantas {record.discount}%"

class DiscountProfiles(models.Model):
    _name = 'discount_profiles.discount'
    _description = 'Descuentos Base'
    _order = 'letter'
    name = fields.Char(string='Nombre', compute='_compute_rec_name', store=True)
    active = fields.Boolean(string='Activo', default=True)
    percent = fields.Integer(string='Porcentaje de Descuento')
    pricelist_ids = fields.Many2many('product.pricelist', string='Aplica en:')    
    letter = fields.Char(string='Letra')


class PartnerFinancialDiscount(models.Model):
    _name = 'discount_profiles.financial.discount'
    _inherit = 'discount_profiles.discount'
    _description = 'Descuento Financiero'
    _order = 'letter'
    active = fields.Boolean(string='Activo', default=True)
    line_ids = fields.One2many('discount_profiles.discount.line', inverse_name='profile_financial_discount_id')
    property_payment_term_id = fields.Many2one('account.payment.term', string='Términos de pago del cliente')
    @api.depends('percent','letter')
    def _compute_rec_name(self):
        for record in self:
            record.name = f'Perfil Financiero: {record.letter or "No Asignado"}'


class PartnerLogisticDiscount(models.Model):
    _name = 'discount_profiles.logistic.discount'
    _inherit = 'discount_profiles.discount'
    _description = 'Descuento Logístico'
    _order = 'letter'
    active = fields.Boolean(string='Activo', default=True)
    line_ids = fields.One2many('discount_profiles.discount.line', inverse_name='profile_logistic_discount_id')        
    
    
    @api.depends('letter')
    def _compute_rec_name(self):
        for record in self:
            record.name = f'{record.letter or "No Asignado"}'

class PartnerVolumeDiscount(models.Model):
    _name = 'discount_profiles.volume.discount'
    _inherit = 'discount_profiles.discount'
    _description = 'Descuento Volumen'
    _order = 'letter'
    active = fields.Boolean(string='Activo', default=True)
    line_ids = fields.One2many('discount_profiles.discount.line', inverse_name='profile_volume_discount_id')        
    
    
    @api.depends('letter')
    def _compute_rec_name(self):
        for record in self:
            record.name = f'{record.letter or "No Asignado"}'

class ResPartner(models.Model):
    _inherit = 'res.partner'
    volume_profile = fields.Many2one('discount_profiles.volume.discount', string='Perfil:  de Volumen',racking=True)
    financial_profile = fields.Many2one('discount_profiles.financial.discount', string='Perfil:  Financiero',racking=True)
    logistic_profile = fields.Many2one('discount_profiles.logistic.discount', string='Perfil:  Logístico',racking=True)
    mostrar_venta_mostrador = fields.Boolean(string="Habilitar Ventas Mostrador")

    @api.onchange('financial_profile')
    def onchange_financial_profile(self):
        self.property_payment_term_id = self.financial_profile.property_payment_term_id.id
            

class SaleOrder(models.Model):

    _inherit = 'sale.order'
        
    volume_profile = fields.Many2one('discount_profiles.volume.discount', string='Perfil:  de Volumen')
    financial_profile = fields.Many2one('discount_profiles.financial.discount', string='Perfil:  Financiero')
    logistic_profile = fields.Many2one('discount_profiles.logistic.discount', string='Perfil:  Logístico')
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.volume_profile = self.partner_id.volume_profile
            self.financial_profile = self.partner_id.financial_profile
            self.logistic_profile = self.partner_id.logistic_profile


class AccountMove(models.Model):
    _inherit = 'account.move'
    payment_discount_text = fields.Html(compute='_compute_payment_discount_text', string='Descuento o Monto a Pagar', store=True)
    bs_nc_amount = fields.Float(compute='_compute_nc_amount', string='Monto NC BS', store=True)
    logistic_nc_amount = fields.Float(compute='_compute_nc_amount', string='Monto NC Logístico', store=True)
    bs_nc_text = fields.Html(compute='_compute_nc_text', string='Bridgestone')
    logistic_nc_text = fields.Html(compute='_compute_nc_text', string='Logístico')
    payment_discount_text = fields.Html(compute='_compute_payment_discount_text', string='Descuento o Monto a Pagar',store=True)
    credit_note_promo = fields.Many2one('account.move',string='Notas de Crédito Promo')
    @api.depends('amount_total', 'partner_id','invoice_date')
    def _compute_payment_discount_text(self):
        for record in self:
            if record.invoice_date and record.invoice_date.year == 2025:
                # Llamamos al método del mixin pasando 'record' como parámetro
                record.payment_discount_text = self.env['payment.discount.mixin'].compute_payment_discount_text(record)

    @api.depends('amount_total', 'partner_id','invoice_date')
    def _compute_nc_amount(self):
        for record in self:
            # Aseguramos que la fecha sea 2025
            if record.invoice_date and record.invoice_date.year == 2025:
                # Calculamos el monto de NC BS y Logístico en cascada
                bs_nc_amount = self.env['payment.discount.mixin'].compute_nc_amount_bs(record)
                logistic_nc_amount = self.env['payment.discount.mixin']._get_logistic_amount(record)
                
                # Asignamos los valores calculados
                record.bs_nc_amount = bs_nc_amount
                record.logistic_nc_amount = logistic_nc_amount
            else:
                # Si no es 2025, asignamos 0 a ambos montos
                record.bs_nc_amount = 0
                record.logistic_nc_amount = 0



    @api.depends('bs_nc_amount', 'logistic_nc_amount','invoice_date')
    def _compute_nc_text(self):
        for record in self:
            # Generamos el HTML con la tabla que contiene ambos montos
            if record.bs_nc_amount and record.logistic_nc_amount:
                record.bs_nc_text = False
                record.logistic_nc_text = self.env['payment.discount.mixin']._generate_html_table(record.bs_nc_amount*1.16, record.logistic_nc_amount*1.16)
            else:
                record.bs_nc_text = False
                record.logistic_nc_text = False

    def generate_and_apply_nc(self):
        for record in self:
            lines_nc = []
            if record.bs_nc_amount>0:
                lines_nc.append((0, 0, {
                        "product_id": 50785,
                        "quantity": 1,
                        'name': 'Descuento B Premium 10%',
                        "price_unit": round((record.bs_nc_amount),2),
                    }))
            if record.logistic_nc_amount>0:
                lines_nc.append((0, 0, {
                        "product_id": 50785,
                        "quantity": 1,
                        'name': 'Descuento Logistico',
                        "price_unit": round((record.logistic_nc_amount),2),
                    }))
            if lines_nc:
                credit_note_vals = {
                    'l10n_mx_edi_origin':f'01|{self.l10n_mx_edi_cfdi_uuid or ""}',
                    'move_type': 'out_refund',  
                    "x_studio_tipo": "Bonificación",
                    "generic_edi":self.generic_edi,
                    "invoice_date": fields.date.today().strftime(DEFAULT_SERVER_DATE_FORMAT),
                    "journal_id": 24,
                    "l10n_mx_edi_payment_method_id": 11, #Condonacion
                    "l10n_mx_edi_usage": "G02",# Devoluciones y Bonificaciones
                    "currency_id": self.env.company.currency_id.id,
                    "partner_id": self.partner_id.id,
                    "partner_shipping_id": self.partner_id.id,   
                        'invoice_line_ids': lines_nc,
                    }
                
                
                res = self.sudo().create(credit_note_vals)
                res.sudo().action_post()
                nc_credit_id = res.mapped('line_ids').filtered(lambda line: line.account_type == 'asset_receivable')
                invoice_debit_id = self.get_debit_move_id()
                apply_out_invoice = self.env['apply_out_invoice.payments']
                apply_out_invoice.sudo().create_partial_reconcile(
                    credit_move_id=nc_credit_id.id,
                    debit_move_id=invoice_debit_id.id,
                    amount=nc_credit_id.credit
                )
                self.credit_note_promo = res.id
    
class SaleOrder2(models.Model):
    _inherit = 'sale.order'
    
    # Campos de cálculo
    payment_discount_text = fields.Html(compute='_compute_payment_discount_text', string='Descuento o Monto a Pagar', store=True)
    bs_nc_amount = fields.Float(compute='_compute_nc_amount', string='Monto NC BS', store=True)
    logistic_nc_amount = fields.Float(compute='_compute_nc_amount', string='Monto NC Logístico', store=True)
    bs_nc_text = fields.Html(compute='_compute_nc_text', string='Bridgestone')
    logistic_nc_text = fields.Html(compute='_compute_nc_text', string='Logístico')
    
    @api.depends('amount_total', 'partner_id')
    def _compute_nc_amount(self):
        for record in self:
            # Aseguramos que la fecha sea 2025
            if record.date_order and record.date_order.year == 2025:
                # Calculamos el monto de NC BS y Logístico en cascada
                bs_nc_amount = self.env['payment.discount.mixin'].compute_nc_amount_bs(record)
                logistic_nc_amount = self.env['payment.discount.mixin']._get_logistic_amount(record)

                # Asignamos los valores calculados
                record.bs_nc_amount = bs_nc_amount
                record.logistic_nc_amount = logistic_nc_amount
            else:
                # Si no es 2025, asignamos 0 a ambos montos
                record.bs_nc_amount = 0
                record.logistic_nc_amount = 0



    @api.depends('bs_nc_amount', 'logistic_nc_amount')
    def _compute_nc_text(self):
        for record in self:
            # Generamos el HTML con la tabla que contiene ambos montos
            if record.bs_nc_amount and record.logistic_nc_amount:
                record.bs_nc_text = False
                record.logistic_nc_text = self.env['payment.discount.mixin']._generate_html_table(record.bs_nc_amount*1.16, record.logistic_nc_amount*1.16)
            else:
                record.bs_nc_text = False
                record.logistic_nc_text = False

    @api.depends('amount_total', 'partner_id')
    def _compute_payment_discount_text(self):
        for record in self:
            if record.date_order and record.date_order.year == 2025:
                # Llamamos al método del mixin para obtener el texto de pago y descuento
                record.payment_discount_text = self.env['payment.discount.mixin'].compute_payment_discount_text(record)
            else:
                record.payment_discount_text = False

# odoo shell -d edu-ZTYRES_TEST -u discount_profiles additional_discounts --config /etc/odoo/odoo.conf --xmlrpc-port=8009 --workers=20