# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import timedelta, date,datetime
import calendar
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
    # _sql_constraints = [
    #     ('unique_percent', 'UNIQUE (percent)', 'No puede haber dos descuentos con el mismo porcentaje.'),
    # ] 
    name = fields.Char(string='Nombre', compute='_compute_rec_name', store=True)
    active = fields.Boolean(string='Activo', default=True)
    percent = fields.Integer(string='Porcentaje de Descuento')
    pricelist_ids = fields.Many2many('product.pricelist', string='Aplica en:')    
    letter = fields.Char(string='Letra')
    
    # @api.constrains('percent')
    # def _check_percent_value(self):
    #     for record in self:
    #         if record.percent < 0 or record.percent > 12:
    #             raise ValidationError(_('El porcentaje debe estar entre 0 y 12.'))


class PartnerFinancialDiscount(models.Model):
    _name = 'discount_profiles.financial.discount'
    _inherit = 'discount_profiles.discount'
    _description = 'Descuento Financiero'
    _order = 'letter'
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
        
    # @api.model
    # def create(self, vals):
    #     if vals.get('partner_id',False):
    #         partner = self.env['res.partner'].browse(vals['partner_id'])
    #         vals.update({
    #             'volume_profile': partner.volume_profile.id,
    #             'financial_profile': partner.financial_profile.id,
    #             'logistic_profile': partner.logistic_profile.id,
    #         })
    #     return super(SaleOrder, self).create(vals)

    # def write(self, vals):
    #     if vals.get('partner_id',False):
    #         partner = self.env['res.partner'].browse(vals['partner_id'])
    #         vals.update({
    #             'volume_profile': partner.volume_profile.id,
    #             'financial_profile': partner.financial_profile.id,
    #             'logistic_profile': partner.logistic_profile.id,
    #         })
    #     return super(SaleOrder, self).write(vals)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.volume_profile = self.partner_id.volume_profile
            self.financial_profile = self.partner_id.financial_profile
            self.logistic_profile = self.partner_id.logistic_profile


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    payment_discount_text = fields.Html(compute='_compute_payment_discount_text', string='Descuento o Monto a Pagar')

    
    def get_row_values_descuento(self):
            descuentos = []
            for move in self:
                if move.partner_id.financial_profile:
                    total_con_iva = 0
                    subtotal_lines = move.invoice_line_ids.filtered(lambda line: line.product_id.id == 50959).mapped('price_subtotal')
                    if subtotal_lines:
                        iva_amount = (sum(subtotal_lines) * 1.16) - sum(subtotal_lines)
                        total_con_iva = sum(subtotal_lines) + iva_amount
                    descuentos_cliente = move.partner_id.financial_profile.line_ids
                    for profile_line in descuentos_cliente:
                        y = (1 - (profile_line.discount / 100.0))
                        pagos = move.amount_total - move.amount_residual
                        monto_descuento = ((((move.amount_total-(total_con_iva+pagos))*y))+ total_con_iva)
                        fecha_vencimiento = move.date+ timedelta(days=profile_line.upper_limit)
                        descuentos.append((profile_line.discount, profile_line.upper_limit, fecha_vencimiento, monto_descuento))
            return descuentos

    @api.depends('invoice_date_due')
    def _compute_payment_discount_text(self):
        for record in self:
            headers = ('Descuento', 'Dias de Pago', 'Fecha máxima', 'Cantidad a pagar')
            meses_espanol = {
                'January': 'enero',
                'February': 'febrero',
                'March': 'marzo',
                'April': 'abril',
                'May': 'mayo',
                'June': 'junio',
                'July': 'julio',
                'August': 'agosto',
                'September': 'septiembre',
                'October': 'octubre',
                'November': 'noviembre',
                'December': 'diciembre'
            }
            rows = record.get_row_values_descuento()
            html = ''
            html = '<table class="page-break1 table table-sm o_main_table table-borderless">'
            html += '<thead>'
            html += '<tr>'
            for header in headers:
                html += f'<th>{header}</th>'
            html += '</tr>'
            html += '</thead>'

            for row in rows:
                html += '<tr>'
                for cell_idx, cell in enumerate(row):
                    if isinstance(cell, datetime):
                        # Obtener el nombre del mes en español
                        mes = meses_espanol[calendar.month_name[cell.month]]
                        # Formatear la fecha como "12 de abril de 2024"
                        cell = f'{cell.day} de {mes} de {cell.year}'  # Formato: día de mes de año (por ejemplo, 12 de abril de 2024)
                    elif isinstance(cell, float):
                        # Formatear el monto con formato de moneda
                        cell = f'${cell:,.2f}'
                    elif isinstance(cell, int) and headers[cell_idx] == 'Dias de Pago':
                        # Formatear el valor de días agregando "Días" al final
                        cell = f'{cell} Días'
                    elif isinstance(cell, int):
                        # Formatear el descuento con el símbolo de porcentaje
                        cell = f'{cell}%'  # Para otros valores de la fila
                    else:
                        # Mantener otros tipos de datos sin formato especial
                        pass
                    html += f'<td>{cell}</td>'
                html += '</tr>'

            html += '</table>'

            record.payment_discount_text = html

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    payment_discount_text = fields.Html(compute='_compute_payment_discount_text', string='Descuento o Monto a Pagar')
    
    def get_row_values_descuento(self):
        """
        Encuentra el descuento correspondiente a un código y cantidad de días dados en un diccionario de descuentos.

        Returns:
        list of tuples: Lista de tuplas conteniendo el descuento, los días, la fecha de vencimiento y el monto después del descuento.
        """

        descuentos = []
        for order in self:
            total_con_iva = 0
            subtotal_lines = order.order_line.filtered(lambda line: line.product_id.id == 50959).mapped('price_subtotal')
            if subtotal_lines:
                iva_amount = sum(subtotal_lines) * 0.16
                total_con_iva = sum(subtotal_lines) + iva_amount
            if order.partner_id.financial_profile:
                descuentos_cliente = order.partner_id.financial_profile.line_ids
                for profile_line in descuentos_cliente:
                    print(order.amount_total-total_con_iva)
                    y = (1 - (profile_line.discount / 100.0))
                    monto_descuento = ((order.amount_total-total_con_iva)*(y))+ total_con_iva
                    fecha_vencimiento = order.date_order + timedelta(days=profile_line.upper_limit)
                    descuentos.append((profile_line.discount, profile_line.upper_limit, fecha_vencimiento, monto_descuento))
        return descuentos
    
    # Diccionario de meses en inglés y su equivalente en español


    @api.depends('date_order')
    def _compute_payment_discount_text(self):
        if self.is_expo:
            self.payment_discount_text = ""
            return
        for record in self:
            headers = ('Descuento', 'Dias de Pago', 'Fecha máxima', 'Cantidad a pagar')
            meses_espanol = {
                'January': 'enero',
                'February': 'febrero',
                'March': 'marzo',
                'April': 'abril',
                'May': 'mayo',
                'June': 'junio',
                'July': 'julio',
                'August': 'agosto',
                'September': 'septiembre',
                'October': 'octubre',
                'November': 'noviembre',
                'December': 'diciembre'
            }
            rows = record.get_row_values_descuento()
            html = ''
            html = '<table class="page-break1 table table-sm o_main_table table-borderless">'
            html += '<thead>'
            html += '<tr>'
            for header in headers:
                html += f'<th>{header}</th>'
            html += '</tr>'
            html += '</thead>'

            for row in rows:
                html += '<tr>'
                for cell_idx, cell in enumerate(row):
                    if isinstance(cell, datetime):
                        # Obtener el nombre del mes en español
                        mes = meses_espanol[calendar.month_name[cell.month]]
                        # Formatear la fecha como "12 de abril de 2024"
                        cell = f'{cell.day} de {mes} de {cell.year}'  # Formato: día de mes de año (por ejemplo, 12 de abril de 2024)
                    elif isinstance(cell, float):
                        # Formatear el monto con formato de moneda
                        cell = f'${cell:,.2f}'
                    elif isinstance(cell, int) and headers[cell_idx] == 'Dias de Pago':
                        # Formatear el valor de días agregando "Días" al final
                        cell = f'{cell} Días'
                    elif isinstance(cell, int):
                        # Formatear el descuento con el símbolo de porcentaje
                        cell = f'{cell}%'  # Para otros valores de la fila
                    else:
                        # Mantener otros tipos de datos sin formato especial
                        pass
                    html += f'<td>{cell}</td>'
                html += '</tr>'

            html += '</table>'

            record.payment_discount_text = html            

# odoo shell -d edu-ZTYRES_TEST -u discount_profiles additional_discounts --config /etc/odoo/odoo.conf --xmlrpc-port=8009 --workers=20
            