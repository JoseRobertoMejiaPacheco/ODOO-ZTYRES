from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Se conservan los campos de línea por compatibilidad con facturas creadas
    # por versiones anteriores del módulo. El flujo nuevo NO modifica discount.
    embarque_discount_percentage = fields.Float(
        string='% Descuento Logístico', readonly=True, copy=False,
        digits=(16, 2))
    embarque_discount_amount = fields.Monetary(
        string='Monto Descuento Logístico', readonly=True, copy=False,
        currency_field='currency_id')
    embarque_discount_applied = fields.Boolean(
        string='Descuento de Embarque Aplicado', readonly=True, copy=False)
    embarque_base_discount = fields.Float(
        string='Descuento Base antes de Embarque', readonly=True, copy=False,
        digits=(16, 6))
    embarque_base_discount_set = fields.Boolean(
        string='Base de Descuento Guardada', readonly=True, copy=False)
    embarque_source_line_id = fields.Many2one(
        'account.move.line', string='Línea de Factura Origen', readonly=True,
        copy=False, ondelete='set null')
    embarque_original_percentage = fields.Float(
        string='% Logístico Original', readonly=True, copy=False,
        digits=(16, 2))


class AccountMove(models.Model):
    _inherit = 'account.move'

    embarque_discount_percentage = fields.Float(
        string='Descuento de Embarque (%)',
        compute='_compute_embarque_discount', store=True, readonly=True,
        copy=False, digits=(16, 2))
    embarque_discount_summary = fields.Char(
        string='Descuentos de Embarque', compute='_compute_embarque_discount',
        store=True, readonly=True, copy=False)
    embarque_discount_amount = fields.Monetary(
        string='Total Descuento Logístico', compute='_compute_embarque_discount',
        store=True, readonly=True, copy=False, currency_field='currency_id')
    embarque_ids = fields.Many2many(
        'embarques.embarques', string='Embarques', compute='_compute_embarque_ids')

    embarque_logistic_nc_id = fields.Many2one(
        'account.move', string='NC Logística de Embarque', readonly=True,
        copy=False, ondelete='set null')
    embarque_logistic_invoice_id = fields.Many2one(
        'account.move', string='Factura de NC Logística', readonly=True,
        copy=False, ondelete='set null', index=True)
    embarque_logistic_nc_new_flow = fields.Boolean(
        string='NC Logística por Embarque', readonly=True, copy=False,
        help='Identifica documentos que usan el flujo nuevo. Los documentos '
             'históricos conservan intacto el esquema anterior.')
    embarque_logistic_stamp_error = fields.Char(
        string='Error Timbrado NC Logística', readonly=True, copy=False)

    @api.depends(
        'invoice_line_ids.price_subtotal',
        'invoice_line_ids.sale_line_ids.order_id.embarque_discount_percentage',
        'invoice_line_ids.sale_line_ids.order_id.embarque_ids',
        'move_type')
    def _compute_embarque_discount(self):
        for move in self:
            if move.move_type != 'out_invoice':
                move.embarque_discount_percentage = 0.0
                move.embarque_discount_summary = False
                move.embarque_discount_amount = 0.0
                continue
            percentages = []
            amount = 0.0
            for line in move.invoice_line_ids.filtered(
                    lambda l: l.display_type in (False, 'product') and l.sale_line_ids):
                orders = line.sale_line_ids.mapped('order_id').filtered('embarque_ids')
                if not orders:
                    continue
                values = set(orders.mapped('embarque_discount_percentage'))
                if len(values) == 1:
                    percentage = values.pop() or 0.0
                    percentages.append(percentage)
                    amount += abs(line.price_subtotal) * percentage / 100.0
            unique = sorted(set(percentages))
            move.embarque_discount_percentage = unique[0] if len(unique) == 1 else 0.0
            move.embarque_discount_summary = ', '.join(
                '%.2f%%' % value for value in unique)
            move.embarque_discount_amount = move.currency_id.round(amount)
        if hasattr(self, '_compute_embarque_logistic_amounts'):
            # Recalcula el monto fiscal nuevo cuando cambia el porcentaje
            # heredado de las OV, incluyendo facturación agrupada/parcial.
            self._compute_embarque_logistic_amounts()

    def _compute_embarque_ids(self):
        for move in self:
            move.embarque_ids = move.invoice_line_ids.mapped(
                'sale_line_ids.order_id.embarque_ids')

    def _embarque_is_logistic_candidate(self, embarque):
        """Sólo aplica NC logística desde la etapa En Proceso en adelante."""
        process_stage = self.env.ref(
            'embarques_module.stage_proceso', raise_if_not_found=False)
        if not process_stage or not embarque or not embarque.stage_id:
            return False
        return embarque.stage_id.sequence >= process_stage.sequence

    def _logistic_percentage_for_invoice_line(self, line):
        """Porcentaje logístico real aplicable a una línea de factura.

        La fuente primaria es el picking que pertenece al embarque, porque ahí
        es donde se calcula/autorizada la política logística. El porcentaje
        propagado a ``sale.order`` queda sólo como respaldo.
        """
        self.ensure_one()
        sale_lines = line.sale_line_ids.filtered(
            lambda sale_line: not sale_line.is_downpayment
            and not sale_line._es_linea_paqueteria())
        if not sale_lines:
            return False
        if sale_lines != line.sale_line_ids:
            raise UserError(_(
                'La línea "%s" mezcla mercancía con anticipo o paquetería. '
                'Sepárala antes de generar la NC logística.') % line.name)

        orders = sale_lines.mapped('order_id')
        percentages = set()
        has_candidate = False

        for order in orders:
            # Fuente de verdad: traslados/pickings del pedido que están dentro
            # de un embarque En Proceso o posterior.
            candidate_pickings = order.picking_ids.filtered(
                lambda picking: any(
                    self._embarque_is_logistic_candidate(embarque)
                    for embarque in picking.embarque_ids))
            if candidate_pickings:
                has_candidate = True
                picking_percentages = set(
                    candidate_pickings.mapped('embarque_discount_percentage'))
                percentages.update(picking_percentages)
                continue

            # Respaldo para documentos donde el vínculo al picking no esté
            # disponible pero el pedido sí conserve el embarque/porcentaje.
            candidate_embarques = order.embarque_ids.filtered(
                lambda embarque: self._embarque_is_logistic_candidate(embarque))
            if candidate_embarques:
                has_candidate = True
                percentages.add(order.embarque_discount_percentage or 0.0)

        if not has_candidate:
            return False

        return percentages.pop() if percentages else 0.0

    def _requires_embarque_logistic_nc(self):
        """Verdadero cuando la factura contiene mercancía con % logístico.

        No depende de ``embarque_discount_amount`` almacenado. La fuente de
        verdad son las líneas facturadas, el porcentaje propagado desde los
        pedidos y que su embarque esté al menos en ``En Proceso``. También
        funciona con facturas agrupadas y parciales.
        """
        self.ensure_one()
        if self.move_type != 'out_invoice':
            return False
        for line in self.invoice_line_ids.filtered(
                lambda l: l.display_type in (False, 'product') and l.sale_line_ids):
            percentage = self._logistic_percentage_for_invoice_line(line)
            if percentage is not False and percentage > 0.0:
                return True
        return False

    def _embarque_logistic_nc_groups(self):
        """Bases de la NC agrupadas exactamente igual que sus líneas fiscales.

        No redondeamos por línea de factura. Se acumula primero por conjunto de
        impuestos y sólo después se redondea cada línea que realmente tendrá la
        NC. Esto evita diferencias de centavos entre el resumen y el CFDI.
        """
        self.ensure_one()
        groups = {}
        for line in self.invoice_line_ids.filtered(
                lambda l: l.display_type in (False, 'product') and l.sale_line_ids):
            percentage = self._logistic_percentage_for_invoice_line(line)
            if percentage is False or not percentage:
                continue
            amount = abs(line.price_subtotal) * percentage / 100.0
            if not amount:
                continue
            tax_ids = tuple(sorted(line.tax_ids.ids))
            groups[tax_ids] = groups.get(tax_ids, 0.0) + amount
        return groups

    def _get_embarque_logistic_nc_totals(self):
        """(sin IVA, con IVA) usando el MISMO redondeo que la NC."""
        self.ensure_one()
        groups = self._embarque_logistic_nc_groups()
        currency = self.currency_id
        product = self.company_id.embarque_logistic_nc_product_id
        untaxed = total = 0.0
        for tax_ids, raw_amount in groups.items():
            amount = currency.round(raw_amount) if currency else raw_amount
            untaxed += amount
            taxes = self.env['account.tax'].browse(list(tax_ids))
            if taxes:
                tax_result = taxes.compute_all(
                    amount, currency=currency, quantity=1.0,
                    product=product, partner=self.partner_id)
                total += tax_result['total_included']
            else:
                total += amount
        if currency:
            untaxed = currency.round(untaxed)
            total = currency.round(total)
        return untaxed, total

    def _prepare_embarque_logistic_nc_lines(self):
        """Agrupa el descuento por impuestos para que la NC replique el IVA."""
        self.ensure_one()
        groups = self._embarque_logistic_nc_groups()
        result = []
        product = self.company_id.embarque_logistic_nc_product_id
        if groups and not product:
            raise UserError(_(
                'Configura el Producto para NC Logística en la compañía %s '
                'antes de facturar el embarque.') % self.company_id.display_name)
        for tax_ids, amount in groups.items():
            result.append((0, 0, {
                'product_id': product.id,
                'name': _('Descuento Logístico de Embarque'),
                'quantity': 1.0,
                'price_unit': self.currency_id.round(amount),
                'tax_ids': [(6, 0, list(tax_ids))],
            }))
        return result

    def _emb_receiver_rfc(self):
        """RFC receptor REAL de la factura origen, obtenido de su CFDI."""
        self.ensure_one()
        if 'edi_vat_receptor' not in self._fields:
            return False
        receiver = (self.edi_vat_receptor or '').strip().upper()
        if not receiver or receiver == 'SIN XML ADJUNTO':
            return False
        return receiver

    def _validate_effective_receiver(self):
        """Indica si ya conocemos UUID y receptor del CFDI origen."""
        self.ensure_one()
        if self.state != 'posted':
            return True
        if ('l10n_mx_edi_cfdi_uuid' in self._fields
                and not self.l10n_mx_edi_cfdi_uuid):
            return False
        return bool(self._emb_receiver_rfc())

    def _prepare_embarque_logistic_nc_vals(self):
        self.ensure_one()
        lines = self._prepare_embarque_logistic_nc_lines()
        if not lines:
            return False
        vals = {
            'move_type': 'out_refund',
            'partner_id': self.partner_id.id,
            'partner_shipping_id': self.partner_shipping_id.id or self.partner_id.id,
            'currency_id': self.currency_id.id,
            'journal_id': self.journal_id.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_origin': self.name or self.ref or self.invoice_origin,
            'ref': _('NC logística de %s') % (self.name or self.display_name),
            'invoice_line_ids': lines,
            'embarque_logistic_invoice_id': self.id,
            'embarque_logistic_nc_new_flow': True,
            # Relación contable/CFDI real con la factura origen. El módulo
            # ztyres_timbrado_generico consulta reversed_entry_id y su XML para
            # determinar el receptor de la nota de crédito.
            'reversed_entry_id': self.id,
        }
        receiver = self._emb_receiver_rfc()
        if 'generic_edi' in self._fields:
            # NO se toma generic_edi como fuente. Se deriva del RFC receptor
            # efectivamente timbrado en la factura origen.
            vals['generic_edi'] = receiver == 'XAXX010101000' if receiver else False
        if 'l10n_mx_edi_usage' in self._fields:
            vals['l10n_mx_edi_usage'] = 'S01' if receiver == 'XAXX010101000' else 'G02'
        if 'x_studio_tipo' in self._fields:
            vals['x_studio_tipo'] = 'Bonificación'
        return vals

    def _restore_legacy_embarque_line_discounts(self):
        """Quita de borradores el logístico aplicado por versiones viejas.

        El flujo anterior sumaba el porcentaje logístico a `line.discount`.
        Sólo se corrigen líneas que tienen la marca histórica
        `embarque_discount_applied` y su `embarque_base_discount` guardado.
        Nunca se modifica una factura publicada ni un descuento comercial
        normal.
        """
        for invoice in self.filtered(
                lambda m: m.move_type == 'out_invoice' and m.state == 'draft'):
            for line in invoice.invoice_line_ids.filtered(
                    lambda l: l.display_type in (False, 'product')
                    and l.embarque_discount_applied
                    and l.embarque_base_discount_set):
                line.sudo().write({
                    'discount': line.embarque_base_discount or 0.0,
                    'embarque_discount_amount': 0.0,
                    'embarque_discount_applied': False,
                })
        return True

    def _ensure_embarque_logistic_nc(self, rebuild=False):
        """Crea/actualiza en borrador la NC logística del flujo nuevo."""
        for invoice in self.filtered(
                lambda m: m.move_type == 'out_invoice'
                and m._requires_embarque_logistic_nc()):
            # Si el borrador nació con una versión anterior que materializaba
            # el logístico en `discount`, se restaura primero el descuento
            # comercial original. La NC se calcula después sobre la factura
            # ya limpia.
            invoice._restore_legacy_embarque_line_discounts()
            if 'use_embarque_logistic_nc' in invoice._fields and not invoice.use_embarque_logistic_nc:
                invoice.sudo().write({'use_embarque_logistic_nc': True})
            if invoice.state not in ('draft', 'posted'):
                continue
            invoice._validate_effective_receiver()
            existing = invoice.embarque_logistic_nc_id
            if not existing:
                existing = self.env['account.move'].sudo().search([
                    ('embarque_logistic_invoice_id', '=', invoice.id),
                    ('state', '!=', 'cancel'),
                ], order='id desc', limit=1)
                if existing:
                    invoice.sudo().write({'embarque_logistic_nc_id': existing.id})
            if existing and existing.state == 'cancel':
                existing = self.env['account.move']
            if rebuild and existing and existing.state == 'draft':
                existing.with_context(force_delete=True).unlink()
                existing = self.env['account.move']
                invoice.embarque_logistic_nc_id = False
            vals = invoice._prepare_embarque_logistic_nc_vals()
            if not vals:
                if existing and existing.state == 'draft':
                    existing.with_context(force_delete=True).unlink()
                    invoice.embarque_logistic_nc_id = False
                continue
            if not existing:
                nc = self.env['account.move'].sudo().with_context(
                    default_move_type='out_refund').create(vals)
                invoice.sudo().write({
                    'embarque_logistic_nc_id': nc.id,
                    'embarque_logistic_nc_new_flow': True,
                })
            elif existing.state == 'draft':
                # Al publicar se reconstruye para reflejar exactamente la factura.
                if rebuild:
                    existing.write(vals)
        return True

    def _post_and_apply_embarque_logistic_nc(self):
        """Publica y aplica la NC al confirmar; timbra cuando el origen tenga CFDI.

        La creación/publicación/conciliación NO espera al UUID de la factura,
        igual que el flujo histórico de BS. El UUID sólo es requisito para
        completar los datos fiscales y timbrar la NC.
        """
        for invoice in self.filtered(
                lambda m: m.move_type == 'out_invoice'
                and m.state == 'posted'
                and m._requires_embarque_logistic_nc()):
            nc = invoice.embarque_logistic_nc_id
            if not nc:
                continue

            receiver_ready = invoice._validate_effective_receiver()
            receiver = invoice._emb_receiver_rfc() if receiver_ready else False
            vals = {}
            if 'reversed_entry_id' in nc._fields and nc.reversed_entry_id != invoice:
                vals['reversed_entry_id'] = invoice.id
            if receiver_ready:
                vals['embarque_logistic_stamp_error'] = False
                if 'generic_edi' in nc._fields:
                    vals['generic_edi'] = receiver == 'XAXX010101000'
                if 'l10n_mx_edi_usage' in nc._fields:
                    vals['l10n_mx_edi_usage'] = (
                        'S01' if receiver == 'XAXX010101000' else 'G02')
                if ('l10n_mx_edi_origin' in nc._fields
                        and 'l10n_mx_edi_cfdi_uuid' in invoice._fields
                        and invoice.l10n_mx_edi_cfdi_uuid):
                    vals['l10n_mx_edi_origin'] = (
                        '01|%s' % invoice.l10n_mx_edi_cfdi_uuid)
            elif not nc.embarque_logistic_stamp_error:
                vals['embarque_logistic_stamp_error'] = _(
                    'NC generada y aplicada. Pendiente de timbrar hasta que la '
                    'factura origen tenga UUID y RFC receptor.')
            if vals:
                nc.sudo().write(vals)

            # Igual que BS: al confirmar la factura se publica la NC y se aplica
            # contablemente de inmediato.
            if nc.state == 'draft':
                nc.sudo().action_post()

            invoice_receivable = invoice.line_ids.filtered(
                lambda l: l.account_type == 'asset_receivable' and not l.reconciled)
            nc_receivable = nc.line_ids.filtered(
                lambda l: l.account_type == 'asset_receivable' and not l.reconciled)
            if invoice_receivable and nc_receivable:
                (invoice_receivable | nc_receivable).sudo().reconcile()

            # El timbrado fiscal espera a que exista el CFDI de la factura origen.
            if (receiver_ready
                    and 'l10n_mx_edi_cfdi_uuid' in nc._fields
                    and not nc.l10n_mx_edi_cfdi_uuid
                    and hasattr(nc, 'action_process_edi_web_services')):
                try:
                    with self.env.cr.savepoint():
                        nc.sudo().action_process_edi_web_services(with_commit=False)
                except Exception as error:
                    nc.sudo().write({
                        'embarque_logistic_stamp_error': str(error)[:500]
                    })
                nc.invalidate_recordset(['l10n_mx_edi_cfdi_uuid'])

            if (receiver_ready
                    and 'l10n_mx_edi_cfdi_uuid' in nc._fields
                    and not nc.l10n_mx_edi_cfdi_uuid
                    and not nc.embarque_logistic_stamp_error):
                edi_errors = nc.edi_document_ids.filtered(
                    lambda d: d.blocking_level == 'error')
                error_text = '; '.join(filter(None, edi_errors.mapped('error')))
                nc.sudo().write({
                    'embarque_logistic_stamp_error':
                        (error_text or _(
                            'La NC fue publicada pero el PAC no devolvió UUID.'))[:500]
                })
        return True

    def generate_and_apply_nc(self):
        """Genera BS y logística como DOS notas de crédito independientes.

        ``ztyres_timbrado_generico`` llama este método al confirmar la factura.
        Conservamos intacta la NC de BS del módulo ``discount_profiles`` y,
        justo después, generamos/publicamos/aplicamos una segunda NC logística
        para las facturas cuyo picking ya pertenece a un embarque candidato.
        """
        result = super().generate_and_apply_nc()
        candidates = self.filtered(
            lambda move: move.move_type == 'out_invoice'
            and move.state == 'posted'
            and move._requires_embarque_logistic_nc())
        if candidates:
            candidates._ensure_embarque_logistic_nc(rebuild=True)
            candidates._post_and_apply_embarque_logistic_nc()
        return result

    def action_generate_embarque_logistic_nc(self):
        """Acción manual idempotente desde factura/embarque para diagnóstico."""
        self.filtered(lambda m: m.state == 'draft')._ensure_embarque_logistic_nc(
            rebuild=True)
        self.filtered(lambda m: m.state == 'posted')._ensure_embarque_logistic_nc()
        self.filtered(lambda m: m.state == 'posted')._post_and_apply_embarque_logistic_nc()
        return True

    def action_process_edi_web_services(self, with_commit=True):
        """Continúa automáticamente con la NC al terminar el CFDI origen.

        En ZTYRES el UUID de la factura se obtiene en este método, no
        necesariamente dentro de ``action_post``. Por eso el intento anterior
        podía quedarse con una NC borrador y el embarque sin detectarla.
        """
        result = super().action_process_edi_web_services(with_commit=with_commit)

        invoices = self.filtered(
            lambda m: m.move_type == 'out_invoice'
            and m.state == 'posted'
            and m._requires_embarque_logistic_nc()
            and (
                'l10n_mx_edi_cfdi_uuid' not in m._fields
                or bool(m.l10n_mx_edi_cfdi_uuid)
            )
        )
        if invoices:
            # Por factura: una factura consolidada produce una NC; si los
            # pedidos se facturan separados, cada factura produce su propia NC.
            invoices._ensure_embarque_logistic_nc()
            invoices._post_and_apply_embarque_logistic_nc()
        return result

    def action_post(self):
        invoices = self.filtered(
            lambda m: m.state == 'draft'
            and m.move_type == 'out_invoice')
        result = super().action_post()
        # Disparador principal: al confirmar/publicar la factura. No importa
        # desde qué pantalla o flujo se creó la factura. Si el pedido está en
        # un embarque En Proceso (o posterior) con porcentaje logístico, aquí
        # se crea, publica y aplica UNA NC por factura.
        candidates = invoices.filtered(
            lambda m: m._requires_embarque_logistic_nc())
        candidates._ensure_embarque_logistic_nc(rebuild=True)
        candidates._post_and_apply_embarque_logistic_nc()
        return result
