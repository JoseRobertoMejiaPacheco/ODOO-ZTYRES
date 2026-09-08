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
    name = fields.Char(string='Nombre', compute='_compute_rec_name', store=True)
    active = fields.Boolean(string='Activo', default=True)
    percent = fields.Integer(string='Porcentaje de Descuento')
    pricelist_ids = fields.Many2many('product.pricelist', string='Aplica en:')    
    


class PartnerFinancialDiscount(models.Model):
    _name = 'discount_profiles.financial.discount'
    _inherit = 'discount_profiles.discount'
    _description = 'Descuento Financiero'
    _order = 'id'
    active = fields.Boolean(string='Activo', default=True)
    line_ids = fields.One2many('discount_profiles.discount.line', inverse_name='profile_financial_discount_id')
    property_payment_term_id = fields.Many2one('account.payment.term', string='Términos de pago del cliente')
    letter = fields.Char(string='Letra')
    @api.depends('percent','letter')
    def _compute_rec_name(self):
        for record in self:
            record.name = f'Perfil Financiero: {record.letter or "No Asignado"}'


class PartnerLogisticDiscount(models.Model):
    _name = 'discount_profiles.logistic.discount'
    _inherit = 'discount_profiles.discount'
    _description = 'Descuento Logístico'
    _order = 'id'
    active = fields.Boolean(string='Activo', default=True)
    line_ids = fields.One2many('discount_profiles.discount.line', inverse_name='profile_logistic_discount_id')        
    letter = fields.Char(string='Letra')
    
    @api.depends('letter')
    def _compute_rec_name(self):
        for record in self:
            record.name = f'{record.letter or "No Asignado"}'

class PartnerVolumeDiscount(models.Model):
    _name = 'discount_profiles.volume.discount'
    _inherit = 'discount_profiles.discount'
    _description = 'Descuento Volumen'
    _order = 'id'
    active = fields.Boolean(string='Activo', default=True)
    line_ids = fields.One2many('discount_profiles.discount.line', inverse_name='profile_volume_discount_id')        
    letter = fields.Char(string='Letra')
    
    @api.depends('letter')
    def _compute_rec_name(self):
        for record in self:
            record.name = f'{record.letter or "No Asignado"}'

