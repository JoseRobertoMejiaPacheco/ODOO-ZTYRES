import unicodedata

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    embarque_ids = fields.Many2many(
        'embarques.embarques', string='Embarques',
        compute='_compute_embarque_ids')

    embarque_discount_percentage = fields.Float(
        string='Descuento de Embarque (%)', readonly=True, copy=False,
        tracking=True, digits=(16, 2),
        help='Lo fija el embarque. Se aplica sobre las líneas al generar la '
             'factura.')

    # ── Paquetería ────────────────────────────────────────────────────────────
    destino_id = fields.Many2one(
        'embarques.destino', string='Destino Detectado',
        compute='_compute_destino', readonly=True)
    piezas_qty = fields.Float(
        string='Piezas', compute='_compute_destino', readonly=True)

    @api.depends('picking_ids')
    def _compute_embarque_ids(self):
        for order in self:
            order.embarque_ids = order.picking_ids.mapped('embarque_ids')

    @api.depends('partner_shipping_id', 'partner_shipping_id.city_id',
                 'partner_shipping_id.state_id',
                 'partner_shipping_id.l10n_mx_edi_locality_id',
                 'partner_id.city_id', 'partner_id.state_id',
                 'partner_id.l10n_mx_edi_locality_id',
                 'order_line.product_uom_qty',
                 'order_line.product_id')
    def _compute_destino(self):
        Destino = self.env['embarques.destino']
        for order in self:
            partner = order.partner_shipping_id or order.partner_id
            order.destino_id = Destino._match_partner(
                partner, company=order.company_id)
            order.piezas_qty = order._piezas_qty()


    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        if self.embarque_ids and 'use_embarque_logistic_nc' in self._fields:
            vals['use_embarque_logistic_nc'] = True
        return vals

    def _piezas_qty(self):
        """Piezas del pedido, sin contar la línea de paquetería ni servicios."""
        self.ensure_one()
        producto = self.company_id.paqueteria_product_id
        return sum(
            line.product_uom_qty
            for line in self.order_line
            if line.product_id
            and line.product_id.type in ('product', 'consu')
            and line.product_id != producto
        )

    @api.model
    def _normalizar_forma_entrega(self, value):
        """Texto comparable para valores/etiquetas de la forma de entrega."""
        text = unicodedata.normalize('NFKD', str(value or ''))
        return ' '.join(
            ''.join(char for char in text if not unicodedata.combining(char))
            .lower().replace('_', ' ').replace('-', ' ').split())

    def _es_entrega_por_cuenta_del_cliente(self):
        """Detecta las dos formas de entrega que nunca pagan paquetería.

        En la base de ZTYRES la forma de entrega es un campo personalizado. Se
        localiza por su nombre técnico/etiqueta para no duplicarlo ni obligar a
        renombrar la personalización existente.
        """
        self.ensure_one()
        keywords = (
            'envio', 'entrega', 'paqueteria', 'recoge', 'recoje',
            'recoleccion', 'delivery', 'shipping')
        excluded = {
            'cliente recoge',
            'cliente recoje',
            'paqueteria del cliente',
            'paqueteria cliente',
            'vendedor lleva',
        }

        records = self | self.env['sale.order']
        records_to_check = (records, self.partner_id,
                            self.partner_shipping_id)
        for record in records_to_check:
            if not record:
                continue
            for field_name, field in record._fields.items():
                field_label = self._normalizar_forma_entrega(field.string)
                technical_name = self._normalizar_forma_entrega(field_name)
                if not any(word in technical_name or word in field_label
                           for word in keywords):
                    continue
                value = record[field_name]
                candidates = []
                if field.type == 'selection':
                    selection = field._description_selection(self.env)
                    selection_map = dict(selection)
                    candidates.extend((value, selection_map.get(value)))
                elif field.type == 'many2one':
                    candidates.append(value.display_name if value else '')
                elif field.type in ('char', 'text'):
                    candidates.append(value)
                for candidate in candidates:
                    if self._normalizar_forma_entrega(candidate) in excluded:
                        return True
        return False

    @api.model
    def _es_campo_forma_entrega(self, field_name):
        field = self._fields.get(field_name)
        if not field:
            return False
        text = '%s %s' % (
            self._normalizar_forma_entrega(field_name),
            self._normalizar_forma_entrega(field.string))
        return any(word in text for word in (
            'envio', 'entrega', 'paqueteria', 'recoge', 'recoje',
            'recoleccion', 'delivery', 'shipping'))

    def _update_paqueteria_line(self):
        """Crea, actualiza o quita la línea de paquetería del pedido.

        Sólo toca presupuestos abiertos: una vez confirmado el pedido, cambiar
        importes por debajo llevaría a facturar algo distinto de lo acordado.
        """
        for order in self:
            if order.state not in ('draft', 'sent'):
                continue
            producto = order.company_id.paqueteria_product_id
            linea = order.order_line.filtered(
                lambda l: producto and l.product_id == producto)

            destino = order.destino_id
            piezas = order._piezas_qty()
            entrega_cliente = order._es_entrega_por_cuenta_del_cliente()
            unitario = (
                destino._paqueteria_unit_cost(piezas)
                if destino and not entrega_cliente else 0.0)

            if not producto or not unitario:
                if linea:
                    linea.unlink()
                continue

            vals = {
                'product_id': producto.id,
                'name': _('Paquetería — %s') % (destino.name or ''),
                'product_uom_qty': piezas,
                'price_unit': unitario,
                'tax_id': [(6, 0, producto.taxes_id.ids)],
            }
            if linea:
                linea[0].write(vals)
                (linea - linea[0]).unlink()
            else:
                order.order_line = [(0, 0, dict(vals, order_id=order.id))]
        return True


    # ── Disparadores ──────────────────────────────────────────────────────────
    # Se recalcula al cambiar líneas o dirección de entrega. El guard de
    # contexto evita el ciclo: escribir la línea de paquetería vuelve a
    # disparar el write del pedido.

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders.with_context(paqueteria_update=True)._update_paqueteria_line()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if 'embarque_discount_percentage' in vals and hasattr(self, '_compute_embarque_logistic_amounts'):
            # El porcentaje no forma parte de @api.depends en discount_profiles
            # porque ese módulo debe seguir instalable sin Embarques. Forzamos
            # aquí la actualización del monto nuevo para cotización/OV.
            self._compute_embarque_logistic_amounts()
        if self.env.context.get('paqueteria_update'):
            return res
        delivery_changed = any(
            self._es_campo_forma_entrega(name) for name in vals)
        if (delivery_changed
                or {'order_line', 'partner_shipping_id', 'partner_id'} & set(vals)):
            self.with_context(paqueteria_update=True)._update_paqueteria_line()
        return res

    def action_recalcular_paqueteria(self):
        return self.with_context(paqueteria_update=True)._update_paqueteria_line()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _es_linea_paqueteria(self):
        self.ensure_one()
        producto = self.order_id.company_id.paqueteria_product_id
        return bool(producto) and self.product_id == producto

    def _refresh_paqueteria(self, orders):
        if self.env.context.get('paqueteria_update'):
            return
        orders = orders.filtered(lambda o: o.state in ('draft', 'sent'))
        if orders:
            orders.with_context(paqueteria_update=True)._update_paqueteria_line()

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._refresh_paqueteria(lines.mapped('order_id'))
        return lines

    def write(self, vals):
        res = super().write(vals)
        if {'product_id', 'product_uom_qty'} & set(vals):
            self._refresh_paqueteria(self.mapped('order_id'))
        return res

    def unlink(self):
        orders = self.mapped('order_id')
        res = super().unlink()
        self._refresh_paqueteria(orders)
        return res

    @api.model
    def _combine_discounts(self, base, extra):
        """Combina el descuento propio de la línea con el del embarque.

        Suma simple, topada a 100. Para descuento en cascada:

            return 100.0 * (1 - (1 - base / 100.0) * (1 - extra / 100.0))
        """
        return min(100.0, (base or 0.0) + (extra or 0.0))

    def _prepare_invoice_line(self, **optional_values):
        """Conserva la factura SIN descuento logístico en la línea.

        El porcentaje queda como trazabilidad; el importe se entrega mediante
        una NC separada creada por ``account.move``.
        """
        vals = super()._prepare_invoice_line(**optional_values)
        if self.is_downpayment or self._es_linea_paqueteria():
            return vals
        if self.order_id.embarque_ids:
            percentage = self.order_id.embarque_discount_percentage or 0.0
            # IMPORTANTE: el porcentaje logístico NUNCA se suma al campo
            # estándar `discount` de la factura. Ese campo conserva únicamente
            # el descuento comercial que ya tenía la línea de venta.
            base_discount = vals.get('discount', self.discount) or 0.0
            vals['discount'] = base_discount
            vals.update({
                'embarque_base_discount': base_discount,
                'embarque_base_discount_set': True,
                'embarque_discount_percentage': percentage,
                'embarque_discount_amount': 0.0,
                'embarque_discount_applied': False,
                'embarque_original_percentage': percentage,
            })
        return vals

    def _create_invoices(self, grouped=False, final=False, date=None):
        """Cubre también el botón estándar **Crear facturas**.

        Odoo puede agrupar varios pedidos en una misma factura. Se espera a que
        ``super`` termine y luego se genera una sola NC logística por factura.
        """
        invoices = super()._create_invoices(
            grouped=grouped, final=final, date=date)
        invoices.filtered(
            lambda move: move.move_type == 'out_invoice' and move.embarque_ids
        )._ensure_embarque_logistic_nc(rebuild=True)
        return invoices
