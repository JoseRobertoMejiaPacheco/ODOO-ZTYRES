#-*- coding: utf-8 -*-

from odoo import models, fields, api,_
from odoo.exceptions import UserError,ValidationError
import re
CUSTOM_NUMBERS_PATTERN = re.compile(r'[0-9]{2}  [0-9]{2}  [0-9]{4}  [0-9]{7}')
import logging
_logger = logging.getLogger(__name__)

def _format_pedimento(digits: str) -> str:
    digits = re.sub(r'\D', '', digits)  # limpiar espacios o caracteres no numéricos
    if len(digits) == 18:
        a, b, c, d, e = digits[:2], digits[2:4], digits[4:8], digits[8:15], digits[15:18]
        return f"{a}  {b}  {c}  {d}  {e}"
    elif len(digits) == 15:
        a, b, c, d = digits[:2], digits[2:4], digits[4:8], digits[8:15]
        return f"{a}  {b}  {c}  {d}"

def _only_digits(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())

class SupplyChainReceiptLocation(models.Model):
    _name = 'supply_chain_receipt.location'
    _rec_name = 'display_name'

    # Vínculo con el padre (obligatorio y en cascada)
    receipt_line_id = fields.Many2one(
        'supply_chain_receipt.receipt_line',
        string='Línea de Recepción',
        required=True,
        ondelete='cascade',
    )

    # Conveniencia: producto heredado del padre (sin contexto)
    product_id = fields.Many2one(
        'product.product',
        related='receipt_line_id.product_id',
        store=True, readonly=True,
    )

    # Captura rápida: "UBICACION AÑO CANTIDAD" (ej. "1-A-1 2025 50")
    entry_text = fields.Char(
        string='Captura rápida',
        help="Formato: 'Ubicación Año Cantidad' (ej. '1-A-1 2025 50'). "
             "La ubicación puede tener espacios; el año debe tener 4 dígitos > 2000."
    )

    location_id = fields.Many2one('stock.location', string='Ubicación')
    lot_id = fields.Many2one('stock.lot', string='Lote')
    product_uom_qty = fields.Float(string='Demanda')

    display_name = fields.Char(
        compute='_compute_display_name',
        store=True
    )

    # ----------------- Helpers -----------------

    @api.depends('location_id', 'product_uom_qty', 'lot_id')
    def _compute_display_name(self):
        for r in self:
            loc = r.location_id.name or 'Sin ubicación'
            lot = r.lot_id.name or ''
            qty = r.product_uom_qty or 0.0
            r.display_name = f'{loc} {lot} {qty:g}'

    def _parse_entry_text(self, text):
        """Devuelve (location, lot_str, qty). Acepta:
           UBICACION AÑO CANTIDAD  |  UBICACION CANTIDAD AÑO
           (deduce el año de 4 dígitos > 2000)
        """
        text = (text or '').strip()
        if not text:
            raise UserError(_("Captura rápida vacía. Usa 'Ubicación Año Cantidad' (ej. '1-A-1 2025 50')."))

        tokens = text.split()
        if len(tokens) < 3:
            raise UserError(_("Formato inválido. Usa 'Ubicación Año Cantidad' (ej. '1-A-1 2025 50')."))

        # La ubicación puede contener espacios → todo menos los 2 últimos tokens
        location_str = ' '.join(tokens[:-2]).strip()
        t2, t3 = tokens[-2].strip(), tokens[-1].strip()

        def _is_year4(s):
            return s.isdigit() and len(s) == 4 and int(s) > 2000

        def _to_float(s):
            try:
                return float(s.replace(',', ''))
            except Exception:
                raise ValidationError(_("La cantidad debe ser numérica."))
        
        # Deducción flexible (año ↔ cantidad)
        if _is_year4(t2):
            lot_str, qty = t2, _to_float(t3)
        elif _is_year4(t3):
            lot_str, qty = t3, _to_float(t2)
        else:
            # Por defecto, exigimos que el penúltimo sea año válido
            if not _is_year4(t2):
                raise ValidationError(_("El lote debe ser un año de 4 dígitos mayor a 2000 (ej. 2025)."))
            lot_str, qty = t2, _to_float(t3)

        if qty <= 0:
            raise UserError(_("La cantidad debe ser mayor a cero."))

        # Buscar ubicación por name o complete_name
        Location = self.env['stock.location']
        location = Location.search(['|', ('name', '=', location_str), ('complete_name', '=', location_str)], limit=1)
        if not location:
            raise ValidationError(_("Ubicación '%s' no encontrada.") % location_str)

        return location, lot_str, qty
    
    # ----------------- Flujo UI (formulario) -----------------

    @api.onchange('entry_text')
    def _onchange_entry_text(self):
        if not self.entry_text:
            return
        location, lot_str, qty = self._parse_entry_text(self.entry_text)

        product = self.receipt_line_id.product_id
        if not product:
            raise UserError(_("No se pudo inferir el producto desde la línea padre."))
        
        lot = self.env['stock.lot'].search([
            ('name', '=', lot_str),
            ('product_id', '=', product.id)
        ], limit=1)
        if not lot:
            lot = self.env['stock.lot'].create({
                'name': lot_str,
                'product_id': product.id,
                'company_id': self.env.company.id,
            })

        self.location_id = location
        self.lot_id = lot
        self.product_uom_qty = qty
        # Opcional: limpiar la captura tras parsear
        # self.entry_text = False

    # ----------------- Fallback (API/Import) -----------------

    @api.model_create_multi
    def create(self, vals_list):
        """Si llegan registros por import/API con 'entry_text' pero sin campos resueltos,
        parseamos aquí para no depender de onchanges del cliente."""
        for vals in vals_list:
            needs_parse = vals.get('entry_text') and not (
                vals.get('location_id') and vals.get('lot_id') and vals.get('product_uom_qty')
            )
            if needs_parse:
                location, lot_str, qty = self._parse_entry_text(vals['entry_text'])
                parent = self.env['supply_chain_receipt.receipt_line'].browse(vals.get('receipt_line_id'))
                product = parent.product_id
                if not product:
                    raise UserError(_("No se pudo inferir el producto desde la línea padre."))

                lot = self.env['stock.lot'].search([
                    ('name', '=', lot_str),
                    ('product_id', '=', product.id)
                ], limit=1)
                if not lot:
                    lot = self.env['stock.lot'].create({
                        'name': lot_str,
                        'product_id': product.id,
                        'company_id': self.env.company.id,
                    })
                vals.update({
                    'location_id': location.id,
                    'lot_id': lot.id,
                    'product_uom_qty': qty,
                })
                _logger.info("[ENTRY_TEXT] loc=%s lot=%s qty=%s prod=%s parent=%s",
                             location.display_name, lot.name, qty, product.display_name, parent.id)
        return super().create(vals_list)

