from datetime import timedelta
from odoo import models, fields, api
import calendar
from datetime import datetime

class PaymentDiscountMixin(models.AbstractModel):
    _name = 'payment.discount.mixin'
    
    
    # region Volumen
    def get_row_values_descuento(self, record):
        """
        Obtiene los valores de descuento basados en el perfil financiero del cliente,
        el total de la factura/orden y el IVA.
        """
        descuentos = []
        if record.partner_id.financial_profile:
            shipping_with_taxes = self._calculate_without_shipping_price(record)
            descuentos_cliente = record.partner_id.financial_profile.line_ids
            for profile_line in descuentos_cliente:
                monto_descuento, fecha_vencimiento = self._calculate_discount(record, shipping_with_taxes, profile_line)
                descuentos.append((profile_line.discount, profile_line.upper_limit, fecha_vencimiento, monto_descuento))
        return descuentos
    
    def _calculate_discount(self, record, shipping_with_taxes, profile_line):
        discount = ((profile_line.discount / 100.0))
        BS = record.bs_nc_amount*1.16
        MT = record.amount_total
        ST = MT - BS - shipping_with_taxes
        NL = record.logistic_nc_amount*1.16
        MF = ST * discount
        TOTAL_PAGAR = ST - NL - MF + shipping_with_taxes
        
        if hasattr(record, 'invoice_line_ids'):
            fecha_vencimiento =  record.invoice_date + timedelta(days=profile_line.upper_limit)
            return TOTAL_PAGAR, fecha_vencimiento
        else:
            fecha_vencimiento = record.date_order + timedelta(days=profile_line.upper_limit)
            return TOTAL_PAGAR, fecha_vencimiento
    
    def compute_payment_discount_text(self, record):
        """
        Calcula el texto HTML para mostrar el descuento o monto a pagar en la factura/orden.
        """
        headers = ('Descuento', 'Dias de Pago', 'Fecha máxima', 'Cantidad a pagar')
        meses_espanol = self._get_months_in_spanish()
        rows = self.get_row_values_descuento(record)
        html = self._generate_html_financial_table(headers, rows, meses_espanol)
        return html

    def _get_months_in_spanish(self):
        """
        Devuelve un diccionario de los meses del año en inglés a español.
        """
        return {
            'January': 'enero', 'February': 'febrero', 'March': 'marzo', 'April': 'abril',
            'May': 'mayo', 'June': 'junio', 'July': 'julio', 'August': 'agosto',
            'September': 'septiembre', 'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre'
        }
    
    def _generate_html_financial_table(self, headers, rows, meses_espanol):
        """
        Genera el HTML de la tabla que contiene los descuentos.
        """
        html = '<table class="page-break1 table table-sm o_main_table table-borderless">'
        html += self._generate_table_headers(headers)
        html += self._generate_table_rows(rows, headers, meses_espanol)
        html += '</table>'
        return html

    def _generate_table_headers(self, headers):
        """
        Genera el encabezado de la tabla HTML.
        """
        return ''.join([f'<th>{header}</th>' for header in headers])
    
    def _generate_table_rows(self, rows, headers, meses_espanol):
        """
        Genera las filas de la tabla HTML con el formato adecuado.
        """
        html = ''
        for row in rows:
            html += '<tr>'
            for idx, cell in enumerate(row):
                html += f'<td>{self._format_cell(cell, idx, headers, meses_espanol)}</td>'
            html += '</tr>'
        return html

    def _format_cell(self, cell, cell_idx, headers, meses_espanol):
        """
        Formatea una celda según su tipo de dato.
        """
        if isinstance(cell, datetime):
            # Formatear fechas como "12 de abril de 2024"
            mes = meses_espanol[calendar.month_name[cell.month]]
            return f'{cell.day} de {mes} de {cell.year}'
        elif isinstance(cell, float):
            # Formatear como monto en formato moneda
            return f'${cell:,.2f}'
        elif isinstance(cell, int):
            # Formatear según el encabezado de la columna
            if headers[cell_idx] == 'Dias de Pago':
                return f'{cell} Días'
            return f'{cell}%'
        return cell
    # endregion
    
    #region NC BS
    def compute_nc_amount_bs(self, record):
        bridgestone_id = 2
        if hasattr(record, 'invoice_line_ids'):  # Es una factura
            sum_subtotal_lines = sum(record.invoice_line_ids.filtered(lambda line: line.product_id.product_tmpl_id.manufacturer_id.id == bridgestone_id and line.sale_line_ids.list_origin in ['MAYOREO']
                and line.product_id.id not in [50959]).mapped('price_subtotal'))
            return sum_subtotal_lines - (sum_subtotal_lines*.90)
        else:  # Es una orden de venta
            sum_subtotal_lines = sum(record.order_line.filtered(lambda line: line.product_id.product_tmpl_id.manufacturer_id.id == bridgestone_id and line.list_origin in ['MAYOREO']
                and line.product_id.id not in [50959]).mapped('price_subtotal') )
            return sum_subtotal_lines - (sum_subtotal_lines*.90)
    #endregion
    
    #region Logistic karen se agarro a  la kim y a la paty .--.      q abra pasado?
    def _get_logistic_amount(self,record,bs_nc_amount):
        amount = 0
        if hasattr(record, 'invoice_line_ids'):  # Es una factura
            
            filtered_lines = record.invoice_line_ids.filtered(
            lambda line: (
                line.sale_line_ids.list_origin in ['MAYOREO','PROMOCIÓN','PROMOCIÓN DOT']
                and line.product_id.id not in [50959]
            )
        )
            total_quantity = sum(record.invoice_line_ids.mapped('quantity'))
        else:
            filtered_lines = record.order_line.filtered(
            lambda line: (
                line.list_origin in ['MAYOREO','PROMOCIÓN','PROMOCIÓN DOT']
                and line.product_id.id not in [50959]
            )
        )
            total_quantity = sum(record.order_line.mapped('product_uom_qty'))
            
        applicable_discounts = self.env['discount_profiles.logistic.discount'].browse(record.partner_id.logistic_profile.id)
        f_disc = False
        f_disc_ids = []
        for discount_line in applicable_discounts:
            f_disc = False
            for line in discount_line.line_ids:
                if total_quantity >= line.lower_limit:
                    f_disc = line
                    f_disc_ids.append(f_disc)
        if f_disc_ids:
            discount = max(f_disc_ids, key=lambda x: x.discount).discount
            amount = (sum(filtered_lines.mapped('price_subtotal'))-bs_nc_amount) * (discount / 100)
        # Si no se encuentra un descuento exacto, se aplica el más alto disponible
        
        return amount

    #endregion
    def _calculate_without_shipping_price(self, record):
        """
        Calcula el total con IVA, dependiendo de si es una factura o una orden.
        """
        if hasattr(record, 'invoice_line_ids'):  # Es una factura
            subtotal_lines = record.invoice_line_ids.filtered(lambda line: line.product_id.id == 50959).mapped('price_subtotal')
            iva_amount = (sum(subtotal_lines) * 1.16) - sum(subtotal_lines)
        else:  # Es una orden de venta
            subtotal_lines = record.order_line.filtered(lambda line: line.product_id.id == 50959).mapped('price_subtotal')
            iva_amount = (sum(subtotal_lines) * 1.16) - sum(subtotal_lines)
        
        return sum(subtotal_lines) + iva_amount
    
    def _generate_html_table(self, bs_nc_amount, logistic_nc_amount):
        """Genera una tabla HTML para mostrar los montos calculados con formato de moneda solo si son mayores a 0."""
        
        # Formatear los montos con formato de moneda si son floats
        if isinstance(bs_nc_amount, float):
            bs_nc_amount = f'${bs_nc_amount:,.2f}'  # Formateamos como moneda, 2 decimales
        if isinstance(logistic_nc_amount, float):
            logistic_nc_amount = f'${logistic_nc_amount:,.2f}'  # Formateamos como moneda, 2 decimales
        
        # Iniciar la tabla HTML
        html_content = """
        <table class="table">
            <thead>
                <tr>
                    <th>Descripción</th>
                    <th>Monto</th>
                </tr>
            </thead>
            <tbody>"""
        
        # Solo agregar el renglón para Bridgestone si el monto es mayor a 0
        if isinstance(bs_nc_amount, str) and float(bs_nc_amount.strip('$').replace(',', '')) > 0:
            html_content += f"""
            <tr>
                <td>Bridgestone</td>
                <td>{bs_nc_amount}</td>
            </tr>"""
        
        # Solo agregar el renglón para Logístico si el monto es mayor a 0
        if isinstance(logistic_nc_amount, str) and float(logistic_nc_amount.strip('$').replace(',', '')) > 0:
            html_content += f"""
            <tr>
                <td>Logístico</td>
                <td>{logistic_nc_amount}</td>
            </tr>"""
        
        # Cerrar la tabla HTML
        html_content += """
            </tbody>
        </table>"""
        
        return html_content

    


    
 