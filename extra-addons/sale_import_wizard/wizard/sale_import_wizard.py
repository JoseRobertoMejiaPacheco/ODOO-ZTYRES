# -*- coding: utf-8 -*-
import base64
import io
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    openpyxl = None


class SaleImportWizardLine(models.TransientModel):
    _name = 'sale.import.wizard.line'
    _description = 'Linea de importacion de pedido'

    wizard_id        = fields.Many2one('sale.import.wizard', ondelete='cascade')
    product_code     = fields.Char(string='Codigo', readonly=True)
    product_id       = fields.Many2one('product.product', string='Producto', readonly=True)
    product_name     = fields.Char(string='Nombre Producto', readonly=True)
    product_found    = fields.Boolean(readonly=True)
    qty              = fields.Float(string='Cantidad', readonly=True, digits='Product Unit of Measure')
    price_unit_excel = fields.Float(string='Precio Excel', readonly=True, digits='Product Price')
    price_unit_list  = fields.Float(string='Precio Lista', readonly=True, digits='Product Price')
    price_unit_final = fields.Float(string='Precio Final', readonly=True, digits='Product Price')
    subtotal         = fields.Float(string='Subtotal', compute='_compute_subtotal', digits='Product Price')
    tax_amount       = fields.Float(string='Impuestos', compute='_compute_subtotal', digits='Product Price')
    total            = fields.Float(string='Total', compute='_compute_subtotal', digits='Product Price')
    pricelist_used   = fields.Char(string='Fuente', readonly=True)
    error_msg        = fields.Char(string='Error', readonly=True)
    include          = fields.Boolean(string='Incluir', default=True)

    @api.depends('qty', 'price_unit_final', 'product_id', 'include')
    def _compute_subtotal(self):
        for line in self:
            sub = line.qty * line.price_unit_final
            line.subtotal = sub
            taxes = line.product_id.taxes_id
            if taxes:
                tax_result = taxes.compute_all(
                    line.price_unit_final,
                    quantity=line.qty,
                    product=line.product_id,
                )
                line.tax_amount = tax_result['total_included'] - tax_result['total_excluded']
                line.total = tax_result['total_included']
            else:
                line.tax_amount = 0.0
                line.total = sub