class supply_chain_receipt_line(models.Model):
    _name = 'supply_chain_receipt.receipt_line'
    _sql_constraints = [
        ('unique_stock_move_id', 'unique(stock_move_id)', 'El movimiento ya está asignado a otra línea de recepción.')
    ]
    stock_move_id = fields.Many2one(comodel_name='stock.move', string='Movimiento')
    product_id = fields.Many2one(comodel_name='product.product', string='Movimiento')
    product_uom_qty = fields.Float(string='Demanda')
    purchase_line_id = fields.Many2one(comodel_name='purchase.order.line', string='Linea de Compra')
    quantity_done = fields.Float(string='Hecho')    
    location_ids = fields.One2many(comodel_name='supply_chain_receipt.location', inverse_name='receipt_line_id',ondelete='cascade', string='Ubicaciones WH')
    receipt_id = fields.Many2one(comodel_name='supply_chain_receipt.receipt')
    qty_to_move = fields.Integer(compute='_compute_qty_to_move', string='Cantidad a Ingresar',store=True)
    purchase_id = fields.Many2one(comodel_name='purchase.order',related='purchase_line_id.order_id', string='Pedido', store=True)
    l10n_mx_edi_pedimento_number = fields.Char(string='Pedimento')
    
    def open_wizard_add_location(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Agregar Ubicaciones',
            'res_model': 'supply_chain_receipt.add_location_wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_receipt_line_id': self.id,
            },
        }
    
    # -------- Normalización en create/write (NO en constrains) --------
    
    def create(self, vals_list):
        for vals in vals_list:
            if 'l10n_mx_edi_pedimento_number' in vals and vals['l10n_mx_edi_pedimento_number']:
                digits = _only_digits(vals['l10n_mx_edi_pedimento_number'])
                formatted = _format_pedimento(digits)
                if not CUSTOM_NUMBERS_PATTERN.match(formatted):
                    # En teoría no pasa si _format_pedimento no falló
                    raise ValidationError(_("Formato de pedimento inválido."))
                vals['l10n_mx_edi_pedimento_number'] = formatted
        return super().create(vals_list)
    
    def write(self, vals):
        if 'l10n_mx_edi_pedimento_number' in vals:
            raw = vals.get('l10n_mx_edi_pedimento_number')
            if raw:
                digits = _only_digits(raw)
                formatted = _format_pedimento(digits)
                if not CUSTOM_NUMBERS_PATTERN.match(formatted):
                    raise ValidationError(_("Formato de pedimento inválido."))
                vals['l10n_mx_edi_pedimento_number'] = formatted
            else:
                # Permitir limpiar el campo (False/None) sin validar
                vals['l10n_mx_edi_pedimento_number'] = False
        self.location_ids.search([('receipt_line_id','=',False)]).unlink()                
        return super().write(vals)
    
    # -------- Constraint SOLO valida, NO escribe --------
    # @api.constrains('l10n_mx_edi_pedimento_number')
    # def _check_l10n_mx_edi_pedimento_number(self):
    #     for rec in self:
    #         if not rec.l10n_mx_edi_pedimento_number:
    #             continue
    #         if not CUSTOM_NUMBERS_PATTERN.match(rec.l10n_mx_edi_pedimento_number.strip()):
    #             raise ValidationError(_(
    #                 "Error: el formato del pedimento es incorrecto.\n\n"
    #                 "Ejemplo: 15  48  3009  0001234"
    #             ))
    # (Opcional) UX: autoformatear en el cliente cuando ya hay 15 dígitos
    @api.onchange('l10n_mx_edi_pedimento_number')
    def _onchange_l10n_mx_edi_pedimento_number(self):
        raw = self.l10n_mx_edi_pedimento_number
        if not raw:
            return
        digits = _only_digits(raw)
        if len(digits) == 15:
            try:
                self.l10n_mx_edi_pedimento_number = _format_pedimento(digits)
            except ValidationError:
                # No rompas la UX en onchange; deja que el constraint server-side valide
                pass
    
    @api.depends('location_ids')
    def _compute_qty_to_move(self):
        for record in self:
            record.qty_to_move = sum(record.location_ids.mapped('product_uom_qty'))
            if record.qty_to_move > record.quantity_done:
                raise UserError(f'No se pueden avanzar más llantas de las que hay en tránsito {record.qty_to_move} es mayor a {record.quantity_done}')

    
