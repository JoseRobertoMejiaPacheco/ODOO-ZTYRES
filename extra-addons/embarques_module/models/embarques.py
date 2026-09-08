from html import escape
from io import BytesIO
import base64
import re
import unicodedata

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class Embarques(models.Model):
    """Embarque: viaje físico con descuento comercial por cada picking.

    La capacidad física proviene del vehículo logístico elegido. El descuento se
    decide por destino, cantidad de llantas y consolidación, sin usar el vehículo como
    límite comercial.
    """

    _name = 'embarques.embarques'
    _description = 'Embarque'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, name desc'

    # ── Identificación ────────────────────────────────────────────────────────
    name = fields.Char(
        string='Referencia', required=True, readonly=True, default='/',
        copy=False)
    active = fields.Boolean(string='Activo', default=True)
    company_id = fields.Many2one(
        'res.company', string='Compañía', required=True,
        default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True)

    stage_id = fields.Many2one(
        'embarques.stage', string='Etapa', required=True, tracking=True,
        ondelete='restrict',
        group_expand='_read_group_stage_ids',
        default=lambda self: self.env['embarques.stage'].search(
            [], order='sequence', limit=1))
    is_delivered = fields.Boolean(
        string='Entregado', compute='_compute_is_delivered', store=True,
        copy=False)
    kanban_state = fields.Selection(
        [
            ('normal', 'En curso'),
            ('done', 'Listo para siguiente etapa'),
            ('blocked', 'Bloqueado'),
        ],
        string='Estado de kanban', default='normal', tracking=True)

    # ── Operación ─────────────────────────────────────────────────────────────
    date_start = fields.Date(
        string='Fecha de programación', required=True,
        default=fields.Date.context_today)
    ruta_id = fields.Many2one(
        'rutas_embarques', string='Ruta', ondelete='restrict', tracking=True)
    operador_id = fields.Many2one(
        'res.partner', string='Operador',
        compute='_compute_vehicle_details', readonly=True,
        help='Operador tomado de las Partes/Intermediarios del vehículo '
             'nativo de Carta Porte.')
    carta_porte_vehicle_id = fields.Many2one(
        'l10n_mx_edi.vehicle', string='Vehículo de Carta Porte',
        ondelete='set null', copy=False,
        help='Referencia histórica. Los embarques nuevos utilizan el catálogo '
             'independiente de vehículos.')
    vehicle_id = fields.Many2one(
        'embarques.vehicle', string='Vehículo', required=True,
        ondelete='restrict', tracking=True,
        help='Unidad propia o externa utilizada para este embarque.')
    carta_porte_vehicle_issue = fields.Char(
        string='Validación del Vehículo',
        compute='_compute_vehicle_details', readonly=True)
    capacidad_m3 = fields.Float(
        string='Capacidad del Camión (m³)', compute='_compute_transport_data',
        readonly=True, digits=(16, 3))
    tag_ids = fields.Many2many(
        'embarques.tag', 'embarques_embarque_tag_rel', 'embarque_id', 'tag_id',
        string='Etiquetas')
    # ── Traslados ─────────────────────────────────────────────────────────────
    pedidos_ids = fields.Many2many(
        'stock.picking', 'embarques_embarque_picking_rel',
        'embarque_id', 'picking_id', string='Traslados')
    picking_count = fields.Integer(
        string='No. Traslados', compute='_compute_picking_count')
    order_count = fields.Integer(
        string='No. Pedidos', compute='_compute_totales', store=True)
    no_clientes = fields.Integer(
        string='No. Clientes', compute='_compute_totales', store=True)
    stop_count = fields.Integer(
        string='Stops del Embarque', compute='_compute_totales', store=True,
        help='Cantidad de clientes distintos que recibirán mercancía en este '
             'embarque. Cada cliente se considera un stop logístico.')
    consolidation_stop_limit = fields.Integer(
        string='Máximo de Stops para Consolidar', required=True, default=2,
        tracking=True,
        help='Cantidad máxima de clientes que pueden completar juntos un '
             'rango de descuento dentro del mismo embarque.')
    consolidation_min_qty = fields.Integer(
        string='Consolidación desde (llantas)', required=True, default=250,
        tracking=True,
        help='No se autoriza consolidar clientes en rangos menores a esta '
             'cantidad de llantas.')
    consolidation_min_percentage = fields.Float(
        string='Participación Mínima por Cliente (%)', required=True,
        default=50.0, digits=(16, 2), tracking=True,
        help='Porcentaje mínimo del rango que debe aportar individualmente '
             'cada cliente para recibir su descuento.')
    invoice_ids = fields.Many2many(
        'account.move', string='Facturas', compute='_compute_invoice_ids')
    invoice_count = fields.Integer(
        string='No. Facturas', compute='_compute_invoice_ids')
    logistic_nc_stamp_status = fields.Selection([
        ('no_invoice', 'Sin factura'),
        ('pending', 'Pendiente'),
        ('stamped', 'Timbrado'),
        ('not_required', 'No aplica'),
        ('error', 'Error'),
    ], string='Timbrado NC Logística', compute='_compute_logistic_nc_stamp_status')
    logistic_nc_stamp_note = fields.Char(
        string='Detalle Timbrado NC', compute='_compute_logistic_nc_stamp_status')
    logistic_nc_count = fields.Integer(
        string='NC Logísticas', compute='_compute_logistic_nc_stamp_status')

    # ── Cubicaje ──────────────────────────────────────────────────────────────
    piezas = fields.Float(
        string='Piezas', compute='_compute_totales', store=True)
    volumen = fields.Float(
        string='Volumen de las Llantas (m³)', compute='_compute_totales',
        store=True, digits=(16, 3))
    ocupacion_m3 = fields.Float(
        string='Ocupación del Camión (%)', compute='_compute_ocupacion_m3',
        digits=(16, 1))
    volumen_faltante_m3 = fields.Float(
        string='Volumen Disponible (m³)', compute='_compute_ocupacion_m3',
        digits=(16, 3))
    productos_sin_volumen = fields.Integer(
        string='Productos sin Volumen', compute='_compute_totales', store=True)
    productos_sin_volumen_texto = fields.Text(
        string='Detalle de Productos sin Volumen', compute='_compute_totales',
        store=True)
    peso = fields.Float(
        string='Peso (kg)', compute='_compute_totales', store=True)

    # ── Base del descuento ────────────────────────────────────────────────────
    total_llantas = fields.Integer(
        string='Llantas del Embarque', compute='_compute_totales', store=True)
    zona_id = fields.Many2one(
        'embarques.zona', string='Zona', compute='_compute_totales', store=True,
        help='Zona común a todos los destinos. Si el embarque mezcla zonas '
             'queda vacía y el descuento pasa a manual.')
    zona_mixta = fields.Boolean(
        string='Zonas Mezcladas', compute='_compute_totales', store=True)
    zonas_texto = fields.Char(
        string='Zonas del Embarque', compute='_compute_totales', store=True)
    ciudades_ruta = fields.Text(
        string='Ciudades de la Ruta', compute='_compute_totales', store=True)
    ciudades_ruta_html = fields.Html(
        string='Recorrido', compute='_compute_totales', store=True,
        sanitize=False)
    amount_untaxed = fields.Monetary(
        string='Total del Embarque antes de IVA', compute='_compute_totales',
        store=True, currency_field='currency_id')
    logistic_cost = fields.Monetary(
        string='Costo Logístico', compute='_compute_totales', store=True,
        currency_field='currency_id',
        help='Costo logístico calculado más el importe capturado manualmente.')
    calculated_logistic_cost = fields.Monetary(
        string='Costo Logístico Calculado', compute='_compute_totales',
        store=True, currency_field='currency_id',
        help='Importe calculado con los porcentajes de cada traslado.')
    manual_logistic_cost = fields.Monetary(
        string='Costo Logístico Manual', currency_field='currency_id',
        tracking=True, default=0.0,
        help='Importe adicional capturado manualmente. Se suma al costo '
             'logístico calculado.')
    qty_ordered = fields.Float(
        string='Pedido', compute='_compute_totales', store=True)
    qty_reserved = fields.Float(
        string='Reservado', compute='_compute_totales', store=True)
    qty_done = fields.Float(
        string='Hecho', compute='_compute_totales', store=True)
    preparation_state = fields.Selection([
        ('empty', 'Sin traslados'),
        ('pending', 'Con diferencias'),
        ('ready', 'Validado'),
    ], string='Validación de Almacén', compute='_compute_totales', store=True)
    preparation_note = fields.Char(
        string='Detalle de Validación', compute='_compute_totales', store=True)

    # ── Descuento ─────────────────────────────────────────────────────────────
    discount_percentage = fields.Float(
        string='Descuento Aplicado (%)', readonly=True, copy=False,
        tracking=True, digits=(16, 2),
        help='Descuento directo que recibirán las facturas de este embarque.')
    discount_status = fields.Selection(
        [
            ('sin_unidad', 'Falta asignar unidad'),
            ('sin_traslados', 'Sin traslados'),
            ('sin_destino', 'Destino sin configuración'),
            ('zona_mixta', 'Zonas mezcladas'),
            ('no_llena', 'Unidad sin llenar'),
            ('destino_no_admite', 'Destino no admite la unidad'),
            ('sin_politica', 'Sin rango/descuento'),
            ('aplica', 'Aplica'),
            ('to_approve', 'Por autorizar'),
            ('manual', 'Manual autorizado'),
            ('rejected', 'Rechazado'),
        ],
        string='Estado del Descuento', readonly=True, copy=False,
        default='sin_unidad', tracking=True)
    discount_note = fields.Char(string='Detalle', readonly=True, copy=False)
    discount_manual = fields.Boolean(
        string='Descuento Manual', readonly=True, copy=False,
        help='El descuento vigente lo autorizó Finanzas; el cálculo automático '
             'ya no lo sobrescribe.')

    requested_discount_percentage = fields.Float(
        string='Descuento Solicitado (%)', copy=False, tracking=True,
        digits=(16, 2),
        help='Descuento manual pendiente de autorización. Mientras Finanzas no '
             'lo apruebe, sigue vigente el descuento calculado.')
    discount_request_note = fields.Char(
        string='Motivo de la Solicitud', copy=False)
    discount_requested_by = fields.Many2one(
        'res.users', string='Solicitado por', readonly=True, copy=False)
    discount_approved_by = fields.Many2one(
        'res.users', string='Revisado por', readonly=True, copy=False)
    discount_approval_date = fields.Datetime(
        string='Fecha de Revisión', readonly=True, copy=False)

    @api.constrains(
        'requested_discount_percentage', 'discount_request_note')
    def _check_manual_discount_request(self):
        for rec in self:
            requested = rec.requested_discount_percentage
            if requested < 0 or requested > 100:
                raise ValidationError(_(
                    'El descuento solicitado debe estar entre 0% y 100%.'))
            if requested and not (rec.discount_request_note or '').strip():
                raise ValidationError(_(
                    'Captura el motivo del descuento manual solicitado.'))

    @api.constrains('manual_logistic_cost')
    def _check_manual_logistic_cost(self):
        for rec in self:
            if rec.manual_logistic_cost < 0:
                raise ValidationError(_(
                    'El costo logístico manual no puede ser negativo.'))

    @api.constrains(
        'consolidation_stop_limit', 'consolidation_min_qty',
        'consolidation_min_percentage')
    def _check_consolidation_rules(self):
        for rec in self:
            if rec.consolidation_stop_limit < 1:
                raise ValidationError(_(
                    'El máximo de stops para consolidar debe ser al menos 1.'))
            if rec.consolidation_min_qty < 250:
                raise ValidationError(_(
                    'La consolidación sólo se autoriza a partir de 250 '
                    'llantas.'))
            if not 0 < rec.consolidation_min_percentage <= 100:
                raise ValidationError(_(
                    'La participación mínima por cliente debe ser mayor que '
                    '0%% y menor o igual que 100%%.'))

    @api.model
    def _vehicle_operator_partners(self, vehicle):
        """Devuelve los operadores SAT configurados en el Vehicle Setup.

        Odoo ha usado nombres técnicos distintos entre revisiones de Carta
        Porte. Primero se atienden los nombres nativos conocidos y después se
        localiza de forma segura la relación de Partes/Intermediarios.
        """
        partners = self.env['res.partner']
        if not vehicle:
            return partners

        # Algunas revisiones exponen el operador directamente en el vehículo.
        for field_name in ('operator_id', 'driver_id'):
            field = vehicle._fields.get(field_name)
            if (field and field.type == 'many2one'
                    and field.comodel_name == 'res.partner'
                    and vehicle[field_name]):
                partners |= vehicle[field_name]

        relation_names = (
            'figure_ids', 'transport_figure_ids', 'intermediary_ids',
            'intermediaries_ids', 'part_ids',
        )
        candidates = []
        for field_name in relation_names:
            field = vehicle._fields.get(field_name)
            if field and field.type in ('one2many', 'many2many'):
                candidates.append(vehicle[field_name])
        if not candidates:
            # Respaldo compatible: busca una relación cuyas líneas tengan un
            # contacto y un tipo de figura, sin depender de una traducción.
            for field_name, field in vehicle._fields.items():
                if field.type not in ('one2many', 'many2many'):
                    continue
                lines = vehicle[field_name]
                line_fields = self.env[field.comodel_name]._fields
                has_partner = any(
                    line_fields.get(name)
                    and line_fields[name].comodel_name == 'res.partner'
                    for name in ('partner_id', 'operator_id'))
                has_type = any(
                    name in line_fields
                    for name in ('type', 'figure_type', 'transport_figure_type'))
                if has_partner and has_type:
                    candidates.append(lines)

        for lines in candidates:
            for line in lines:
                type_value = next((
                    line[name] for name in (
                        'type', 'figure_type', 'transport_figure_type')
                    if name in line._fields
                ), False)
                normalized = str(type_value or '').strip().lower()
                # 01 es Operador en el catálogo SAT de FiguraTransporte.
                if normalized not in ('01', 'operator', 'operador'):
                    continue
                for partner_field in ('partner_id', 'operator_id'):
                    field = line._fields.get(partner_field)
                    if (field and field.comodel_name == 'res.partner'
                            and line[partner_field]):
                        partners |= line[partner_field]
                        break
        return partners

    @api.depends(
        'carta_porte_vehicle_id',
        'carta_porte_vehicle_id.embarques_capacidad_m3')
    def _compute_vehicle_details(self):
        """Toma capacidad y operador de la unidad elegida en el embarque.

        El embarque se prepara antes que la Carta Porte; por ello los vehículos
        de los traslados no intervienen ni generan diferencias.
        """
        for rec in self:
            vehicle = rec.carta_porte_vehicle_id
            operators = rec._vehicle_operator_partners(vehicle)
            rec.operador_id = operators if len(operators) == 1 else False
            if not vehicle:
                # El propio campo obligatorio guía la captura; no se muestra
                # una advertencia duplicada por falta de unidad.
                rec.carta_porte_vehicle_issue = False
            elif not vehicle.embarques_capacidad_m3:
                rec.carta_porte_vehicle_issue = (
                    _('El vehículo %s no tiene Capacidad útil en m³.') %
                    vehicle.display_name)
            elif len(operators) > 1:
                rec.carta_porte_vehicle_issue = (
                    _('El vehículo %s tiene más de un Operador en Partes: %s.') %
                    (vehicle.display_name,
                     ', '.join(operators.mapped('display_name'))))
            elif not operators:
                rec.carta_porte_vehicle_issue = (
                    _('El vehículo %s no tiene una Parte de tipo Operador.') %
                    vehicle.display_name)
            else:
                rec.carta_porte_vehicle_issue = False

    @api.onchange('carta_porte_vehicle_id')
    def _onchange_carta_porte_vehicle_id(self):
        """Refresca el operador y advierte antes de intentar guardar."""
        self._compute_vehicle_details()
        if self.carta_porte_vehicle_issue:
            return {'warning': {
                'title': _('Configuración incompleta de la unidad'),
                'message': self.carta_porte_vehicle_issue,
            }}

    def _validate_vehicle_configuration(self):
        """Valida únicamente nombre y cubicaje de la unidad logística."""
        for rec in self:
            vehicle = rec.vehicle_id
            if not vehicle:
                raise ValidationError(_(
                    'No se puede guardar el embarque sin seleccionar una '
                    'unidad.'))
            if vehicle.capacity_m3 <= 0:
                raise ValidationError(_(
                    'No se puede guardar el embarque: la unidad "%s" no '
                    'tiene un cubicaje mayor que cero.') %
                    vehicle.display_name)

    @api.depends(
        'vehicle_id.capacity_m3')
    def _compute_transport_data(self):
        for rec in self:
            rec.capacidad_m3 = rec.vehicle_id.capacity_m3 or 0.0

    # ══════════════════════════════════════════════════════════════════════════
    # Computes
    # ══════════════════════════════════════════════════════════════════════════

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return stages.search([], order=order)

    @api.depends('stage_id')
    def _compute_is_delivered(self):
        delivered = self.env.ref(
            'embarques_module.stage_entregado', raise_if_not_found=False)
        for rec in self:
            rec.is_delivered = bool(delivered and rec.stage_id == delivered)

    def _check_not_delivered(self):
        delivered_records = self.filtered('is_delivered')
        if delivered_records:
            raise UserError(_(
                'El embarque %s ya está Entregado y no admite ninguna '
                'modificación.') % ', '.join(
                    delivered_records.mapped('display_name')))

    def _check_stage_change(self, new_stage):
        """Sólo permite avanzar una etapa y valida el cierre operativo."""
        delivered = self.env.ref(
            'embarques_module.stage_entregado', raise_if_not_found=False)
        for rec in self:
            if rec.is_delivered:
                rec._check_not_delivered()
            if not new_stage:
                raise UserError(_('El embarque debe conservar una etapa.'))
            if new_stage == rec.stage_id:
                continue
            sequences = self.env['embarques.stage'].search([]).mapped('sequence')
            duplicates = sorted({
                str(value) for value in sequences
                if sequences.count(value) > 1
            })
            if duplicates:
                raise UserError(_(
                    'La configuración de etapas tiene secuencias repetidas: '
                    '%s. Corrígelas antes de avanzar embarques.') %
                    ', '.join(duplicates))
            next_stage = self.env['embarques.stage'].search([
                ('sequence', '>', rec.stage_id.sequence),
            ], order='sequence, id', limit=1)
            if new_stage != next_stage:
                raise UserError(_(
                    'El embarque %(shipment)s sólo puede avanzar de '
                    '"%(current)s" a "%(next)s"; no se permite saltar ni '
                    'regresar etapas.') % {
                        'shipment': rec.display_name,
                        'current': rec.stage_id.display_name,
                        'next': next_stage.display_name or _('sin etapa siguiente'),
                    })
            if delivered and new_stage == delivered:
                pending = rec.pedidos_ids.filtered(
                    lambda picking: picking.state != 'done')
                if pending:
                    raise UserError(_(
                        'No se puede marcar %(shipment)s como Entregado. Los '
                        'siguientes traslados todavía no están Hechos: %(picking)s.') % {
                            'shipment': rec.display_name,
                            'picking': ', '.join(
                                pending.mapped('display_name')),
                        })
                if rec.preparation_state != 'ready':
                    raise UserError(_(
                        'No se puede marcar %s como Entregado hasta conciliar '
                        'Pedido = Reservado + Hecho.') % rec.display_name)
                # Si existen facturas con descuento logístico, todas sus NC
                # deben estar fiscalmente timbradas (UUID), no sólo publicadas.
                if rec.logistic_nc_stamp_status in ('pending', 'error'):
                    raise UserError(_(
                        'No se puede marcar %(shipment)s como Entregado porque '
                        'el timbrado de la NC logística no está completo. %(detail)s') % {
                            'shipment': rec.display_name,
                            'detail': rec.logistic_nc_stamp_note or '',
                        })

    @api.depends('pedidos_ids')
    def _compute_picking_count(self):
        for rec in self:
            rec.picking_count = len(rec.pedidos_ids)

    @api.depends('pedidos_ids.sale_id.invoice_ids.state')
    def _compute_invoice_ids(self):
        for rec in self:
            invoices = rec.pedidos_ids.mapped('sale_id.invoice_ids').filtered(
                lambda m: m.move_type in ('out_invoice', 'out_refund')
                and m.state != 'cancel')
            rec.invoice_ids = invoices
            rec.invoice_count = len(invoices)

    @api.depends(
        'pedidos_ids.sale_id.invoice_ids.state',
        'pedidos_ids.sale_id.invoice_ids.l10n_mx_edi_cfdi_uuid',
        'pedidos_ids.sale_id.invoice_ids.embarque_logistic_nc_id',
        'pedidos_ids.sale_id.invoice_ids.embarque_logistic_nc_id.state',
        'pedidos_ids.sale_id.invoice_ids.embarque_logistic_nc_id.l10n_mx_edi_cfdi_uuid',
        'pedidos_ids.sale_id.invoice_ids.embarque_logistic_nc_id.embarque_logistic_stamp_error',
        'pedidos_ids.sale_id.embarque_discount_percentage',
        'pedidos_ids.embarque_discount_percentage',
        'pedidos_ids.embarque_ids.stage_id')
    def _compute_logistic_nc_stamp_status(self):
        for rec in self:
            invoices = rec.pedidos_ids.mapped('sale_id.invoice_ids').filtered(
                lambda m: m.move_type == 'out_invoice' and m.state != 'cancel')
            ncs = invoices.mapped('embarque_logistic_nc_id').filtered(
                lambda m: m.state != 'cancel')
            rec.logistic_nc_count = len(ncs)
            if not invoices:
                rec.logistic_nc_stamp_status = 'no_invoice'
                rec.logistic_nc_stamp_note = 'Aún no hay facturas para evaluar.'
                continue

            posted = invoices.filtered(lambda m: m.state == 'posted')
            if not posted:
                rec.logistic_nc_stamp_status = 'pending'
                rec.logistic_nc_stamp_note = 'Las facturas todavía están en borrador.'
                continue

            # No usar embarque_discount_amount como criterio: puede estar
            # desactualizado/0 aunque la factura venga de un pedido con 5%.
            # La fuente de verdad son las líneas facturadas y sus pedidos.
            invoices_with_discount = posted.filtered(
                lambda m: m._requires_embarque_logistic_nc())
            if not invoices_with_discount:
                rec.logistic_nc_stamp_status = 'not_required'
                rec.logistic_nc_stamp_note = 'Las facturas no requieren NC logística.'
                continue

            missing = invoices_with_discount.filtered(
                lambda m: not m.embarque_logistic_nc_id)
            if missing:
                rec.logistic_nc_stamp_status = 'error'
                rec.logistic_nc_stamp_note = (
                    'Falta generar NC logística para: %s' %
                    ', '.join(missing.mapped('display_name')))
                continue

            relevant_ncs = invoices_with_discount.mapped('embarque_logistic_nc_id')
            unstamped = relevant_ncs.filtered(
                lambda m: m.state != 'posted' or not m.l10n_mx_edi_cfdi_uuid)
            if unstamped:
                details = []
                for nc in unstamped:
                    edi_errors = nc.edi_document_ids.filtered(
                        lambda d: d.blocking_level == 'error')
                    error_text = nc.embarque_logistic_stamp_error or (
                        '; '.join(filter(None, edi_errors.mapped('error')))
                        if edi_errors else '')
                    details.append('%s%s' % (
                        nc.display_name,
                        (': ' + error_text) if error_text else ' (sin UUID)'))
                rec.logistic_nc_stamp_status = 'error'
                rec.logistic_nc_stamp_note = ' | '.join(details)[:500]
                continue

            rec.logistic_nc_stamp_status = 'stamped'
            rec.logistic_nc_stamp_note = '%s NC logística(s) timbrada(s) correctamente.' % len(relevant_ncs)

    def action_retry_logistic_nc_stamp(self):
        """Reintenta generación/timbrado de NC de las facturas del embarque."""
        invoices = self.mapped('pedidos_ids.sale_id.invoice_ids').filtered(
            lambda m: m.move_type == 'out_invoice' and m.state == 'posted')
        invoices.action_generate_embarque_logistic_nc()
        return True

    @api.depends(
        'pedidos_ids',
        'pedidos_ids.partner_id',
        'pedidos_ids.load_order',
        'pedidos_ids.sale_id.amount_untaxed',
        'pedidos_ids.sale_id.partner_id',
        'pedidos_ids.sale_id.partner_shipping_id',
        'pedidos_ids.sale_id.partner_shipping_id.city_id',
        'pedidos_ids.sale_id.partner_shipping_id.state_id',
        'pedidos_ids.sale_id.partner_shipping_id.l10n_mx_edi_locality_id',
        'pedidos_ids.embarque_discount_percentage',
        'pedidos_ids.move_ids_without_package.state',
        'pedidos_ids.move_ids_without_package.product_uom_qty',
        'pedidos_ids.move_ids_without_package.reserved_availability',
        'pedidos_ids.move_ids_without_package.quantity_done',
        'pedidos_ids.move_ids_without_package.product_id',
        'pedidos_ids.move_ids_without_package.product_id.volume',
        'pedidos_ids.move_ids_without_package.product_id.weight',
        'manual_logistic_cost',
    )
    def _compute_totales(self):
        """Cubicaje, llantas y zona(s) del embarque, en una sola pasada."""
        Zona = self.env['embarques.zona']
        for embarque in self:
            piezas = volumen = peso = llantas = 0.0
            qty_ordered = qty_reserved = qty_done = 0.0
            zonas = Zona
            partners = self.env['res.partner']
            stop_customers = self.env['res.partner']
            destinos_ruta = []
            productos_sin_volumen = self.env['product.product']
            amount_untaxed = 0.0
            calculated_logistic_cost = 0.0
            preparation_buckets = {}

            # En un onchange los pickings recién agregados pueden tener NewId.
            # No se usa `p.id` como desempate porque dos NewId no son
            # ordenables en Python. `sorted()` es estable y conserva el orden
            # actual cuando varios traslados comparten el mismo load_order.
            for picking_index, picking in enumerate(
                    embarque.pedidos_ids.sorted(lambda p: p.load_order or 0)):
                partners |= picking.partner_id
                customer = embarque._customer_for_picking(picking)
                if customer:
                    stop_customers |= customer
                partner = picking.sale_id.partner_shipping_id or picking.partner_id
                destino = embarque._picking_destino(picking)
                ciudad = partner.city_id
                estado_record = (
                    destino.state_id if destino else
                    ciudad.state_id if ciudad else partner.state_id)
                estado = estado_record.name if estado_record else ''
                lugar = ((destino.name or '') if destino else
                         ciudad.name if ciudad else partner.city or '')
                partes_destino = [lugar] if lugar else []
                if estado and estado.lower() not in lugar.lower():
                    partes_destino.append(estado)
                etiqueta_destino = ', '.join(partes_destino)
                if (etiqueta_destino and
                        (not destinos_ruta or
                         destinos_ruta[-1] != etiqueta_destino)):
                    destinos_ruta.append(etiqueta_destino)
                for move in picking.move_ids_without_package:
                    if move.state == 'cancel' or not move.product_id:
                        continue
                    qty = move.product_uom_qty
                    piezas += qty
                    volumen += qty * (move.product_id.volume or 0.0)
                    peso += qty * (move.product_id.weight or 0.0)
                    if self._is_llanta(move.product_id):
                        llantas += qty
                        qty_ordered += qty
                        qty_reserved += (
                            0.0 if move.state in ('done', 'cancel')
                            else move.reserved_availability)
                        qty_done += move.quantity_done
                        validation_key = (picking_index, move.product_id.id)
                        bucket = preparation_buckets.setdefault(
                            validation_key, [0.0, 0.0, 0.0])
                        bucket[0] += qty
                        if move.state != 'done':
                            bucket[1] += move.reserved_availability
                        bucket[2] += move.quantity_done
                        if not move.product_id.volume:
                            productos_sin_volumen |= move.product_id
                    line = move.sale_line_id
                    if line and line.product_uom_qty:
                        move_untaxed = (
                            line.price_subtotal / line.product_uom_qty) * qty
                        amount_untaxed += move_untaxed
                        calculated_logistic_cost += (
                            move_untaxed
                            * (picking.embarque_discount_percentage or 0.0)
                            / 100.0)

                destino = embarque._picking_destino(picking)
                if destino.zona_id:
                    zonas |= destino.zona_id

            embarque.piezas = piezas
            embarque.volumen = volumen
            embarque.peso = peso
            embarque.no_clientes = len(partners)
            embarque.stop_count = len(stop_customers)
            embarque.order_count = len(embarque.pedidos_ids.mapped('sale_id'))
            embarque.total_llantas = int(round(llantas))
            embarque.zona_mixta = len(zonas) > 1
            embarque.zona_id = zonas if len(zonas) == 1 else False
            embarque.zonas_texto = ', '.join(zonas.mapped('name'))
            embarque.ciudades_ruta = ' → '.join(destinos_ruta)
            colores = ('primary', 'success', 'warning', 'info', 'secondary')
            elementos = []
            for index, destino_ruta in enumerate(destinos_ruta, 1):
                if elementos:
                    elementos.append('<span class="mx-1 text-muted">→</span>')
                elementos.append(
                    '<span class="badge badge-%s o_embarque_route_badge">%s&nbsp; %s</span>'
                    % (colores[(index - 1) % len(colores)], index,
                       escape(destino_ruta)))
            embarque.ciudades_ruta_html = (
                '<div class="d-flex flex-wrap align-items-center o_embarque_route">%s</div>'
                % ''.join(elementos))
            embarque.amount_untaxed = amount_untaxed
            embarque.calculated_logistic_cost = calculated_logistic_cost
            embarque.logistic_cost = (
                calculated_logistic_cost + embarque.manual_logistic_cost)
            embarque.productos_sin_volumen = len(productos_sin_volumen)
            embarque.productos_sin_volumen_texto = ', '.join(
                productos_sin_volumen.mapped('display_name'))
            embarque.qty_ordered = qty_ordered
            embarque.qty_reserved = qty_reserved
            embarque.qty_done = qty_done
            differences = [
                ordered - reserved - done
                for ordered, reserved, done in preparation_buckets.values()
                if abs(ordered - reserved - done) > 0.01
            ]
            if not embarque.pedidos_ids:
                embarque.preparation_state = 'empty'
                embarque.preparation_note = _('Agrega traslados al embarque.')
            elif not differences:
                embarque.preparation_state = 'ready'
                embarque.preparation_note = _(
                    'Pedido, reservado y hecho están conciliados.')
            else:
                embarque.preparation_state = 'pending'
                missing = sum(value for value in differences if value > 0)
                excess = abs(sum(value for value in differences if value < 0))
                details = []
                if missing:
                    details.append(_('faltan %.2f') % missing)
                if excess:
                    details.append(_('sobran %.2f') % excess)
                embarque.preparation_note = _(
                    '%s línea(s) con diferencia: %s llantas.') % (
                        len(differences), ', '.join(details))

    @api.depends('volumen', 'pedidos_ids')
    def _compute_ocupacion_m3(self):
        for rec in self:
            capacidad = rec.capacidad_m3
            rec.ocupacion_m3 = min(100.0, rec.volumen / capacidad * 100.0) if capacidad else 0.0
            rec.volumen_faltante_m3 = max(0.0, capacidad - rec.volumen) if capacidad else 0.0

    # ══════════════════════════════════════════════════════════════════════════
    # Destino y llantas
    # ══════════════════════════════════════════════════════════════════════════

    @api.model
    def _is_llanta(self, product):
        """Hook: qué producto cuenta como llanta para llenar la unidad.

        Por defecto cuenta cualquier almacenable o consumible (quedan fuera los
        servicios). Si sólo deben contar ciertas categorías, restringe aquí.
        """
        return product.type in ('product', 'consu')

    @api.model
    def _picking_llantas(self, picking):
        """Llantas SOLICITADAS en el traslado.

        Se usa `product_uom_qty` y no la reservada a propósito: una llanta sin
        reservar no debe tumbar por sí sola un descuento ya calculado.
        """
        return sum(
            move.product_uom_qty
            for move in picking.move_ids_without_package
            if move.state != 'cancel' and move.product_id
            and self._is_llanta(move.product_id)
        )

    @api.model
    def _picking_destino(self, picking):
        """Destino de la dirección de entrega del traslado."""
        partner = picking.sale_id.partner_shipping_id or picking.partner_id
        return self.env['embarques.destino']._match_partner(
            partner, company=picking.company_id)

    def _destinos(self):
        """Destinos de todos los traslados del embarque."""
        self.ensure_one()
        destinos = self.env['embarques.destino']
        for picking in self.pedidos_ids:
            destinos |= self._picking_destino(picking)
        return destinos

    def _zonas(self):
        self.ensure_one()
        return self._destinos().mapped('zona_id')

    def _assign_initial_load_orders(self):
        """Asigna 10, 20, 30... sólo a órdenes vacíos o repetidos."""
        for embarque in self:
            used = set()
            next_order = 10
            for picking in embarque.pedidos_ids:
                current = int(picking.load_order or 0)
                if current > 0 and current not in used:
                    used.add(current)
                    next_order = max(next_order, current + 10)
                    continue
                while next_order in used:
                    next_order += 10
                picking.with_context(embarque_internal_write=True).write({
                    'load_order': next_order,
                })
                used.add(next_order)
                next_order += 10
        return True

    # ══════════════════════════════════════════════════════════════════════════
    # Cálculo del descuento
    # ══════════════════════════════════════════════════════════════════════════

    def _evaluate_discount(self):
        """Resumen legado; la decisión real se toma por cada picking."""
        self.ensure_one()
        if not self.pedidos_ids:
            return 'sin_traslados', 0.0, _('El embarque no tiene traslados.')
        results = [self._evaluate_picking_discount(p)[0]
                   for p in self.pedidos_ids]
        applies = sum(1 for value in results if value > 0)
        unique = set(results)
        percentage = unique.pop() if len(unique) == 1 else 0.0
        return ('aplica' if applies else 'no_llena', percentage,
                _('%s de %s traslados cumplen solos o mediante consolidación '
                  'dentro del embarque. Cada picking conserva el porcentaje '
                  'de su destino; no se toma el máximo.') % (
                    applies, len(results)))

    def _city_for_picking(self, picking):
        destino = self._picking_destino(picking)
        if destino and destino.city_id:
            return destino.city_id
        partner = picking.sale_id.partner_shipping_id or picking.partner_id
        return partner.city_id if partner else self.env['res.city']

    @api.model
    def _customer_for_picking(self, picking):
        partner = picking.sale_id.partner_id or picking.partner_id
        return partner.commercial_partner_id if partner else partner

    def _customer_llantas(self, customer):
        """Compra total de un cliente dentro de este embarque."""
        self.ensure_one()
        return sum(
            self._picking_llantas(route_picking)
            for route_picking in self.pedidos_ids
            if self._customer_for_picking(route_picking) == customer)

    def _stop_partners_for_picking(self, picking):
        """Otros clientes del mismo embarque habilitados para consolidación.

        Ya no depende de ciudades configuradas. La ruta es el propio embarque
        y sólo se consolida cuando la cantidad de clientes distintos no supera
        el límite capturado en éste.
        """
        self.ensure_one()
        customer = self._customer_for_picking(picking)
        customers = self.env['res.partner']
        for route_picking in self.pedidos_ids:
            route_customer = self._customer_for_picking(route_picking)
            if route_customer:
                customers |= route_customer
        if (not customer or len(customers) < 2
                or len(customers) > self.consolidation_stop_limit):
            return self.env['res.partner']
        return customers - customer

    def _partner_supports_range(self, partner, transport_range):
        """El cliente compañero tiene un destino que admite el mismo rango."""
        self.ensure_one()
        partner_pickings = self.pedidos_ids.filtered(
            lambda route_picking:
                self._customer_for_picking(route_picking) == partner)
        return any(
            transport_range in self._picking_destino(
                route_picking).discount_policy_ids.mapped('unidad_id')
            for route_picking in partner_pickings
            if self._picking_destino(route_picking))

    def _discount_capacity_result(self, picking, transport_range):
        """Valida rango, mínimo general y participación de cada cliente."""
        self.ensure_one()
        capacity = transport_range.capacidad_llantas
        customer = self._customer_for_picking(picking)
        own_qty = self._customer_llantas(customer)
        if own_qty >= capacity:
            return True, own_qty, False, _(
                'El cliente llena por sí solo el rango con %s llantas.') % own_qty

        if capacity < self.consolidation_min_qty:
            return False, own_qty, False, _(
                'El rango es de %s llantas y la consolidación sólo se '
                'autoriza a partir de %s.') % (
                    capacity, self.consolidation_min_qty)

        minimum_own_qty = (
            capacity * self.consolidation_min_percentage / 100.0)
        if own_qty < minimum_own_qty:
            return False, own_qty, False, _(
                'El cliente aporta %s llantas; necesita al menos %s '
                '(%s%% de %s) para consolidar en este embarque.') % (
                    own_qty, minimum_own_qty,
                    self.consolidation_min_percentage, capacity)

        partners = self._stop_partners_for_picking(picking)
        if not partners:
            return False, own_qty, False, _(
                'La consolidación requiere 2 clientes y este embarque tiene '
                '%s stop(s); el máximo autorizado es %s.') % (
                    self.stop_count, self.consolidation_stop_limit)

        for partner in partners:
            if not self._partner_supports_range(partner, transport_range):
                continue
            partner_qty = self._customer_llantas(partner)
            if (partner_qty >= minimum_own_qty
                    and own_qty + partner_qty >= capacity):
                return True, own_qty, partner, _(
                    '%s + %s: %s llantas. Ambos clientes aportan al menos '
                    '%s%% del rango dentro del mismo embarque.') % (
                        customer.display_name, partner.display_name,
                        own_qty + partner_qty,
                        self.consolidation_min_percentage)
        return False, own_qty, False, _(
            'Los clientes del embarque no cumplen simultáneamente el total '
            'del rango y la participación mínima individual de %s%%.') % (
                self.consolidation_min_percentage)

    def _candidate_ranges(self, destino):
        """Todos los rangos comerciales permitidos por el destino."""
        self.ensure_one()
        options = destino.discount_policy_ids.filtered(
            lambda option: option.active and option.unidad_id.active)
        counts = {}
        for option in options:
            counts.setdefault(option.unidad_id.id, []).append(option)
        duplicated = [values for values in counts.values() if len(values) > 1]
        if duplicated:
            detail = '; '.join('%s: %s' % (
                values[0].unidad_id.display_name,
                ', '.join('%.2f%%' % option.percentage for option in values))
                for values in duplicated)
            raise UserError(_(
                'El destino "%s" tiene más de un descuento para el mismo '
                'rango (%s). Corrige el catálogo de destinos antes de '
                'calcular el descuento.') % (destino.display_name, detail))
        candidates = options.mapped('unidad_id')
        return candidates.sorted(
            lambda transport_range: (
                -transport_range.capacidad_llantas,
                transport_range.sequence,
                transport_range.id))

    def action_calculate_discount(self):
        """Recalcula el descuento y lo baja a los pedidos de venta.

        Un descuento autorizado por Finanzas no se sobrescribe: sólo se
        actualiza el detalle informativo.
        """
        self._check_not_delivered()
        for embarque in self:
            status, percentage, note = embarque._evaluate_discount()

            if embarque.discount_manual:
                vals = {
                    'discount_status': 'manual',
                    'discount_note': _('Autorizado por Finanzas. Cálculo: %s') % note,
                }
            elif embarque.requested_discount_percentage:
                vals = {'discount_status': 'to_approve', 'discount_note': note}
            else:
                vals = {
                    'discount_percentage': percentage,
                    'discount_status': status,
                    'discount_note': note,
                }

            super(Embarques, embarque).write(vals)
            for picking in embarque.pedidos_ids:
                if picking.discount_manual or picking.requested_discount_percentage:
                    continue
                percentage, picking_note = embarque._evaluate_picking_discount(picking)
                picking.with_context(embarque_internal_write=True).write({
                    'embarque_discount_percentage': percentage,
                    'discount_state': 'draft',
                    'discount_note': picking_note,
                })
            embarque._propagate_picking_discounts()
        return True

    def _evaluate_picking_discount(self, picking):
        """Porcentaje propio: llena solo o consolida dentro del embarque."""
        self.ensure_one()
        if not self.pedidos_ids:
            return 0.0, _('El embarque no tiene traslados.')
        destino = self._picking_destino(picking)
        if not destino or not destino.zona_id:
            return 0.0, _('El traslado no tiene destino o zona configurada.')
        candidates = self._candidate_ranges(destino)
        if not candidates:
            return 0.0, _('%s no tiene rangos comerciales permitidos.') % (
                destino.name)

        failure_notes = []
        for transport_range in candidates:
            option = destino.discount_policy_ids.filtered(
                lambda record: record.active
                and record.unidad_id == transport_range)[:1]
            if not option:
                failure_notes.append(_('Sin descuento configurado para %s.') %
                                     transport_range.name)
                continue
            capacity_ok, own_qty, _partner, capacity_note = (
                self._discount_capacity_result(picking, transport_range))
            if not capacity_ok:
                failure_notes.append('%s: %s' % (
                    transport_range.name, capacity_note))
                continue
            percentage = option.percentage
            return percentage, _(
                '%s: %.2f%% con rango %s (%s llantas). Compra del cliente: '
                '%s. %s') % (
                    destino.name, percentage, transport_range.name,
                    transport_range.capacidad_llantas, own_qty, capacity_note)
        return 0.0, ' | '.join(failure_notes)

    def _max_manual_percentage_for_picking(self, picking):
        """Techo manual según los rangos permitidos del destino del picking."""
        self.ensure_one()
        destino = self._picking_destino(picking)
        if not destino or not destino.zona_id or not destino.discount_policy_ids:
            return False
        rows = destino.discount_policy_ids.filtered('active')
        return max(rows.mapped('percentage')) if rows else False

    def _propagate_picking_discounts(self):
        """Pasa a cada pedido el descuento autorizado/calculado de su picking."""
        for embarque in self:
            for order in embarque.pedidos_ids.mapped('sale_id'):
                pickings = embarque.pedidos_ids.filtered(lambda p: p.sale_id == order)
                percentages = set(pickings.mapped('embarque_discount_percentage'))
                # if len(percentages) > 1:
                #     raise UserError(_(
                #         'El pedido %s tiene traslados con descuentos distintos. '
                #         'Sepáralos antes de facturar.') % order.display_name)
                vals = {
                    'embarque_discount_percentage': percentages.pop() if percentages else 0.0,
                }
                if 'use_embarque_logistic_nc' in order._fields:
                    vals['use_embarque_logistic_nc'] = True
                order.write(vals)
        return True

    def _propagate_discount(self):
        """Empuja el descuento a los pedidos de venta de los traslados.

        La factura todavía no existe: el pedido guarda el porcentaje y
        `sale.order.line._prepare_invoice_line()` lo materializa al facturar.
        """
        for embarque in self:
            orders = embarque.pedidos_ids.mapped('sale_id')
            for order in orders:
                vals = {}
                if order.embarque_discount_percentage != embarque.discount_percentage:
                    vals['embarque_discount_percentage'] = embarque.discount_percentage
                if 'use_embarque_logistic_nc' in order._fields and not order.use_embarque_logistic_nc:
                    vals['use_embarque_logistic_nc'] = True
                if vals:
                    order.write(vals)
        return True

    # ══════════════════════════════════════════════════════════════════════════
    # Descuento manual
    # ══════════════════════════════════════════════════════════════════════════

    def _max_manual_percentage(self):
        """Mayor porcentaje válido entre los destinos reales del embarque."""
        self.ensure_one()
        percentages = [
            self._max_manual_percentage_for_picking(picking)
            for picking in self.pedidos_ids
        ]
        percentages = [value for value in percentages if value is not False]
        return max(percentages) if percentages else False

    def _check_finance(self):
        if not self.env.user.has_group('embarques_module.group_embarques_finance'):
            raise UserError(_(
                'Sólo Finanzas puede autorizar o rechazar descuentos manuales.'))

    def action_approve_discount(self):
        self._check_not_delivered()
        self._check_finance()
        for embarque in self:
            if not embarque.requested_discount_percentage:
                raise UserError(_('El embarque %s no tiene solicitud pendiente.')
                                % embarque.name)
            solicitado = embarque.requested_discount_percentage
            super(Embarques, embarque).write({
                'discount_percentage': solicitado,
                'requested_discount_percentage': 0.0,
                'discount_manual': True,
                'discount_status': 'manual',
                'discount_note': _('Autorizado por %s: %.2f%%.') % (
                    self.env.user.display_name, solicitado),
                'discount_approved_by': self.env.user.id,
                'discount_approval_date': fields.Datetime.now(),
            })
            embarque.message_post(body=_(
                'Descuento manual <b>autorizado</b>: %.2f%%.<br/>Motivo: %s'
            ) % (solicitado, embarque.discount_request_note or _('sin motivo')))
            embarque._propagate_discount()
        return True

    def action_reject_discount(self):
        self._check_not_delivered()
        self._check_finance()
        for embarque in self:
            if not embarque.requested_discount_percentage:
                raise UserError(_('El embarque %s no tiene solicitud pendiente.')
                                % embarque.name)
            # Se vuelve al resultado automático, pero el estado queda en
            # "Rechazado" para dejar constancia. El siguiente recálculo lo
            # devuelve a su estado normal.
            _status, percentage, note = embarque._evaluate_discount()
            super(Embarques, embarque).write({
                'requested_discount_percentage': 0.0,
                'discount_percentage': percentage,
                'discount_status': 'rejected',
                'discount_note': _('Rechazado por %s. Vigente: %s') % (
                    self.env.user.display_name, note),
                'discount_approved_by': self.env.user.id,
                'discount_approval_date': fields.Datetime.now(),
            })
            embarque.message_post(body=_(
                'Descuento manual <b>rechazado</b>. Vuelve al automático: %.2f%%.'
                '<br/>%s') % (percentage, note))
            embarque._propagate_discount()
        return True

    def action_reset_discount(self):
        """Libera un descuento manual y vuelve al cálculo automático."""
        self._check_not_delivered()
        self._check_finance()
        super(Embarques, self).write({
            'discount_manual': False,
            'requested_discount_percentage': 0.0,
            'discount_request_note': False,
        })
        for embarque in self:
            embarque.message_post(body=_(
                'Descuento manual retirado por %s; vuelve al cálculo automático.'
            ) % self.env.user.display_name)
        return self.action_calculate_discount()

    # ══════════════════════════════════════════════════════════════════════════
    # ORM
    # ══════════════════════════════════════════════════════════════════════════

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.pop('transport_unit_id', None)
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'embarques.embarques') or '/'
        embarques = super().create(vals_list)
        embarques._assign_initial_load_orders()
        embarques._validate_vehicle_configuration()
        embarques.action_calculate_discount()
        return embarques

    def write(self, vals):
        self._check_not_delivered()
        vals.pop('transport_unit_id', None)
        if 'stage_id' in vals:
            new_stage = self.env['embarques.stage'].browse(vals['stage_id'])
            self._check_stage_change(new_stage)
        if vals.get('requested_discount_percentage'):
            solicitado = vals['requested_discount_percentage']
            for embarque in self:
                tope = embarque._max_manual_percentage()
                if tope is not False and solicitado > tope:
                    raise UserError(_(
                        'El descuento solicitado (%.2f%%) supera el máximo de '
                        '%.2f%% permitido por los destinos y rangos del '
                        'embarque en %s.') % (
                            solicitado, tope,
                            embarque.zonas_texto or _('sus zonas')))
            vals.update({
                'discount_status': 'to_approve',
                'discount_requested_by': self.env.user.id,
                'discount_approved_by': False,
                'discount_approval_date': False,
            })

        res = super().write(vals)
        if 'pedidos_ids' in vals:
            self._assign_initial_load_orders()
        self._validate_vehicle_configuration()

        if vals.get('requested_discount_percentage'):
            for embarque in self:
                embarque.message_post(body=_(
                    '%s <b>solicita</b> un descuento manual de %.2f%%.'
                    '<br/>Motivo: %s'
                ) % (self.env.user.display_name,
                     vals['requested_discount_percentage'],
                     vals.get('discount_request_note')
                     or embarque.discount_request_note or _('sin motivo')))

        if ({'pedidos_ids', 'consolidation_stop_limit',
             'consolidation_min_qty', 'consolidation_min_percentage'}
                & set(vals)):
            self.action_calculate_discount()
        return res

    def unlink(self):
        self._check_not_delivered()
        return super().unlink()

    # ══════════════════════════════════════════════════════════════════════════
    # Acciones
    # ══════════════════════════════════════════════════════════════════════════

    def _business_configuration_messages(self):
        """Devuelve errores y advertencias operativas antes de liberar el viaje."""
        self.ensure_one()
        errors = []
        warnings = []
        # Un embarque entregado es un documento histórico e inmutable. No se
        # debe volver a someter a validaciones de preparación al consultarlo o
        # al generar sus reportes, pues sus datos ya no pueden corregirse.
        if self.is_delivered:
            return errors, warnings
        if not self.ruta_id:
            errors.append(_('Falta la ruta.'))
        if not self.pedidos_ids:
            errors.append(_('El embarque no contiene traslados.'))
            return errors, warnings

        wrong_company = self.pedidos_ids.filtered(
            lambda picking: picking.company_id != self.company_id)
        if wrong_company:
            errors.append(_('Traslados de otra compañía: %s.') % ', '.join(
                wrong_company.mapped('display_name')))
        cancelled = self.pedidos_ids.filtered(lambda picking: picking.state == 'cancel')
        if cancelled:
            errors.append(_('Traslados cancelados: %s.') % ', '.join(
                cancelled.mapped('display_name')))
        without_sale = self.pedidos_ids.filtered(lambda picking: not picking.sale_id)
        if without_sale:
            errors.append(_('Traslados sin pedido de venta: %s.') % ', '.join(
                without_sale.mapped('display_name')))

        for picking in self.pedidos_ids:
            shipping = picking.sale_id.partner_shipping_id or picking.partner_id
            if not shipping or not shipping.city_id:
                errors.append(_(
                    '%s: la dirección de entrega no tiene Ciudad. Captura una '
                    'ciudad de Odoo antes de evaluar el descuento logístico.') %
                    picking.display_name)
                continue
            destination = self._picking_destino(picking)
            if not destination:
                shipping = (
                    picking.sale_id.partner_shipping_id
                    or picking.partner_id)
                customer = self._customer_for_picking(picking)
                errors.append(_(
                    '%(picking)s no tiene destino configurado. Cliente: '
                    '%(customer)s. Dirección: %(shipping)s.') % {
                        'picking': picking.display_name,
                        'customer': customer.display_name
                        if customer else _('Sin cliente'),
                        'shipping': shipping.display_name
                        if shipping else _('Sin dirección de entrega'),
                    })
                continue
            if not destination.city_id:
                errors.append(_(
                    '%s: el destino %s no tiene Ciudad configurada. Cada ciudad '
                    'debe tener su renglón en Destinos para poder determinar el '
                    'descuento.') % (picking.display_name, destination.display_name))
                continue
            if not self.env['embarques.destino']._cities_equivalent(
                    destination.city_id, shipping.city_id):
                errors.append(_(
                    '%s: la ciudad de entrega %s no coincide con la ciudad %s '
                    'configurada en el destino %s.') % (
                        picking.display_name, shipping.city_id.display_name,
                        destination.city_id.display_name, destination.display_name))
                continue
            if not destination.zona_id:
                errors.append(_('%s: el destino %s no tiene zona.') % (
                    picking.display_name, destination.display_name))
            if not destination.discount_policy_ids:
                errors.append(_('%s: el destino %s no tiene rangos y descuentos.') % (
                    picking.display_name, destination.display_name))
        other = self.search([
            ('id', '!=', self.id), ('active', '=', True),
            ('pedidos_ids', 'in', self.pedidos_ids.ids),
        ], limit=1)
        if other:
            repeated = self.pedidos_ids & other.pedidos_ids
            errors.append(_(
                'Los traslados %s ya pertenecen al embarque activo %s.') % (
                    ', '.join(repeated.mapped('display_name')),
                    other.display_name))

        destinations = self._destinos()
        if (destinations.filtered(
                lambda destination: destination.paqueteria_estado == 'con_costo')
                and not self.company_id.paqueteria_product_id):
            errors.append(_(
                'Hay destinos con paquetería de costo, pero la compañía no '
                'tiene configurado el Producto de Paquetería.'))
        if self.productos_sin_volumen:
            warnings.append(_(
                '%s producto(s) no tienen volumen; la ocupación en m³ será '
                'menor a la real.') % self.productos_sin_volumen)
        if self.stop_count > self.consolidation_stop_limit:
            warnings.append(_(
                'El embarque tiene %s stops y la consolidación admite máximo '
                '%s. Los clientes deberán llenar su rango individualmente; '
                'no se sumarán sus cantidades.') % (
                    self.stop_count, self.consolidation_stop_limit))
        return errors, warnings

    def _check_business_configuration(self):
        self.ensure_one()
        errors, warnings = self._business_configuration_messages()
        if errors:
            raise UserError(_(
                'Corrige la configuración del embarque antes de continuar:\n\n• %s')
                % '\n• '.join(errors))
        return warnings

    def action_avanzar_embarque(self):
        all_warnings = []
        for rec in self:
            # Dar prioridad al bloqueo por cierre para no mostrar errores de
            # configuración históricos (por ejemplo, órdenes repetidos).
            rec._check_not_delivered()
            rec._assign_initial_load_orders()
            warnings = rec._check_business_configuration()
            rec.action_calculate_discount()
            siguiente = self.env['embarques.stage'].search(
                [('sequence', '>', rec.stage_id.sequence)],
                order='sequence', limit=1)
            if siguiente:
                rec.stage_id = siguiente
            all_warnings.extend('%s: %s' % (rec.display_name, warning)
                                for warning in warnings)
        if all_warnings:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Embarque avanzado con advertencias'),
                    'message': '\n'.join(all_warnings),
                    'type': 'warning',
                    'sticky': True,
                },
            }
        return True

    def action_view_traslados(self):
        self.ensure_one()
        tree = self.env.ref('embarques_module.view_picking_tree_embarque')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Traslados'),
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'views': [(tree.id, 'tree'), (False, 'form')],
            'domain': [('id', 'in', self.pedidos_ids.ids)],
        }

    def action_view_facturas(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Facturas'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.invoice_ids.ids)],
        }

    def action_view_orders(self):
        self.ensure_one()
        orders = self.pedidos_ids.mapped('sale_id')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pedidos'),
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', orders.ids)],
        }

    # ══════════════════════════════════════════════════════════════════════════
    # Validación de almacén y reportes de separación
    # ══════════════════════════════════════════════════════════════════════════

    def _preparation_rows(self):
        """Cantidades por picking/producto para validar y generar los Excel."""
        self.ensure_one()
        rows = {}
        for picking in self.pedidos_ids.sorted(lambda p: p.load_order or 0):
            for move in picking.move_ids_without_package:
                if (move.state == 'cancel' or not move.product_id
                        or not self._is_llanta(move.product_id)):
                    continue
                key = (picking.id, move.product_id.id)
                row = rows.setdefault(key, {
                    'picking': picking,
                    'product': move.product_id,
                    'ordered': 0.0,
                    'reserved': 0.0,
                    'done': 0.0,
                })
                row['ordered'] += move.product_uom_qty
                if move.state != 'done':
                    row['reserved'] += move.reserved_availability
                row['done'] += move.quantity_done
        return list(rows.values())

    def _check_preparation_ready(self):
        """Bloquea la separación si Pedido != Reservado + Hecho."""
        self.ensure_one()
        self._check_business_configuration()
        rows = self._preparation_rows()
        if not rows:
            raise UserError(_('El embarque no contiene llantas para separar.'))
        errors = []
        for row in rows:
            difference = row['ordered'] - row['reserved'] - row['done']
            if abs(difference) > 0.01:
                errors.append(_(
                    '%(picking)s · %(product)s: pedido %(ordered).2f, '
                    'reservado %(reserved).2f, hecho %(done).2f, '
                    'diferencia %(difference).2f') % {
                        'picking': row['picking'].display_name,
                        'product': row['product'].display_name,
                        'ordered': row['ordered'],
                        'reserved': row['reserved'],
                        'done': row['done'],
                        'difference': difference,
                    })
        if errors:
            visible = errors[:20]
            extra = len(errors) - len(visible)
            message = _(
                'No se puede generar el reporte porque hay diferencias entre '
                'Pedido y Reservado + Hecho:\n\n%s') % '\n'.join(visible)
            if extra:
                message += _('\n\n... y %s diferencias adicionales.') % extra
            raise UserError(message)
        return rows

    def _separation_detail_rows(self):
        """Desglosa cantidades validadas por lote, pedimento y ubicación."""
        self.ensure_one()
        rows = []
        Picking = self.env['stock.picking']
        for picking in self.pedidos_ids.sorted(lambda p: p.load_order or 0):
            for move in picking.move_ids_without_package:
                if (move.state == 'cancel' or not move.product_id
                        or not self._is_llanta(move.product_id)):
                    continue
                for line in move.move_line_ids:
                    reserved_field = (
                        'reserved_uom_qty'
                        if 'reserved_uom_qty' in line._fields
                        else 'product_uom_qty')
                    reserved = (0.0 if move.state == 'done'
                                else line[reserved_field])
                    done = line.qty_done
                    allocated = reserved + done
                    if allocated <= 0:
                        continue
                    rows.append({
                        'picking': picking,
                        'product': move.product_id,
                        'origin': picking.origin or '',
                        'ordered': allocated,
                        'reserved': reserved,
                        'done': done,
                        'lot': (line.lot_id.name or
                                (line.lot_name if 'lot_name' in line._fields else '') or ''),
                        'pedimento': Picking._pedimento_from_move_line(line),
                        'location': line.location_id.complete_name or '',
                    })
        if not rows:
            raise UserError(_(
                'No se encontraron líneas reservadas o hechas para separar.'))
        return rows

    @api.model
    def _product_brand_name(self, product):
        """Obtiene la marca sin acoplar el módulo a un addon específico."""
        candidates = (
            'product_brand_id', 'brand_id', 'marca_id',
            'product_brand', 'x_studio_marca',
        )
        for record in (product, product.product_tmpl_id):
            for field_name in candidates:
                if field_name not in record._fields:
                    continue
                value = record[field_name]
                if not value:
                    continue
                if record._fields[field_name].type == 'many2one':
                    return value.display_name
                return str(value)
        return _('Sin marca')

    @api.model
    def _product_measure_name(self, product):
        """Obtiene la medida sin depender del módulo de catálogo de llantas."""
        candidates = (
            'measure_id', 'medida_id', 'x_studio_medida', 'tire_size_id',
            'tire_size', 'size_id', 'size',
        )
        for record in (product, product.product_tmpl_id):
            for field_name in candidates:
                if field_name not in record._fields:
                    continue
                value = record[field_name]
                if not value:
                    continue
                if record._fields[field_name].type == 'many2one':
                    return value.display_name
                return str(value)

        attribute_values = getattr(
            product, 'product_template_attribute_value_ids', False)
        for value in attribute_values or self.env[
                'product.template.attribute.value']:
            attribute_name = (value.attribute_id.name or '').casefold()
            if any(label in attribute_name for label in (
                    'medida', 'size', 'talla')):
                return value.name
        return _('Sin medida')

    @api.model
    def _natural_measure_key(self, measure):
        normalized = unicodedata.normalize('NFKD', measure or '')
        normalized = ''.join(
            char for char in normalized
            if not unicodedata.combining(char)).casefold()
        parts = re.split(r'(\d+(?:\.\d+)?)', normalized)
        return tuple(
            (0, float(part)) if re.fullmatch(r'\d+(?:\.\d+)?', part)
            else (1, part)
            for part in parts if part)

    def _xlsx_report(self, by_customer=False):
        self.ensure_one()
        self._check_preparation_ready()
        rows = self._separation_detail_rows()
        try:
            import xlsxwriter
        except ImportError as error:
            raise UserError(_(
                'El servidor no tiene instalada la biblioteca xlsxwriter.')) from error

        grouped = {}
        brand_order = {}
        customer_order = {}
        customer_brand_order = {}
        for row in rows:
            picking = row['picking']
            product = row['product']
            brand = self._product_brand_name(product)
            measure = self._product_measure_name(product)
            if brand not in brand_order:
                brand_order[brand] = len(brand_order)
            customer = picking.partner_id.display_name if by_customer else ''
            if customer not in customer_order:
                customer_order[customer] = len(customer_order)
            customer_brand_key = (customer, brand)
            if customer_brand_key not in customer_brand_order:
                customer_brand_order[customer_brand_key] = len(
                    customer_brand_order)
            order = picking.sale_id.name if by_customer else ''
            invoices = picking.invoice_names if by_customer else ''
            key = (brand, measure, customer, order, invoices,
                   picking.id if by_customer else False,
                   row['origin'], product.id,
                   row['lot'], row['pedimento'], row['location'])
            if key in grouped:
                target = grouped[key]
                target['ordered'] += row['ordered']
                target['reserved'] += row['reserved']
                target['done'] += row['done']
            else:
                grouped[key] = dict(
                    row, brand=brand, measure=measure, customer=customer,
                    order=order, invoices=invoices)

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Separación')
        title = workbook.add_format({
            'bold': True, 'font_size': 16, 'font_color': '#000000',
            'bottom': 2, 'bottom_color': '#000000',
            'align': 'center', 'valign': 'vcenter'})
        header = workbook.add_format({
            'bold': True, 'font_color': '#000000', 'bg_color': '#E6E6E6',
            'top': 1, 'bottom': 1, 'left': 0, 'right': 0,
            'align': 'center', 'valign': 'vcenter'})

        # 0 = renglón normal, 1 = nueva marca, 2 = nuevo cliente/marca.
        text_formats = {}
        label_formats = {}
        number_formats = {}
        check_formats = {}
        for level in (0, 1, 2):
            base = {
                'bottom': 1, 'bottom_color': '#D9D9D9',
                'valign': 'top',
            }
            if level:
                base.update({'top': level, 'top_color': '#666666'})
            text_formats[level] = workbook.add_format(dict(base))
            label_formats[level] = workbook.add_format(dict(base, bold=True))
            number_formats[level] = workbook.add_format(dict(
                base, num_format='#,##0.00', align='right'))
            check_formats[level] = workbook.add_format(dict(
                base, font_size=18, align='center', valign='vcenter'))

        columns = ['Marca', 'Medida']
        if by_customer:
            columns += ['Cliente', 'Pedido', 'Facturas']
        columns += [
            'Origen', 'Código', 'Producto', 'Lote', 'Pedimento', 'Ubicación origen',
            'Pedido', 'Reservado', 'Hecho']
        if by_customer:
            columns.append('Revisado')
        sheet.merge_range(0, 0, 0, len(columns) - 1,
                          '%s · %s' % (self.name, _('Reporte de separación')),
                          title)
        sheet.set_row(0, 26)
        for col, label in enumerate(columns):
            sheet.write(2, col, label, header)

        if by_customer:
            # Conserva el orden de cliente y marca del embarque; dentro de cada
            # bloque ordena por medida.
            ordered_rows = sorted(grouped.values(), key=lambda item: (
                customer_order[item['customer']],
                customer_brand_order[(item['customer'], item['brand'])],
                self._natural_measure_key(item['measure'])))
        else:
            # Agrupa por marca según su primera aparición en el embarque.
            # Dentro de cada marca presenta las medidas en orden natural.
            ordered_rows = sorted(
                grouped.values(), key=lambda item: (
                    brand_order[item['brand']],
                    self._natural_measure_key(item['measure'])))
        previous_customer = previous_brand = previous_measure = None
        for row_index, row in enumerate(ordered_rows, 3):
            customer_changed = bool(
                by_customer and row['customer'] != previous_customer)
            brand_changed = bool(
                customer_changed or row['brand'] != previous_brand)
            measure_changed = bool(
                brand_changed or row['measure'] != previous_measure)
            separator_level = (
                2 if customer_changed or (not by_customer and brand_changed)
                else 1 if brand_changed or measure_changed else 0)
            values = [row['brand'], row['measure']]
            if by_customer:
                values += [row['customer'], row['order'], row['invoices']]
            values += [
                row['origin'], row['product'].default_code or '',
                row['product'].display_name,
                row['lot'], row['pedimento'], row['location']]
            for col, value in enumerate(values):
                is_label = col in (0, 1) or (by_customer and col == 2)
                fmt = (label_formats if is_label else text_formats)[separator_level]
                sheet.write(row_index, col, value, fmt)
            start = len(values)
            number_fmt = number_formats[separator_level]
            sheet.write_number(row_index, start, row['ordered'], number_fmt)
            sheet.write_number(row_index, start + 1, row['reserved'], number_fmt)
            sheet.write_number(row_index, start + 2, row['done'], number_fmt)
            if by_customer:
                sheet.write(row_index, start + 3, '□',
                            check_formats[separator_level])
                sheet.set_row(row_index, 24)
            previous_customer = row['customer']
            previous_brand = row['brand']
            previous_measure = row['measure']

        sheet.freeze_panes(3, 0)
        sheet.autofilter(2, 0, max(3, len(ordered_rows) + 2), len(columns) - 1)
        widths = ([18, 18] + ([28, 16, 24] if by_customer else [])
                  + [18, 16, 48, 18, 24, 34, 14, 14, 14]
                  + ([11] if by_customer else []))
        for index, width in enumerate(widths):
            sheet.set_column(index, index, width)
        sheet.hide_gridlines(2)
        sheet.set_landscape()
        sheet.fit_to_pages(1, 0)
        sheet.repeat_rows(0, 2)
        sheet.set_margins(left=0.25, right=0.25, top=0.45, bottom=0.45)
        # No se invoca print_black_and_white/set_black_and_white: esos métodos
        # no existen en todas las versiones de xlsxwriter usadas por Odoo 16.
        # El libro ya contiene exclusivamente negro, blanco y grises.
        sheet.set_footer(_('Página &P de &N'))
        workbook.close()
        output.seek(0)

        suffix = 'marca_cliente' if by_customer else 'marca'
        filename = '%s_separacion_%s.xlsx' % (self.name.replace('/', '_'), suffix)
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }

    def action_xlsx_by_brand(self):
        return self._xlsx_report(by_customer=False)

    def action_xlsx_by_brand_customer(self):
        return self._xlsx_report(by_customer=True)

    def action_aplicar_descuento_facturas(self):
        """Genera/sincroniza la NC logística separada de las facturas.

        Se conserva el nombre técnico de la acción para no romper vistas ni
        accesos existentes, pero ya no modifica ``discount`` en las líneas.
        """
        facturas = self.mapped('invoice_ids').filtered(
            lambda m: m.move_type == 'out_invoice' and m.state != 'cancel')
        facturas.action_generate_embarque_logistic_nc()
        return True
