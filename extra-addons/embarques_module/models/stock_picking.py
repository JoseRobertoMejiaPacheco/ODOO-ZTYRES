from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # El cálculo, la solicitud manual y la aprobación viven en cada picking.

    load_order = fields.Integer(
        string='Orden de Carga', default=10, copy=False,
        help='Orden en que se carga el traslado dentro del embarque.')

    embarque_ids = fields.Many2many(
        'embarques.embarques', 'embarques_embarque_picking_rel',
        'picking_id', 'embarque_id', string='Embarques', readonly=True)

    destino_id = fields.Many2one(
        'embarques.destino', string='Destino Detectado',
        compute='_compute_destino', readonly=True)
    zona_id = fields.Many2one(
        'embarques.zona', string='Zona',
        compute='_compute_destino', readonly=True)
    llantas_qty = fields.Float(
        string='Llantas', compute='_compute_destino', readonly=True)
    ciudad_envio_id = fields.Many2one(
        'res.city', string='Ciudad de Envío',
        compute='_compute_destino', readonly=True)
    estado_envio_id = fields.Many2one(
        'res.country.state', string='Estado de Envío',
        compute='_compute_destino', readonly=True)
    invoice_names = fields.Char(
        string='Facturas', compute='_compute_invoice_names', readonly=True)
    pedimento_names = fields.Char(
        string='Pedimentos', compute='_compute_stock_detail', readonly=True)
    source_location_names = fields.Char(
        string='Ubicaciones', compute='_compute_stock_detail', readonly=True)

    embarque_discount_percentage = fields.Float(
        string='Descuento (%)', readonly=True, copy=False, tracking=True,
        digits=(16, 2))
    requested_discount_percentage = fields.Float(
        string='Descuento Solicitado (%)', copy=False, tracking=True,
        digits=(16, 2))
    discount_state = fields.Selection([
        ('draft', 'Calculado'), ('to_approve', 'Por autorizar'),
        ('approved', 'Manual autorizado'), ('rejected', 'Rechazado'),
    ], string='Estado de Aprobación', default='draft', readonly=True,
       copy=False, tracking=True)
    discount_note = fields.Char(string='Detalle del Descuento', readonly=True,
                                copy=False)
    discount_request_note = fields.Char(string='Motivo de la Solicitud', copy=False)
    discount_requested_by = fields.Many2one(
        'res.users', string='Solicitado por', readonly=True, copy=False)
    discount_approved_by = fields.Many2one(
        'res.users', string='Revisado por', readonly=True, copy=False)
    discount_approval_date = fields.Datetime(
        string='Fecha de Revisión', readonly=True, copy=False)
    discount_manual = fields.Boolean(readonly=True, copy=False)

    @api.constrains(
        'requested_discount_percentage', 'discount_request_note', 'load_order')
    def _check_embarque_business_values(self):
        for picking in self:
            requested = picking.requested_discount_percentage
            if requested < 0 or requested > 100:
                raise ValidationError(_(
                    'El descuento solicitado de %s debe estar entre 0%% y 100%%.')
                    % picking.display_name)
            if requested and not (picking.discount_request_note or '').strip():
                raise ValidationError(_(
                    'Captura el motivo del descuento solicitado para %s.') %
                    picking.display_name)
            if picking.embarque_ids and picking.load_order <= 0:
                raise ValidationError(_(
                    'El Orden de Carga de %s debe ser mayor a cero.') %
                    picking.display_name)

    @api.depends('partner_id', 'partner_id.city_id', 'partner_id.state_id',
                 'partner_id.l10n_mx_edi_locality_id',
                 'sale_id.partner_shipping_id',
                 'sale_id.partner_shipping_id.city_id',
                 'sale_id.partner_shipping_id.state_id',
                 'sale_id.partner_shipping_id.l10n_mx_edi_locality_id',
                 'move_ids_without_package.state',
                 'move_ids_without_package.product_uom_qty',
                 'move_ids_without_package.product_id')
    def _compute_destino(self):
        Embarque = self.env['embarques.embarques']
        for picking in self:
            partner = picking.sale_id.partner_shipping_id or picking.partner_id
            destino = Embarque._picking_destino(picking)
            picking.destino_id = destino
            picking.zona_id = destino.zona_id
            picking.llantas_qty = Embarque._picking_llantas(picking)
            picking.ciudad_envio_id = partner.city_id
            picking.estado_envio_id = partner.state_id

    @api.depends('sale_id.invoice_ids.name', 'sale_id.invoice_ids.state')
    def _compute_invoice_names(self):
        for picking in self:
            invoices = picking.sale_id.invoice_ids.filtered(
                lambda move: move.state != 'cancel'
                and move.move_type in ('out_invoice', 'out_refund'))
            picking.invoice_names = ', '.join(invoices.mapped('name'))

    @api.model
    def _pedimento_from_move_line(self, line):
        """Lee el pedimento del campo disponible en la localización instalada."""
        candidates = (
            'l10n_mx_edi_customs_number', 'customs_number',
            'pedimento', 'pedimento_id', 'pedimento_numero',
            'customs_id', 'x_studio_pedimento',
        )
        records = [line, line.lot_id]
        Quant = self.env['stock.quant']
        quant_domain = [
            ('product_id', '=', line.product_id.id),
            ('location_id', '=', line.location_id.id),
        ]
        if line.lot_id:
            quant_domain.append(('lot_id', '=', line.lot_id.id))
        records += list(Quant.sudo().search(quant_domain))
        for record in records:
            if not record:
                continue
            for field_name in candidates:
                if field_name not in record._fields:
                    continue
                value = record[field_name]
                if not value:
                    continue
                if record._fields[field_name].type == 'many2one':
                    return value.display_name
                return str(value)
        return _('Sin pedimento')

    @api.depends('move_line_ids.location_id', 'move_line_ids.lot_id')
    def _compute_stock_detail(self):
        for picking in self:
            pedimentos = []
            locations = []
            for line in picking.move_line_ids:
                pedimento = self._pedimento_from_move_line(line)
                location = line.location_id.complete_name
                if pedimento and pedimento not in pedimentos:
                    pedimentos.append(pedimento)
                if location and location not in locations:
                    locations.append(location)
            picking.pedimento_names = ', '.join(pedimentos)
            picking.source_location_names = ', '.join(locations)

    def write(self, vals):
        protected = {
            'load_order', 'partner_id', 'sale_id', 'state',
            'move_ids_without_package', 'move_ids',
            'requested_discount_percentage', 'discount_request_note',
            'embarque_discount_percentage', 'discount_state',
            'discount_manual',
        }
        carta_vehicle_fields = {
            field_name for field_name, field in self._fields.items()
            if field.type == 'many2one'
            and field.comodel_name == 'l10n_mx_edi.vehicle'
        }
        if protected.union(carta_vehicle_fields) & set(vals):
            delivered = self.mapped('embarque_ids').filtered('is_delivered')
            if delivered:
                raise UserError(_(
                    'No se puede modificar el traslado porque pertenece al '
                    'embarque Entregado %s.') % ', '.join(
                        delivered.mapped('display_name')))
        if vals.get('requested_discount_percentage') and not self.env.context.get('embarque_internal_write'):
            for picking in self:
                embarque = picking.embarque_ids[:1]
                if not embarque:
                    raise UserError(_('El traslado debe pertenecer a un embarque.'))
                solicitado = vals['requested_discount_percentage']
                tope = embarque._max_manual_percentage_for_picking(picking)
                if tope is not False and solicitado > tope:
                    raise UserError(_(
                        'El descuento solicitado (%.2f%%) supera el máximo '
                        'permitido de %.2f%% para %s.') % (
                            solicitado, tope, picking.display_name))
            vals.update({
                'discount_state': 'to_approve',
                'discount_requested_by': self.env.user.id,
                'discount_approved_by': False,
                'discount_approval_date': False,
            })
        res = super().write(vals)
        # Cambios que alteran las llantas o el destino obligan a reevaluar el
        # descuento del embarque completo, no sólo el de este traslado.
        if (not self.env.context.get('embarque_internal_write')
                and (({'partner_id', 'move_ids_without_package', 'move_ids',
                       'load_order'} | carta_vehicle_fields) & set(vals))):
            self.mapped('embarque_ids').action_calculate_discount()
        return res

    def _check_finance(self):
        if not self.env.user.has_group('embarques_module.group_embarques_finance'):
            raise UserError(_('Sólo Finanzas puede autorizar o rechazar descuentos.'))

    def action_approve_discount(self):
        delivered = self.mapped('embarque_ids').filtered('is_delivered')
        if delivered:
            delivered._check_not_delivered()
        self._check_finance()
        for picking in self:
            if not picking.requested_discount_percentage:
                raise UserError(_('%s no tiene una solicitud pendiente.') % picking.display_name)
            solicitado = picking.requested_discount_percentage
            super(StockPicking, picking).write({
                'embarque_discount_percentage': solicitado,
                'requested_discount_percentage': 0.0,
                'discount_manual': True,
                'discount_state': 'approved',
                'discount_note': _('Autorizado por %s: %.2f%%.') % (
                    self.env.user.display_name, solicitado),
                'discount_approved_by': self.env.user.id,
                'discount_approval_date': fields.Datetime.now(),
            })
            picking.message_post(body=_('Descuento manual autorizado: %.2f%%.') % solicitado)
            picking.embarque_ids._propagate_picking_discounts()
        return True

    def action_reject_discount(self):
        delivered = self.mapped('embarque_ids').filtered('is_delivered')
        if delivered:
            delivered._check_not_delivered()
        self._check_finance()
        for picking in self:
            if not picking.requested_discount_percentage:
                raise UserError(_('%s no tiene una solicitud pendiente.') % picking.display_name)
            embarque = picking.embarque_ids[:1]
            percentage, note = embarque._evaluate_picking_discount(picking)
            super(StockPicking, picking).write({
                'requested_discount_percentage': 0.0,
                'embarque_discount_percentage': percentage,
                'discount_manual': False,
                'discount_state': 'rejected',
                'discount_note': _('Rechazado por %s. %s') % (
                    self.env.user.display_name, note),
                'discount_approved_by': self.env.user.id,
                'discount_approval_date': fields.Datetime.now(),
            })
            picking.message_post(body=_('Descuento manual rechazado.'))
            embarque._propagate_picking_discounts()
        return True


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model_create_multi
    def create(self, vals_list):
        picking_ids = [vals.get('picking_id') for vals in vals_list
                       if vals.get('picking_id')]
        delivered = self.env['stock.picking'].browse(
            picking_ids).mapped('embarque_ids').filtered('is_delivered')
        if delivered:
            delivered._check_not_delivered()
        moves = super().create(vals_list)
        if not self.env.context.get('embarque_internal_write'):
            moves.mapped(
                'picking_id.embarque_ids').action_calculate_discount()
        return moves

    def write(self, vals):
        embarques_before = self.mapped('picking_id.embarque_ids')
        affected = embarques_before
        if vals.get('picking_id'):
            affected |= self.env['stock.picking'].browse(
                vals['picking_id']).mapped('embarque_ids')
        delivered = affected.filtered('is_delivered')
        if delivered:
            delivered._check_not_delivered()
        result = super().write(vals)
        relevant = {'product_uom_qty', 'product_id', 'state', 'picking_id'}
        if (not self.env.context.get('embarque_internal_write')
                and relevant & set(vals)):
            (embarques_before | self.mapped(
                'picking_id.embarque_ids')).action_calculate_discount()
        return result

    def unlink(self):
        embarques = self.mapped('picking_id.embarque_ids')
        delivered = embarques.filtered('is_delivered')
        if delivered:
            delivered._check_not_delivered()
        result = super().unlink()
        if not self.env.context.get('embarque_internal_write'):
            embarques.action_calculate_discount()
        return result
