#-*- coding: utf-8 -*-
from odoo import models, fields, api
from collections import defaultdict
import math
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.fields import Command

class AdditionalDiscounts(models.Model):
    _name = 'additional_discounts.additional_discounts'
    _description = 'additional_discounts.additional_discounts'
    active = fields.Boolean(string='Activo', default=True)
    name = fields.Char(string='Nombre')
    line_ids = fields.One2many('additional_discounts.additional_discounts_line', inverse_name='additional_discounts_id')


class AdditionalDiscountsLine(models.Model):
    _name = 'additional_discounts.additional_discounts_line'
    _description = 'additional_discounts.additional_discounts_line'

    additional_discounts_id = fields.Many2one('additional_discounts.additional_discounts')    
    manufacturer_id = fields.Many2many(
        'ztyres_products.manufacturer',
        relation='additional_discounts_line_manufacturer_rel',
        string='Fabricante'
    )
    brand_id = fields.Many2many(
        'ztyres_products.brand',
        relation='additional_discounts_line_brand_rel',
        string='Marca'
    )
    tier_id = fields.Many2many('ztyres_products.tier',relation='additional_discounts_line_tier_rel', string='Tier')
    segment_id = fields.Many2many('ztyres_products.segment',relation='additional_discounts_line_segment_rel',string='Segmento')
    lower_limit = fields.Integer(string='Límite Inferior')
    upper_limit = fields.Integer(string='Límite Superior')
    discount_amount = fields.Integer(string='Monto de Descuento')

class AdditionalDiscountsProduct(models.Model):
    _name = 'additional_discounts.products'
    active = fields.Boolean(string='Activo', default=True)
    line = fields.One2many('additional_discounts.products_line','additional_prod_id', string='Lineas de producto')
    is_mix = fields.Boolean(string='Se pueden mezclar?',default=False)
    min_qty = fields.Integer(string='Cantidad mínima')
    
class AdditionalDiscounts(models.Model):
    _name = 'additional_discounts.products_line'
    additional_prod_id = fields.Many2one('additional_discounts.products', string='Additional Discounts Product')
    product_tmpl_id = fields.Many2many('product.template', string='Productos')
    qty = fields.Integer(string='Cantidad mínima')
    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self: self.env.user.company_id.currency_id.id)
    price = fields.Monetary(string='Precio', currency_field='currency_id')