class SaleImportWizard(models.TransientModel):
    _name = 'sale.import.wizard'
    _description = 'Wizard Importacion Pedido de Venta'

    partner_id     = fields.Many2one('res.partner', string='Cliente', required=True,
                                     domain=[('customer_rank', '>', 0)])
    pricelist_id   = fields.Many2one('product.pricelist', string='Lista de Precio')
    invoice_policy = fields.Selection([
        ('order',    'Cantidad Pedida'),
        ('delivery', 'Cantidad Entregada'),
    ], string='Politica de Facturacion', required=True, default='delivery')

    excel_file     = fields.Binary(string='Archivo Excel', attachment=False)
    excel_filename = fields.Char()

    line_ids       = fields.One2many('sale.import.wizard.line', 'wizard_id', string='Lineas')
    has_errors     = fields.Boolean(compute='_compute_totals')

    total_subtotal = fields.Float(string='Subtotal', compute='_compute_totals', digits='Product Price')
    total_taxes    = fields.Float(string='Impuestos', compute='_compute_totals', digits='Product Price')
    total_total    = fields.Float(string='Total', compute='_compute_totals', digits='Product Price')

    state = fields.Selection([
        ('step1', 'Paso 1'),
        ('step2', 'Paso 2'),
        ('step3', 'Paso 3'),
    ], default='step1')

    @api.depends('line_ids.subtotal', 'line_ids.tax_amount', 'line_ids.total',
                 'line_ids.include', 'line_ids.product_found', 'line_ids.error_msg')
    def _compute_totals(self):
        for rec in self:
            included = rec.line_ids.filtered(lambda l: l.include and l.product_found)
            rec.total_subtotal = sum(included.mapped('subtotal'))
            rec.total_taxes    = sum(included.mapped('tax_amount'))
            rec.total_total    = sum(included.mapped('total'))
            rec.has_errors = any(not l.product_found or l.error_msg for l in rec.line_ids)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id and self.partner_id.property_product_pricelist:
            self.pricelist_id = self.partner_id.property_product_pricelist

    def action_next_step1(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('Debe seleccionar un cliente.'))
        self.write({'state': 'step2'})
        return self._reopen_step('step2')

    def action_back_step2(self):
        self.write({'state': 'step1'})
        return self._reopen_step('step1')

    def action_parse_excel(self):
        self.ensure_one()
        if not self.excel_file:
            raise UserError(_('Debe adjuntar un archivo Excel (.xlsx).'))
        if openpyxl is None:
            raise UserError(_('La libreria openpyxl no esta instalada.\nEjecute: pip install openpyxl'))

        self.line_ids.unlink()
        file_data = base64.b64decode(self.excel_file)
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_data), data_only=True)
        except Exception as e:
            raise UserError(_('No se pudo leer el archivo: %s') % str(e))

        ws = wb.active
        lines_vals = []

        for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or all(v is None for v in row):
                continue

            product_code = str(row[0]).strip() if row[0] is not None else ''
            try:
                qty = float(row[1]) if row[1] is not None else 0.0
            except (ValueError, TypeError):
                qty = 0.0
            try:
                price_excel = float(row[2]) if row[2] is not None else 0.0
            except (ValueError, TypeError):
                price_excel = 0.0

            if not product_code:
                continue

            product = self.env['product.product'].search(
                [('default_code', '=', product_code)], limit=1)
            if not product:
                product = self.env['product.product'].search(
                    [('barcode', '=', product_code)], limit=1)

            product_found = bool(product)
            error_msg = '' if product_found else 'Producto no encontrado'

            price_list = 0.0
            pricelist_name = ''
            if product_found:
                if self.pricelist_id:
                    price_list = self.pricelist_id._get_product_price(
                        product, qty or 1.0,
                        uom=product.uom_id,
                        date=fields.Date.today(),
                    )
                    pricelist_name = self.pricelist_id.name
                else:
                    price_list = product.lst_price
                    pricelist_name = 'Precio venta'

            price_final = price_list if price_excel == 0.0 else price_excel
            fuente = pricelist_name if price_excel == 0.0 else 'Excel'

            lines_vals.append({
                'wizard_id':        self.id,
                'product_code':     product_code,
                'product_id':       product.id if product_found else False,
                'product_name':     product.name if product_found else '',
                'product_found':    product_found,
                'qty':              qty,
                'price_unit_excel': price_excel,
                'price_unit_list':  price_list,
                'price_unit_final': price_final,
                'pricelist_used':   fuente,
                'error_msg':        error_msg,
                'include':          product_found,
            })

        if not lines_vals:
            raise UserError(_('El Excel no contiene datos validos (desde fila 2).'))

        self.env['sale.import.wizard.line'].create(lines_vals)
        self.write({'state': 'step3'})
        return self._reopen_step('step3')

    def action_back_step3(self):
        self.write({'state': 'step2'})
        return self._reopen_step('step2')

    def action_export_excel(self):
        self.ensure_one()
        if openpyxl is None:
            raise UserError(_('La libreria openpyxl no esta instalada.'))

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Cotizacion'

        header_font = Font(bold=True, color='FFFFFF', size=11)
        header_fill = PatternFill('solid', fgColor='1F4E79')
        total_fill  = PatternFill('solid', fgColor='D6E4F0')
        total_font  = Font(bold=True, size=11)
        center      = Alignment(horizontal='center', vertical='center')
        right       = Alignment(horizontal='right', vertical='center')
        thin        = Side(style='thin', color='AAAAAA')
        border      = Border(left=thin, right=thin, top=thin, bottom=thin)
        money_fmt   = '#,##0.00'
        qty_fmt     = '#,##0.##'

        company = self.env.company

        ws.merge_cells('A1:L1')
        ws['A1'] = company.name
        ws['A1'].font = Font(bold=True, size=14, color='1F4E79')
        ws['A1'].alignment = center

        ws.merge_cells('A2:L2')
        ws['A2'] = 'Cliente: %s' % self.partner_id.name
        ws['A2'].font = Font(bold=True, size=11)
        ws['A2'].alignment = Alignment(horizontal='left')

        ws.merge_cells('A3:L3')
        lista = self.pricelist_id.name if self.pricelist_id else 'Sin lista'
        politica_map = {'order': 'Cantidad Pedida', 'delivery': 'Cantidad Entregada'}
        politica = politica_map.get(self.invoice_policy, '')
        ws['A3'] = 'Lista de precio: %s   |   Politica: %s' % (lista, politica)
        ws['A3'].font = Font(italic=True, size=10, color='555555')
        ws['A3'].alignment = Alignment(horizontal='left')

        ws.row_dimensions[4].height = 6

        headers = ['#', 'Codigo', 'Producto', 'Cantidad', 'Disponible', 'Pedido 1 (con stock)', 'Pedido 2 (sin stock)', 'Queda', 'Precio Unitario', 'Subtotal', 'Impuestos', 'Total']
        widths  = [5,    14,       40,          12,          14,            20,                   20,                    12,      18,               16,          14,           16]

        for col, (h, w) in enumerate(zip(headers, widths), start=1):
            cell = ws.cell(row=5, column=col, value=h)
            cell.font      = header_font
            cell.fill      = header_fill
            cell.alignment = center
            cell.border    = border
            ws.column_dimensions[get_column_letter(col)].width = w

        ws.row_dimensions[5].height = 22

        lines = self.line_ids.filtered(lambda l: l.include and l.product_found)
        alt_fill = PatternFill('solid', fgColor='EBF3FB')

        for idx, line in enumerate(lines, start=1):
            row = 5 + idx
            fill = alt_fill if idx % 2 == 0 else PatternFill()
            nombre = line.product_name or (line.product_id.name if line.product_id else '')
            disponible = self._get_product_available_qty(line.product_id) if line.product_id else 0.0
            disponible_pos = max(disponible, 0.0)
            se_reserva = min(line.qty, disponible_pos)
            pendiente  = max(line.qty - disponible_pos, 0.0)
            queda      = max(disponible_pos - line.qty, 0.0)
            data = [idx, line.product_code, nombre, line.qty,
                    disponible, se_reserva, pendiente, queda,
                    line.price_unit_final, line.subtotal, line.tax_amount, line.total]
            for col, val in enumerate(data, start=1):
                cell = ws.cell(row=row, column=col, value=val)
                cell.border = border
                cell.fill   = fill
                if col == 1:
                    cell.alignment = center
                elif col in range(4, 13):
                    cell.alignment = right
                    if col in (4, 5, 6, 7, 8):
                        cell.number_format = qty_fmt
                    else:
                        cell.number_format = money_fmt
                # Colores segun disponibilidad
                if col == 5:  # Disponible
                    if disponible <= 0:
                        cell.font = Font(bold=True, color='C00000')
                    elif disponible < line.qty:
                        cell.font = Font(color='C55A11')
                elif col == 6 and se_reserva > 0:  # Pedido 1
                    cell.font = Font(color='375623')
                elif col == 7 and pendiente > 0:   # Pedido 2
                    cell.font = Font(bold=True, color='C00000')

        total_row = 5 + len(lines) + 2
        labels = {10: self.total_subtotal, 11: self.total_taxes, 12: self.total_total}
        for col in range(1, 13):
            cell = ws.cell(row=total_row, column=col)
            cell.fill   = total_fill
            cell.font   = total_font
            cell.border = border
            if col == 9:
                cell.value     = 'TOTALES'
                cell.alignment = right
            elif col in labels:
                cell.value         = labels[col]
                cell.number_format = money_fmt
                cell.alignment     = right

        ws.row_dimensions[total_row].height = 22
        ws.freeze_panes = 'A6'

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        xls_data = base64.b64encode(output.read())

        filename = 'cotizacion_%s_%s.xlsx' % (self.partner_id.name, fields.Date.today())
        attachment = self.env['ir.attachment'].create({
            'name':     filename,
            'type':     'binary',
            'datas':    xls_data,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type':   'ir.actions.act_url',
            'url':    '/web/content/%d?download=true' % attachment.id,
            'target': 'new',
        }

    def _get_product_available_qty(self, product):
        """Retorna la cantidad libre (sin reservar) del producto.
        Usa qty_available (stock fisico real) menos outgoing_qty (reservas existentes).
        Esto evita tomar stock pronosticado o recepciones pendientes.
        """
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1
        )
        product_ctx = product.with_context(warehouse=warehouse.id)
        # qty_available = stock fisico en mano
        # outgoing_qty  = cantidad ya reservada en otros pickings
        # free_qty      = qty_available - outgoing_qty
        return product_ctx.free_qty

    def _create_order_lines(self, order, lines):
        """Crea las lineas de un pedido de venta.
        lines: lista de dicts {line: SaleImportWizardLine, qty: float}
        """
        SaleLine = self.env['sale.order.line'].with_context(check_availability=False)
        for item in lines:
            line = item['line']
            qty  = item['qty']
            sol = SaleLine.create({
                'order_id':        order.id,
                'product_id':      line.product_id.id,
                'product_uom_qty': qty,
                'price_unit':      line.price_unit_final,
                'product_uom':     line.product_id.uom_id.id,
            })
            sol.with_context(check_availability=False).write(
                {'invoice_policy_override': self.invoice_policy})

    def action_create_sale_order(self):
        self.ensure_one()
        lines_ok = self.line_ids.filtered(lambda l: l.include and l.product_found)
        if not lines_ok:
            raise UserError(_('No hay lineas validas seleccionadas para importar.'))

        order_vals = {
            'partner_id':              self.partner_id.id,
            'pricelist_id':            self.pricelist_id.id if self.pricelist_id else False,
            'invoice_policy_override': self.invoice_policy,
            'unlock_financial':True
        }
        # Usar with_context en el env para evitar slowness del chatter al crear
        SaleOrder = self.env['sale.order'].with_context(
            mail_notrack=True,
            mail_auto_subscribe_no_notify=True,
            tracking_disable=True,
        )

        # Clasificar lineas con split de cantidad:
        #   Si disponible >= qty        → va completo al pedido 1
        #   Si 0 < disponible < qty     → se parte: disponible al pedido 1, resto al pedido 2
        #   Si disponible <= 0          → va completo al pedido 2
        #
        # Cada entrada es un dict con {line, qty} para manejar cantidades parciales
        lines_with_stock    = []  # [{line, qty}]
        lines_without_stock = []  # [{line, qty}]

        for line in lines_ok:
            available = self._get_product_available_qty(line.product_id)
            available = max(available, 0.0)

            if available <= 0:
                # Sin stock: todo al pedido 2, sin split
                lines_without_stock.append({'line': line, 'qty': line.qty})
            elif available >= line.qty:
                # Stock suficiente: todo al pedido 1
                lines_with_stock.append({'line': line, 'qty': line.qty})
            else:
                # Stock parcial: split — disponible al pedido 1, resto al pedido 2
                lines_with_stock.append({'line': line, 'qty': available})
                lines_without_stock.append({'line': line, 'qty': line.qty - available})

        created_orders = []

        # ── Pedido 1: productos con algo de stock (en BORRADOR) ───────────
        if lines_with_stock:
            order1 = SaleOrder.create(order_vals)
            self._create_order_lines(order1, lines_with_stock)
            created_orders.append(order1)

        # ── Pedido 2: sin stock (en BORRADOR) ───────────────────────────────
        if lines_without_stock:
            order_vals2 = dict(order_vals)
            order_vals2['note'] = (
                'Pedido pendiente: sin inventario al importar. '
                'Confirmar cuando haya stock.'
            )
            order2 = SaleOrder.create(order_vals2)
            self._create_order_lines(order2, lines_without_stock)
            created_orders.append(order2)

        # ── Resultado ───────────────────────────────────────────────────────
        if len(created_orders) == 1:
            return {
                'type':      'ir.actions.act_window',
                'res_model': 'sale.order',
                'res_id':    created_orders[0].id,
                'view_mode': 'form',
                'target':    'current',
            }

        return {
            'type':      'ir.actions.act_window',
            'name':      'Pedidos Importados',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain':    [('id', 'in', [o.id for o in created_orders])],
            'target':    'current',
        }

    def _reopen_step(self, step):
        view_map = {
            'step1': 'sale_import_wizard.view_sale_import_wizard_step1',
            'step2': 'sale_import_wizard.view_sale_import_wizard_step2',
            'step3': 'sale_import_wizard.view_sale_import_wizard_step3',
        }
        view_id = self.env.ref(view_map[step]).id
        return {
            'type':      'ir.actions.act_window',
            'res_model': self._name,
            'res_id':    self.id,
            'view_mode': 'form',
            'view_id':   view_id,
            'target':    'new',
            'context':   self.env.context,
        }