class ResPartner(models.Model):
    _inherit = 'res.partner'
    volume_profile = fields.Many2one('discount_profiles.volume.discount', string='Perfil:  de Volumen',tracking=True)
    financial_profile = fields.Many2one('discount_profiles.financial.discount', string='Perfil:  Financiero',tracking=True)
    logistic_profile = fields.Many2one('discount_profiles.logistic.discount', string='Perfil:  Logístico',tracking=True)
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
    embarque_logistic_nc_amount = fields.Float(
        compute='_compute_embarque_logistic_amounts', string='Monto Logístico Embarque sin IVA', store=False)
    embarque_logistic_nc_total = fields.Float(
        compute='_compute_embarque_logistic_amounts', string='Monto Logístico Embarque con IVA', store=False)
    bs_nc_text = fields.Html(compute='_compute_nc_text', string='Bridgestone')
    logistic_nc_text = fields.Html(compute='_compute_nc_text', string='Logístico')
    payment_discount_text = fields.Html(compute='_compute_payment_discount_text', string='Descuento o Monto a Pagar',store=True)
    credit_note_promo = fields.Many2one('account.move',string='Notas de Crédito Promo')
    use_embarque_logistic_nc = fields.Boolean(
        string='Logístico gestionado por Embarques', default=False, copy=False,
        help='Cuando está activo, el descuento logístico ya no se calcula por '
             'el perfil histórico. Embarques genera una NC logística separada.')
    
    @api.depends('invoice_line_ids.price_subtotal', 'invoice_line_ids.tax_ids',
                 'invoice_line_ids.sale_line_ids', 'use_embarque_logistic_nc')
    def _compute_embarque_logistic_amounts(self):
        for record in self:
            untaxed = total = 0.0
            if record.use_embarque_logistic_nc and record.move_type == 'out_invoice':
                # Si Embarques está instalado, usar SU cálculo fiscal: agrupa por
                # impuestos, redondea cada línea real de la NC y después calcula
                # IVA. Es exactamente el mismo criterio con el que se crea la NC.
                helper = getattr(record, '_get_embarque_logistic_nc_totals', False)
                if helper:
                    untaxed, total = helper()
                else:
                    # Respaldo si discount_profiles se usa sin Embarques.
                    groups = {}
                    for line in record.invoice_line_ids.filtered(
                            lambda l: l.display_type in (False, 'product') and l.sale_line_ids):
                        orders = line.sale_line_ids.mapped('order_id').filtered(
                            lambda order: bool(getattr(order, 'embarque_ids', False)))
                        percentages = set(orders.mapped('embarque_discount_percentage')) if orders else set()
                        if len(percentages) != 1:
                            continue
                        percentage = percentages.pop() or 0.0
                        tax_ids = tuple(sorted(line.tax_ids.ids))
                        groups[tax_ids] = groups.get(tax_ids, 0.0) + (
                            abs(line.price_subtotal) * percentage / 100.0)
                    for tax_ids, raw_amount in groups.items():
                        amount = record.currency_id.round(raw_amount) if record.currency_id else raw_amount
                        untaxed += amount
                        taxes = self.env['account.tax'].browse(list(tax_ids))
                        if taxes:
                            tax_result = taxes.compute_all(
                                amount, currency=record.currency_id, quantity=1.0,
                                partner=record.partner_id)
                            total += tax_result['total_included']
                        else:
                            total += amount
                    if record.currency_id:
                        untaxed = record.currency_id.round(untaxed)
                        total = record.currency_id.round(total)
            record.embarque_logistic_nc_amount = untaxed
            record.embarque_logistic_nc_total = total

    @api.depends('amount_total', 'partner_id', 'invoice_date', 'use_embarque_logistic_nc')
    def _compute_payment_discount_text(self):
        for record in self:
            if record.invoice_date and record.invoice_date.year in [2025,2026]:
                # Llamamos al método del mixin pasando 'record' como parámetro
                record.payment_discount_text = self.env['payment.discount.mixin'].compute_payment_discount_text(record)

    @api.depends('amount_total', 'partner_id', 'invoice_date', 'use_embarque_logistic_nc')
    def _compute_nc_amount(self):
        for record in self:
            # Aseguramos que la fecha sea 2025
            if record.invoice_date and record.invoice_date.year in [2025,2026]:
                # Calculamos el monto de NC BS y Logístico en cascada
                bs_nc_amount = self.env['payment.discount.mixin'].compute_nc_amount_bs(record)
                if record.use_embarque_logistic_nc:
                    # En el flujo nuevo el campo conserva el VALOR logístico
                    # (sin IVA) para compatibilidad con reportes y módulos que ya
                    # lo consumen. La bandera impide que discount_profiles genere
                    # la NC logística antigua.
                    logistic_nc_amount = record.embarque_logistic_nc_amount
                else:
                    logistic_nc_amount = self.env['payment.discount.mixin']._get_logistic_amount(record, bs_nc_amount)

                record.bs_nc_amount = bs_nc_amount
                record.logistic_nc_amount = logistic_nc_amount
            else:
                # Si no es 2025, asignamos 0 a ambos montos
                record.bs_nc_amount = 0
                record.logistic_nc_amount = 0



    @api.depends('bs_nc_amount', 'logistic_nc_amount', 'embarque_logistic_nc_amount',
                 'use_embarque_logistic_nc', 'embarque_logistic_nc_total', 'invoice_date')
    def _compute_nc_text(self):
        for record in self:
            logistic_amount = (record.embarque_logistic_nc_amount
                               if record.use_embarque_logistic_nc
                               else record.logistic_nc_amount)
            if record.bs_nc_amount or logistic_amount:
                record.bs_nc_text = False
                bs_total = record.bs_nc_amount * 1.16
                logistic_total = (record.embarque_logistic_nc_total
                                  if record.use_embarque_logistic_nc
                                  else logistic_amount * 1.16)
                # Una vez creada la NC, el documento fiscal es la fuente final.
                # Esto garantiza que el resumen muestre exactamente los mismos
                # centavos que la NC (p. ej. 343.26, nunca 343.24).
                nc = getattr(record, 'embarque_logistic_nc_id', False)
                if record.use_embarque_logistic_nc and nc:
                    logistic_total = abs(nc.amount_total)
                record.logistic_nc_text = self.env['payment.discount.mixin']._generate_html_table(
                    bs_total, logistic_total)
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
            # IMPORTANTE: discount_profiles ya NO genera NC logística.
            # El valor logistic_nc_amount se conserva únicamente por compatibilidad
            # con históricos/reportes. La generación fiscal del descuento logístico
            # pertenece exclusivamente a embarques_module, que valida que las líneas
            # facturadas provengan de un embarque aplicable y crea una NC separada.
            if lines_nc:
                credit_note_vals = {
                    'l10n_mx_edi_origin':f'01|{self.l10n_mx_edi_cfdi_uuid or ""}',
                    'move_type': 'out_refund',  
                    "x_studio_tipo": "Bonificación",
                    "generic_edi":self.generic_edi,
                    "invoice_date": fields.date.today().strftime(DEFAULT_SERVER_DATE_FORMAT),
                    "journal_id": 148,
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
    embarque_logistic_nc_amount = fields.Float(
        compute='_compute_embarque_logistic_amounts', string='Monto Logístico Embarque sin IVA', store=False)
    embarque_logistic_nc_total = fields.Float(
        compute='_compute_embarque_logistic_amounts', string='Monto Logístico Embarque con IVA', store=False)
    bs_nc_text = fields.Html(compute='_compute_nc_text', string='Bridgestone')
    logistic_nc_text = fields.Html(compute='_compute_nc_text', string='Logístico')
    promo_onyx = fields.Boolean(string='Promoción Onyx 500 llantas')
    use_embarque_logistic_nc = fields.Boolean(
        string='Logístico gestionado por Embarques', default=False, copy=False,
        help='Evita el cálculo logístico histórico por perfil cuando el pedido '
             'será gestionado por el módulo de Embarques.')
    
    
    @api.depends('order_line.price_subtotal', 'order_line.tax_id', 'use_embarque_logistic_nc')
    def _compute_embarque_logistic_amounts(self):
        for record in self:
            untaxed = 0.0
            total = 0.0
            percentage = getattr(record, 'embarque_discount_percentage', 0.0) or 0.0
            if record.use_embarque_logistic_nc and percentage:
                for line in record.order_line.filtered(lambda l: not l.display_type):
                    if line.is_downpayment:
                        continue
                    if hasattr(line, '_es_linea_paqueteria') and line._es_linea_paqueteria():
                        continue
                    base_discount = abs(line.price_subtotal) * percentage / 100.0
                    untaxed += base_discount
                    taxes = line.tax_id.compute_all(
                        base_discount, currency=record.currency_id, quantity=1.0,
                        product=line.product_id, partner=record.partner_id)
                    total += taxes['total_included']
            record.embarque_logistic_nc_amount = record.currency_id.round(untaxed) if record.currency_id else untaxed
            record.embarque_logistic_nc_total = record.currency_id.round(total) if record.currency_id else total

    @api.depends('amount_total', 'partner_id', 'use_embarque_logistic_nc')
    def _compute_nc_amount(self):
        for record in self:
            # Aseguramos que la fecha sea 2025
            if record.date_order and record.date_order.year in [2025,2026]:
                # Calculamos el monto de NC BS y Logístico en cascada
                bs_nc_amount = self.env['payment.discount.mixin'].compute_nc_amount_bs(record)
                if record.use_embarque_logistic_nc:
                    logistic_nc_amount = record.embarque_logistic_nc_amount
                else:
                    logistic_nc_amount = self.env['payment.discount.mixin']._get_logistic_amount(record, bs_nc_amount)

                record.bs_nc_amount = bs_nc_amount
                record.logistic_nc_amount = logistic_nc_amount
            else:
                # Si no es 2025, asignamos 0 a ambos montos
                record.bs_nc_amount = 0
                record.logistic_nc_amount = 0



    @api.depends('bs_nc_amount', 'logistic_nc_amount', 'embarque_logistic_nc_amount',
                 'use_embarque_logistic_nc', 'embarque_logistic_nc_total')
    def _compute_nc_text(self):
        for record in self:
            logistic_amount = (record.embarque_logistic_nc_amount
                               if record.use_embarque_logistic_nc
                               else record.logistic_nc_amount)
            if record.date_order and record.date_order.year in [2025, 2026] and (record.bs_nc_amount or logistic_amount):
                record.bs_nc_text = False
                bs_total = record.bs_nc_amount * 1.16
                logistic_total = (record.embarque_logistic_nc_total
                                  if record.use_embarque_logistic_nc
                                  else logistic_amount * 1.16)
                record.logistic_nc_text = self.env['payment.discount.mixin']._generate_html_table(
                    bs_total, logistic_total)
            else:
                record.bs_nc_text = False
                record.logistic_nc_text = False

    @api.depends('amount_total', 'partner_id', 'use_embarque_logistic_nc')
    def _compute_payment_discount_text(self):
        for record in self:
            if record.date_order and record.date_order.year in [2025,2026]:
                # Llamamos al método del mixin para obtener el texto de pago y descuento
                record.payment_discount_text = self.env['payment.discount.mixin'].compute_payment_discount_text(record)
            else:
                record.payment_discount_text = False

# odoo shell -d ZTYRES --config /etc/odoo/odoo.conf --xmlrpc-port=8009 --workers=20