import logging

_logger = logging.getLogger(__name__)


class supply_chain_receipt(models.Model):
    _name = 'supply_chain_receipt.receipt'
    _description = 'supply_chain_receipt.supply_chain_receipt'
    
    name = fields.Char()
    date = fields.Date(string='Fecha')
    arrive_date = fields.Date(string='Fecha de arribo')
    transit_picking_ids = fields.Many2many(
        comodel_name='stock.picking',
        relation='supply_receipt_transit_picking_rel',
        string='Transito'
    )
    warehouse_picking_ids = fields.Many2many(
        comodel_name='stock.picking',
        relation='supply_receipt_warehouse_picking_rel',
        string='Almacen'
    )
    total_warehouse_qty = fields.Integer(
        compute='_compute_total_warehouse_qty',
        string='Total en almacen'
    )
    total_transit_qty = fields.Integer(
        compute='_compute_total_transit_qty',
        string='Total en tránsito'
    )
    remaining_warehouse_qty = fields.Integer(
        compute='_compute_remaining_warehouse_qty',
        string='Por Avanzar a almacen'
    )
    total_invoiced_qty = fields.Float(
        compute='_compute_total_invoiced_qty',
        digits=(16, 2),
        string='Cantidad Facturada'
    )
    receipt_line_ids = fields.One2many(
        comodel_name='supply_chain_receipt.receipt_line',
        inverse_name='receipt_id'
    )
    group_ids = fields.Many2many(
        'procurement.group',
        compute='_compute_group_ids',
        string='Grupos de procura'
    )
    picking_type_id = fields.Many2one(
        compute='_compute_picking_type_id',
        comodel_name='stock.picking.type',
        string='Tipo de Operación'
    )
    location_id = fields.Many2one(
        compute='_compute_location_id',
        comodel_name='stock.location',
        string='Ubicación Origen'
    )
    location_dest_id = fields.Many2one(
        compute='_compute_location_dest_id',
        comodel_name='stock.location',
        string='Almacén destino'
    )
    purchase_ids = fields.Many2many(
        comodel_name='purchase.order',
        string='Órdenes de compra'
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Proveedor'
    )
    invoice_ids = fields.Many2many(
        comodel_name='account.move',
        string='Facturas'
    )
    count_invoice_ids = fields.Integer(
        string="Count Notas de Crédito",
        compute="_compute_count_invoice_ids"
    )
    
    @api.depends('invoice_ids')
    def _compute_total_invoiced_qty(self):
        for record in self:
            record.total_invoiced_qty = sum(
                record.invoice_ids.invoice_line_ids.filtered(
                    lambda l: l.product_id.type == 'product' and l.display_type == 'product'
                ).mapped('quantity')
            )
    
    @api.depends('invoice_ids')
    def _compute_count_invoice_ids(self):
        for record in self:
            domain = [('id', 'in', record.invoice_ids.ids)]
            record.count_invoice_ids = self.env['account.move'].search_count(domain)
    
    def action_open_line_ids(self):
        """Retorna la acción para visualizar las facturas en modo solo lectura."""
        self.ensure_one()
        action = self.env.ref('account.action_move_in_invoice_type').sudo().read()[0]
        action['domain'] = [('move_type', '=', 'in_invoice'), (['id', 'in', self.invoice_ids.ids])]
        action['context'] = dict(
            no_create=True,
            no_edit=True,
            no_delete=True
        )
        return action
    
    @api.depends('warehouse_picking_ids')
    def _compute_total_transit_qty(self):
        for record in self:
            pickings_done = record.transit_picking_ids.filtered(lambda x: x.state == 'done')
            qty_done = sum(pickings_done.mapped('move_ids_without_package').mapped('quantity_done'))
            record.total_transit_qty = qty_done
    
    @api.depends('warehouse_picking_ids')
    def _compute_total_warehouse_qty(self):
        for record in self:
            pickings_done = record.warehouse_picking_ids.filtered(lambda x: x.state == 'done')
            qty_done = sum(pickings_done.mapped('move_ids_without_package').mapped('quantity_done'))
            record.total_warehouse_qty = qty_done
    
    @api.depends('warehouse_picking_ids')
    def _compute_remaining_warehouse_qty(self):
        for record in self:
            record.remaining_warehouse_qty = record.total_transit_qty - record.total_warehouse_qty
    
    @api.depends('transit_picking_ids')
    def _compute_location_dest_id(self):
        for record in self:
            locations = record.transit_picking_ids.mapped('location_dest_id')
            if len(locations) == 1:
                record.location_dest_id = 8  # WH
            else:
                record.location_dest_id = False
    
    @api.depends('transit_picking_ids')
    def _compute_location_id(self):
        for record in self:
            locations = record.transit_picking_ids.mapped('location_dest_id')
            
            # Si todos son iguales (solo hay 1 valor único en el set)
            if len(locations) == 1:
                record.location_id = locations[0]  # Usa el valor único encontrado
            elif len(locations) > 1:
                # Hay valores diferentes, lanzar error
                raise ValidationError(
                    "Todos los pickings deben tener la misma Ubicación de Origen. "
                    f"Se encontraron: {', '.join(locations.mapped('complete_name'))}"
                )
            else:
                # No hay pickings
                record.location_id = False
        
    @api.depends('transit_picking_ids')
    def _compute_picking_type_id(self):
        for record in self:
            picking_types = record.transit_picking_ids.mapped('picking_type_id')
            
            # Si todos son iguales (solo hay 1 valor único en el set)
            if len(picking_types) == 1:
                record.picking_type_id = picking_types[0]
            elif len(picking_types) > 1:
                # Hay valores diferentes, lanzar error
                raise ValidationError(
                    "Todos los pickings deben tener el mismo Tipo de Operación. "
                    f"Se encontraron: {', '.join(picking_types.mapped('name'))}"
                )
            else:
                # No hay pickings
                record.picking_type_id = False
    
    @api.depends('purchase_ids')
    def _compute_group_ids(self):
        for rec in self:
            rec.group_ids = rec.purchase_ids.mapped('group_id').filtered(lambda g: g)
    
    def unreserve_product(self, product_ids, picking_id=None):
        """Libera la reserva de productos."""
        StockMove = self.env['stock.move']
        
        domain = [
            ('product_id', 'in', product_ids),
            ('state', '=', 'assigned'),
            ('location_dest_id.usage', '=', 'internal'),
        ]
        
        if picking_id:
            domain.append(('picking_id', '=', picking_id))
        
        moves = StockMove.search(domain)
        
        if moves:
            moves.picking_id.do_unreserve()
    
    def create_invoice(self):
        """Crea factura basada en los pickings de tránsito."""
        for record in self:
            # Buscar órdenes relacionadas
            purchase_orders = self.env['purchase.order'].search([
                ('group_id', 'in', record.transit_picking_ids.mapped('group_id').ids)
            ])
            
            # Crear factura
            action = purchase_orders.action_create_invoice()
            invoice_id = action.get('res_id')
            if not invoice_id:
                return
            
            invoice = self.env['account.move'].browse(invoice_id)
            
            # Borrar líneas anteriores
            invoice.invoice_line_ids.unlink()
            
            # Obtener líneas desde pickings
            product_lines = record._get_product_qty()
            
            # Agregar nuevas líneas
            new_lines = []
            for line in product_lines:
                new_lines.append((0, 0, {
                    'product_id': line['product_id'],
                    'quantity': line['quantity'],
                    'product_uom_id': line['uom_id'],
                    'price_unit': line['price_unit'],
                    'tax_ids': line['tax_ids'],
                    'name': line['name'],
                    'purchase_line_id': line['purchase_line_id'],
                }))
            
            invoice.write({'invoice_line_ids': new_lines})
            record.invoice_ids = [(6, 0, invoice.ids)]
            
            return invoice
    
    def _get_product_qty(self):
        """Obtiene cantidades de productos desde transit_picking_ids."""
        data = []
        for record in self:
            lines = record.transit_picking_ids.mapped('move_ids_without_package')
            for move in lines:
                if move.product_id and move.quantity_done > 0 and move.purchase_line_id:
                    data.append({
                        'product_id': move.product_id.id,
                        'quantity': move.quantity_done,
                        'uom_id': move.product_uom.id,
                        'price_unit': move.purchase_line_id.price_unit,
                        'tax_ids': [(6, 0, move.purchase_line_id.taxes_id.ids)],
                        'name': move.name,
                        'purchase_line_id': move.purchase_line_id.id,
                    })
        return data
    
    def _generate_dict_stock_picking_values(self):
        """
        FLUJO MANUAL DE ODOO 16: Simula el proceso manual exacto
        
        Diferencias clave en Odoo 16:
        - product_uom_qty → reserved_uom_qty en stock.move.line
        - Mejor manejo de reservas
        """
        StockMove = self.env['stock.move']
        StockMoveLine = self.env['stock.move.line']
        
        for record in self:
            # Validar datos de entrada
            if not record.receipt_line_ids:
                raise UserError("No hay líneas de recibo (receipt_line_ids)")
            
            total_locations = sum(len(line.location_ids) for line in record.receipt_line_ids)
            if total_locations == 0:
                raise UserError("No hay ubicaciones en las líneas de recibo")
            
            total_expected = sum(
                location.product_uom_qty
                for line in record.receipt_line_ids
                for location in line.location_ids
            )
            
            _logger.info(f"\n{'='*80}")
            _logger.info(f"INICIANDO CREACIÓN DE PICKING - {record.name}")
            _logger.info(f"{'='*80}")
            _logger.info(f"Total ubicaciones requeridas: {total_locations}")
            _logger.info(f"Cantidad total: {total_expected}")
            
            # ================================================================
            # PASO 1: Crear picking
            # ================================================================
            picking = self.env["stock.picking"].create({
                "is_locked": False,
                "immediate_transfer": False,
                "priority": "0",
                "partner_id": record.partner_id.id,
                "picking_type_id": record.picking_type_id.id,
                "location_id": record.location_id.id,
                "location_dest_id": record.location_dest_id.id,
                "scheduled_date": fields.Datetime.now(),
                "origin": ", ".join(record.purchase_ids.mapped('name')),
                "move_type": "direct",
                "state": "draft",
                "user_id": self.env.uid,
            })
            
            _logger.info(f"Picking creado: {picking.name}")
            
            # ================================================================
            # PASO 2: Agrupar ubicaciones por producto
            # ================================================================
            from collections import defaultdict
            
            product_data = defaultdict(lambda: {
                'total_qty': 0,
                'locations': [],
                'product_id': None,
                'uom_id': None,
            })
            
            for line in record.receipt_line_ids:
                for location in line.location_ids:
                    key = line.product_id.id
                    product_data[key]['product_id'] = line.product_id
                    product_data[key]['uom_id'] = line.product_id.uom_id
                    product_data[key]['total_qty'] += location.product_uom_qty
                    product_data[key]['locations'].append({
                        'location': location,
                        'qty': location.product_uom_qty
                    })
            
            _logger.info(f"Productos únicos: {len(product_data)}")
            
            # ================================================================
            # PASO 3: Crear moves agrupados por producto
            # ================================================================
            move_mapping = {}
            
            for product_id, data in product_data.items():
                move = StockMove.create({
                    "product_id": data['product_id'].id,
                    "name": data['product_id'].display_name,
                    "product_uom": data['uom_id'].id,
                    "product_uom_qty": data['total_qty'],
                    "location_id": record.location_id.id,
                    "location_dest_id": record.location_dest_id.id,
                    "picking_id": picking.id,
                    "date": fields.Datetime.now(),
                })
                move_mapping[product_id] = move
                
                _logger.info(
                    f"Move creado: {data['product_id'].default_code} "
                    f"- Qty total: {data['total_qty']}"
                )
            
            # ================================================================
            # PASO 4: Confirmar picking
            # ================================================================
            picking.action_confirm()
            _logger.info("Picking confirmado")
            
            # ================================================================
            # PASO 5: Asignar disponibilidad
            # ================================================================
            #picking.action_assign()
            _logger.info("Disponibilidad asignada")
            _logger.info(f"Move lines creados por Odoo: {len(picking.move_line_ids)}")
            
            # ================================================================
            # PASO 6: BORRAR move_lines automáticos
            # ================================================================
            _logger.info("Eliminando move_lines automáticos...")
            picking.move_line_ids.unlink()
            
            # ================================================================
            # PASO 7: Crear move_lines con ubicaciones específicas
            # ================================================================
            move_line_count = 0
            
            for line in record.receipt_line_ids:
                for location in line.location_ids:
                    move = move_mapping.get(line.product_id.id)
                    
                    if not move:
                        _logger.error(f"No se encontró move para {line.product_id.default_code}")
                        continue
                    
                    # ODOO 16: Usar reserved_uom_qty en lugar de product_uom_qty
                    StockMoveLine.create({
                        'move_id': move.id,
                        'product_id': line.product_id.id,
                        'product_uom_id': line.product_id.uom_id.id,
                        'location_id': record.location_id.id,
                        'location_dest_id': location.location_id.id,
                        'qty_done': location.product_uom_qty,
                        'reserved_uom_qty': 0,  # ODOO 16: Cambio aquí
                        'lot_id': location.lot_id.id if location.lot_id else False,
                        'picking_id': picking.id,
                    })
                    
                    move_line_count += 1
                    
                    _logger.info(
                        f"  [{move_line_count}] {line.product_id.default_code} "
                        f"-> {location.location_id.name}: {location.product_uom_qty}"
                    )
            
            # ================================================================
            # PASO 8: Validación final
            # ================================================================
            final_move_lines = len(picking.move_line_ids)
            final_qty = sum(picking.move_line_ids.mapped('qty_done'))
            
            _logger.info(f"\n{'='*80}")
            _logger.info(f"RESULTADO FINAL:")
            _logger.info(f"  Move lines: {final_move_lines} (esperados: {total_locations})")
            _logger.info(f"  Cantidad: {final_qty} (esperada: {total_expected})")
            _logger.info(f"{'='*80}\n")
            
            # Validar exactitud
            if final_move_lines != total_locations:
                raise UserError(
                    f"❌ ERROR: Se esperaban {total_locations} move_lines "
                    f"pero se crearon {final_move_lines}"
                )
            
            if abs(final_qty - total_expected) > 0.01:
                raise UserError(
                    f"❌ ERROR: Se esperaban {total_expected} unidades "
                    f"pero se procesaron {final_qty}"
                )
            
            _logger.info("✅ VALIDACIÓN EXITOSA - Picking creado correctamente")
            
            record.warehouse_picking_ids = [(4, picking.id)]
            
            return picking

    
    def create_picking(self):
        """Crea el picking de almacén liberando reservas previas."""
        self.unreserve_product(self.receipt_line_ids.mapped('product_id').ids)
        return self._generate_dict_stock_picking_values()
    
    def generate_lines(self):
        """Genera receipt_line_ids desde transit_picking_ids."""
        records = []
        for record in self:
            for transit in record.transit_picking_ids:
                if transit.state not in ('done',):
                    raise ValidationError(
                        f'El documento {transit.name} no se ha avanzado'
                    )
                for move in transit.move_ids_without_package:
                    vals = {
                        'stock_move_id': move.id,
                        'product_id': move.product_id.id,
                        'quantity_done': move.quantity_done,
                        'purchase_line_id': move.purchase_line_id.id,
                        'product_uom_qty': move.product_qty
                    }
                    records.append((0, 0, vals))
            record.receipt_line_ids = records

class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    
    def action_cancel(self):
        # Agregar codigo de validacion aca
        self.move_line_ids_without_package.write({'qty_done':0})
        return super(stock_picking, self).action_cancel()
    
    @api.model
    def create(self, vals):
        # Agregar codigo de validacion aca
        print(vals)
        return super(stock_picking, self).create(vals)
    
    def write(self, vals):
        # Agregar codigo de validacion aca
        
        return super(stock_picking, self).write(vals)

class StockPackageLevel(models.Model):
    _inherit = 'stock.package_level'
    
    @api.depends('picking_id', 'picking_id.location_dest_id')
    def _compute_location_dest_id(self):
        for pl in self:
            pl.location_dest_id = pl.picking_id.location_dest_id
            