class AccountMove(models.Model):
    _inherit = 'account.move'
    _description = 'asdfsdf'
    credit_note_promo = fields.Many2one('account.move',string='Notas de Crédito Promo')
    
    def get_lines_grouped_by_brand(self):
        # Diccionario para acumular las cantidades por producto
        product_quantities = defaultdict(int)
        amount = 0
        all_promo = []
        # Recorrer las líneas de la factura
        for line in self.invoice_line_ids:
            if line.product_id.product_tmpl_id:
                brand_id = line.product_id.product_tmpl_id.brand_id
                quantity = line.quantity
                # Acumular la cantidad por producto
                product_quantities[brand_id] += quantity
        # Convertir el diccionario a una lista de tuplas (producto, cantidad)
        grouped_data = list(product_quantities.items())
        brand_id = False
        final_amount = 0
        for brand_name, quantity in grouped_data:
            x = self.calculate_discount_brand(brand_name, quantity)
            if x:
                brand_id = x.brand_id
                final_amount = int((quantity/x.lower_limit))*x.discount_amount
                all_promo.append((final_amount,brand_id))
        return all_promo

    def calculate_discount_brand(self, brand_name, quantity):
        applicable_discounts = self.env['additional_discounts.additional_discounts_line'].search([
                    ('brand_id', 'in', brand_name.ids),('additional_discounts_id.active','=',True)
                ])
        if not applicable_discounts:
            return 0  # No hay descuento disponible para esta marca
        for discount_line in applicable_discounts:
            f_disc_ids = []
            f_disc = False
            if quantity >= discount_line.lower_limit:
                f_disc = discount_line
                f_disc_ids.append(f_disc)
        if f_disc_ids:
            f_disc_ids = max(f_disc_ids, key=lambda x: x.discount_amount)
        # Si no se encuentra un descuento exacto, se aplica el más alto disponible
        return f_disc_ids

    def discount_increase(self,quotation=False):
        is_expo_values = self.line_ids.sale_line_ids.mapped('order_id').mapped('is_expo')
        if not any(is_expo_values):
            vals_for_credit_note = []
            promo_item = self.ahhh_group()
            for manufacturer_item in promo_item:
                description = f'PROMOCIÓN: {manufacturer_item[0].additional_discounts_id.name} PARTICIPANTES: {", ".join(manufacturer_item[0].manufacturer_id.mapped("name"))} CANTIDAD PARTICIPANTE: {manufacturer_item[1]}'
                monto = (manufacturer_item[0].discount_amount)/(1+(16/100))
                vals_for_credit_note.append((description,monto))                   
            logistic_discount,quantity_logistic,valid_lines = self.get_total_logistic_discount_line()
            if logistic_discount:
                if logistic_discount.discount > 0:
                    valid_lines = self.invoice_line_ids.filtered(lambda x: x.sale_line_ids.list_origin in logistic_discount.profile_logistic_discount_id.pricelist_ids.mapped('name') and x.product_id.id not in [50959])
                    price_subtotal = sum(valid_lines.mapped('price_subtotal'))
                    vals_for_credit_note.append((f'DESCUENTO: Logístico {logistic_discount.discount}% CANTIDAD PARTICIPANTE: {quantity_logistic}', price_subtotal * (logistic_discount.discount / 100)))
            lines_nc = []
            for description,amount in vals_for_credit_note:
                if amount>0:
                    print(amount)
                    print(round((amount/1.16),2))
                    lines_nc.append((0, 0, {
                            "product_id": 50785,
                            "quantity": 1,
                            'name': description,
                            "price_unit": round((amount),2),
                        }))
            if quotation:
                return lines_nc
            if lines_nc:
                credit_note_vals = {
                    'l10n_mx_edi_origin':f'01|{self.l10n_mx_edi_cfdi_uuid or ""}',
                    'move_type': 'out_refund',  
                    "x_studio_tipo": "Bonificación",
                    "generic_edi":self.generic_edi,
                    "invoice_date": fields.date.today().strftime(DEFAULT_SERVER_DATE_FORMAT),
                    "journal_id": 24,
                    "l10n_mx_edi_payment_method_id": 11, #Condonacion
                    "l10n_mx_edi_usage": "G01",# Devoluciones y Bonificaciones
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


    def get_total_logistic_discount_line(self):
        sin_descuento_logistico = self.env['additional_discounts.products'].search([('active','=',True)]).mapped('line')
        #sin_descuento_logistico = sin_descuento_logistico + [50959]
        array_condiciones = []
        for l_item in sin_descuento_logistico:
            array_condiciones.append((l_item.qty,l_item.mapped('product_tmpl_id').mapped('product_variant_id').id))
        # Filtrar las líneas de factura que no cumplan las condiciones
        filtered_lines = self.invoice_line_ids.filtered(
            lambda line: (
                line.sale_line_ids.list_origin in ['MAYOREO','PROMOCIÓN']
                and line.product_id.id not in [50959]
                and not any(line.product_id.id == prod_id and line.quantity <= qty for qty, prod_id in array_condiciones)
            )
        )
        print(len(self.invoice_line_ids))
        print(len(filtered_lines))
        x = self.invoice_line_ids - filtered_lines
        print(x)
        for item in x:
            print(item.product_id.display_name)
            print(item.quantity)
        # Sumar las cantidades de las líneas filtradas
        #########################################################################################################################
        total_quantity = sum(filtered_lines.mapped('quantity'))
        if self.partner_id.logistic_profile:
            applicable_discounts = self.env['discount_profiles.logistic.discount'].browse(self.partner_id.logistic_profile.id)
            if applicable_discounts.id in (4, 6):
                for discount_line in applicable_discounts:
                    for line in discount_line.line_ids:
                        if total_quantity > line.upper_limit:
                            applicable_discounts = self.env['discount_profiles.logistic.discount'].browse(2)
        #########################################################################################################################
        else:
            applicable_discounts = False
            
        f_disc_ids = []
        if not applicable_discounts:
            return []  # No hay descuento disponible para esta marca
        for discount_line in applicable_discounts:
            f_disc = False
            for line in discount_line.line_ids:
                if total_quantity >= line.lower_limit:
                    f_disc = line
                    f_disc_ids.append(f_disc)
        if f_disc_ids:
            f_disc_ids = max(f_disc_ids, key=lambda x: x.discount)
        # Si no se encuentra un descuento exacto, se aplica el más alto disponible
        return f_disc_ids,total_quantity,filtered_lines


    def ahhh_group(self):
        # Diccionario para acumular las cantidades por producto
        promo_lines = []
        promo = self.env['additional_discounts.additional_discounts_line'].search([('additional_discounts_id.active','=',True)])
        for promo_line in promo:
            filtered_lines = self.invoice_line_ids.filtered(
    lambda x: (
        (x.product_id.product_tmpl_id.default_code not in ['8106','8118','8103','8210','8215']) and
        (not promo_line.brand_id or x.product_id.product_tmpl_id.brand_id.id in promo_line.brand_id.ids) and
        (not promo_line.manufacturer_id or x.product_id.product_tmpl_id.manufacturer_id.id in promo_line.manufacturer_id.ids) and
        (not promo_line.tier_id or x.product_id.product_tmpl_id.tier_id.id in promo_line.tier_id.ids) and
        (not promo_line.segment_id or x.product_id.product_tmpl_id.segment_id.id in promo_line.segment_id.ids)
    )
)
            qty = sum(filtered_lines.mapped('quantity'))
            print(promo_line.lower_limit)
            print(promo_line.upper_limit)
            if promo_line.lower_limit<=qty<=promo_line.upper_limit:
                promo_lines.append((promo_line,qty))
        return promo_lines


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    payment_promo_text = fields.Html(compute='compute_promo_text', string='Promociones')
    bonificacion = fields.Float(string='Monto Bonificación')
    tipo_de_timbrado = fields.Selection(string='Facturación', selection=[('normal', 'A Razón Social del Cliente'), ('generic', 'A venta mostrador')],tracking=True)
    mostrar_venta_mostrador_rel = fields.Boolean(
        related='partner_id.mostrar_venta_mostrador',
        store=False
    )
    # INVOICING #
    
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        
        return {
            'generic_edi': True if self.tipo_de_timbrado == 'generic' else False,
            'ref': self.client_order_ref or '',
            'move_type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id._get_fiscal_position(self.partner_invoice_id)).id,
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_user_id': self.user_id.id,
            'payment_reference': self.reference,
            'transaction_ids': [Command.set(self.transaction_ids.ids)],
            'company_id': self.company_id.id,
            'invoice_line_ids': [],
            'user_id': self.user_id.id,
        }
    
    @api.depends('order_line')
    def compute_promo_text(self):
        for order in self:
            if not self.is_expo:
                x = order.create_draft_invoice()
                
                # Construimos el encabezado de la tabla HTML con thead
                html_content = """
                    <table class="table table-sm o_main_table table-borderless">
                        <thead>
                            <tr>
                                <th>Promoción</th>
                                <th>Bonificación</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                
                # Iteramos sobre los elementos para agregar filas a la tabla
                total_discount = 0
                for item in x:
                    if item:                
                        vals = item[2]
                        # Suponiendo que 'vals' contiene la información de la promoción
                        promo_name = vals.get('name', 'Promoción Desconocida')
                        price_unit = vals.get('price_unit', 0.0)
                        total_price = round(price_unit * 1.16, 2)
                        total_discount = total_discount + total_price
                        html_content += """
                            <tr>
                                <td>{promo_name}</td>
                                <td>$ {total_price:,.2f}</td>
                            </tr>
                        """.format(promo_name=promo_name, total_price=total_price)
                
                # Cerramos el cuerpo y la tabla HTML
                html_content += """
                        </tbody>
                    </table>
                """
                
                # Asignamos el HTML generado al campo calculado
                order.payment_promo_text = html_content
                order.bonificacion = total_discount
            else:
                order.payment_promo_text = ""
                order.bonificacion = ""
                
            
    def create_draft_invoice(self):
        if not self.is_expo:
            for order in self:
                # Datos básicos de la factura
                invoice_vals = {
                    'move_type': 'out_invoice',
                    'partner_id': order.partner_id.id,
                    'invoice_origin': order.name,
                    'currency_id': order.currency_id.id,
                    'invoice_user_id': order.user_id.id,
                    'invoice_date': fields.Date.context_today(self),
                    'invoice_line_ids': [],
                }

                # Creación de líneas de factura
                for line in order.order_line:
                    invoice_line_vals = {
                        'name': line.name,
                        'quantity': line.product_uom_qty,
                        'product_id': line.product_id.id,
                        'price_unit': line.price_unit,
                        'tax_ids': [(6, 0, line.tax_id.ids)],
                        'move_id': False,
                        'sale_line_ids': [(6, 0, line.ids)],
                        'discount': line.discount,
                    }
                    invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))

                # Crear factura
                invoice = self.env['account.move'].sudo().create(invoice_vals)
                # Relacionar la factura con el pedido de venta
                order.invoice_ids = [(4, invoice.id)]
            
            x = invoice.discount_increase(quotation=True)
            invoice.unlink()
            print(x)
            return x
        else:
            self.payment_promo_text = ""
            self.bonificacion = ""