# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools import float_compare
from odoo.exceptions import ValidationError, UserError
from odoo.exceptions import ValidationError
from odoo import api, _
from odoo.tools.float_utils import float_compare

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    
    single_dot = fields.Char(string="DOT")
    lots_ids = fields.Many2many("stock.lot")
    dot_range = fields.Char(related='product_id.dot_range')
    rangos_dots = fields.Char(string='Rango Dot', compute='_compute_rangos_dots')
    price_unit_discount = fields.Float(
        compute="_compute_price_unit_discount",
        string="Precio Unitario con descuento",
        digits=(6, 2),
    )
    list_origin = fields.Char(string="Lista de Origen")
    pricelist_id = fields.Many2one("product.pricelist", string="Lista de Precios")
    
    @api.constrains('price_unit')
    def _check_price_unit(self):
        for line in self:
            if not self.env.context.get('is_expo',False):
                return
            if not self.env.context.get('skip_shipping_price',False):
                return 
            if line.price_unit <= 0:
                raise ValidationError(_(
                    "El precio unitario para %s debe ser mayor que cero.") % line.product_id.display_name)
    
    @api.constrains("product_uom_qty")
    def _constrains_check_product_availability_dot(self):
        if self.env.context.get('force_skip',False):
            return
        for record in self:
            if record.lots_ids:
                stock_quants = self.env["stock.quant"].search(
                    [
                        ("product_id", "=", record.product_id.id),
                        ("quantity", ">", 0),  # Solo los que tienen cantidad disponible
                        ("location_id.usage", "=", "internal"),
                        (
                            "location_id.id",
                            "in",
                            record.lots_ids.quant_ids.location_id.ids,
                        ),
                    ]
                )
                total_available = sum(stock_quants.mapped("quantity"))
                if total_available < record.product_uom_qty:
                    raise UserError(
                        f"No hay suficiente stock disponible del producto '{total_available} < {record.product_uom_qty} {record.product_id.name} {record.single_dot}' en las ubicaciones internas. 200"
                    )
    def _ztyres_action_launch_stock_rule(self, previous_product_uom_qty=False):
        """
        Launch procurement group run method with required/custom fields genrated by a
        sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
        depending on the sale order line product rule.
        """
        precision = self.env["decimal.precision"].precision_get(
            "Product Unit of Measure"
        )
        procurements = []
        for line in self:
            line = line.with_company(line.company_id)
            if not line.product_id.type in ("consu", "product"):
                continue
            qty = line._get_qty_procurement(previous_product_uom_qty)
            if (
                float_compare(qty, line.product_uom_qty, precision_digits=precision)
                >= 0
            ):
                continue

            group_id = line._get_procurement_group()
            if not group_id:
                group_id = self.env["procurement.group"].create(
                    line._prepare_procurement_group_vals()
                )
                line.order_id.procurement_group_id = group_id
            else:
                # In case the procurement group is already created and the order was
                # cancelled, we need to update certain values of the group.
                updated_vals = {}
                if group_id.partner_id != line.order_id.partner_shipping_id:
                    updated_vals.update(
                        {"partner_id": line.order_id.partner_shipping_id.id}
                    )
                if group_id.move_type != line.order_id.picking_policy:
                    updated_vals.update({"move_type": line.order_id.picking_policy})
                if updated_vals:
                    group_id.write(updated_vals)

            values = line._prepare_procurement_values(group_id=group_id)
            product_qty = line.product_uom_qty - qty

            line_uom = line.product_uom
            quant_uom = line.product_id.uom_id
            product_qty, procurement_uom = line_uom._adjust_uom_quantities(
                product_qty, quant_uom
            )
            procurements.append(
                self.env["procurement.group"].Procurement(
                    line.product_id,
                    product_qty,
                    procurement_uom,
                    line.order_id.partner_shipping_id.property_stock_customer,
                    line.name,
                    line.order_id.name,
                    line.order_id.company_id,
                    values,
                )
            )
        if procurements:
            self.env["procurement.group"].run(procurements)
        return True

    @api.constrains("product_uom_qty")
    def _constrains_check_product_availability(self):
        MoveLine = self.env["stock.move.line"]

        for record in self:
            if not self.env.context.get("check_availability", True):
                continue

            product = record.product_id

            if (
                product.detailed_type != "product"
                or not record.product_uom_qty
            ):
                continue

            # 🔹 Cantidad física real
            qty_available = product.qty_available

            # 🔹 Reservas reales (misma lógica que validamos)
            move_lines = MoveLine.search([
                ('product_id', '=', product.id),
                ('reserved_uom_qty', '>', 0),
                ('move_id.state', 'in', ['assigned', 'partially_available']),
                ('location_id.usage', '=', 'internal'),
                ('move_id.picking_type_id.code', '=', 'outgoing'),
            ])

            total_reservado = sum(move_lines.mapped('reserved_uom_qty'))

            # 🔹 Disponible real calculado
            disponible_real = qty_available - total_reservado

            # 🔹 Validación con precisión UoM
            if float_compare(
                record.product_uom_qty,
                disponible_real,
                precision_rounding=product.uom_id.rounding,
            ) > 0:
                raise ValidationError(
                    _(
                        "Intentas vender %s de %s.\n\n"
                        "Stock físico: %s\n"
                        "Reservado real: %s\n"
                        "Disponible real: %s"
                    )
                    % (
                        record.product_uom_qty,
                        product.display_name,
                        qty_available,
                        total_reservado,
                        disponible_real,
                    )
                )

    def rango_fechas(self, anos):
        # Filtrar solo los años que tengan el formato correcto (4 dígitos)
        anos_validos = [ano for ano in anos if ano.isdigit() and len(ano) == 4]
        if len(anos_validos) == 0:
            return "N/A"
        elif len(anos_validos) == 1:
            return anos_validos[0]  # Si solo hay un año válido, devolverlo directamente
        elif len(anos_validos) < 1:
            return anos_validos
            # Ordenar los años válidos
        anos_validos.sort()
        # Tomar la fecha más antigua y la más reciente
        fecha_mas_antigua = anos_validos[0]
        fecha_mas_reciente = anos_validos[-1]
        print(f"Fecha más antigua: {fecha_mas_antigua}")
        print(f"Fecha más reciente: {fecha_mas_reciente}")
        return f"{fecha_mas_antigua}-{fecha_mas_reciente}"

    def _compute_rangos_dots(self):
        for sol in self:
            sol.rangos_dots = self.rango_fechas(
                sol.order_id.picking_ids.move_line_ids_without_package.filtered(
                    lambda x: x.product_id.id == sol.product_id.id
                )
                .mapped("lot_id")
                .mapped("name")
            )
            print(
                sol.order_id.picking_ids.move_line_ids_without_package.filtered(
                    lambda x: x.product_id.id == sol.product_id.id
                )
                .mapped("lot_id")
                .mapped("name")
            )
    
    def _compute_price_unit_discount(self):
        for record in self:
            discount = record.discount / 100
            record.price_unit_discount = record.price_unit * (1 - discount)

    @api.onchange("product_uom_qty", "product_id")
    def _onchange_check_product_availability(self):
        MoveLine = self.env["stock.move.line"]

        for record in self:
            if not record.product_id or not record.product_uom_qty:
                continue

            product = record.product_id

            if product.detailed_type != "product":
                continue

            # 🔹 STOCK FÍSICO
            qty_available = product.qty_available

            # 🔹 RESERVAS REALES (misma lógica que el constraint)
            domain = [
                ('product_id', '=', product.id),
                ('reserved_uom_qty', '>', 0),
                ('move_id.state', 'in', ['assigned', 'partially_available']),
                ('location_id.usage', '=', 'internal'),
                ('move_id.picking_type_id.code', '=', 'outgoing'),
            ]

            # 🔸 Si se están forzando lotes específicos
            if record.lots_ids:
                domain.append(
                    ('location_id', 'in', record.lots_ids.quant_ids.location_id.ids)
                )

            move_lines = MoveLine.search(domain)

            total_reservado = sum(move_lines.mapped('reserved_uom_qty'))

            disponible_real = qty_available - total_reservado

            # 🔹 Validación con precisión correcta
            if float_compare(
                record.product_uom_qty,
                disponible_real,
                precision_rounding=product.uom_id.rounding,
            ) > 0:

                return {
                    "warning": {
                        "title": _("¡Inventario insuficiente!"),
                        "message": _(
                            "Producto: %s\n\n"
                            "Stock físico: %s\n"
                            "Reservado real: %s\n"
                            "Disponible real: %s\n\n"
                            "Intentas vender: %s"
                        )
                        % (
                            product.display_name,
                            qty_available,
                            total_reservado,
                            disponible_real,
                            record.product_uom_qty,
                        ),
                    }
                }

    @api.constrains("product_uom_qty", "product_id")
    def _constrains_check_product_availability(self):

        if not self.env.context.get("check_availability", True):
            return

        MoveLine = self.env["stock.move.line"]

        for record in self:
            product = record.product_id

            if (
                not product
                or product.detailed_type != "product"
                or not record.product_uom_qty
            ):
                continue

            # 🔹 Stock físico total
            qty_available = product.qty_available

            # 🔹 Reservas reales (assigned y parcialmente disponible)
            domain = [
                ('product_id', '=', product.id),
                ('reserved_uom_qty', '>', 0),
                ('move_id.state', 'in', ['assigned', 'partially_available']),
                ('location_id.usage', '=', 'internal'),
                ('move_id.picking_type_id.code', '=', 'outgoing'),
            ]

            move_lines = MoveLine.search(domain)

            total_reservado = sum(move_lines.mapped('reserved_uom_qty'))

            # 🔹 Excluir la propia línea si ya tiene movimientos creados
            if record.move_ids:
                own_reserved = sum(
                    record.move_ids.mapped('move_line_ids.reserved_uom_qty')
                )
                total_reservado -= own_reserved

            disponible_real = qty_available - total_reservado

            if float_compare(
                record.product_uom_qty,
                disponible_real,
                precision_rounding=product.uom_id.rounding,
            ) > 0:

                raise ValidationError(
                    _(
                        "Inventario insuficiente.\n\n"
                        "Producto: %s\n"
                        "Stock físico: %s\n"
                        "Reservado real: %s\n"
                        "Disponible real: %s\n"
                        "Intentas vender: %s"
                    )
                    % (
                        product.display_name,
                        qty_available,
                        total_reservado,
                        disponible_real,
                        record.product_uom_qty,
                    )
                )

    def _get_valid_pricelists(self):
        return [1, 108]
    
    def get_item_with_min_price_after_discount(self):
        domain = [
            ("product_tmpl_id", "in", self.product_id.product_tmpl_id.ids),
            (
                "pricelist_id",
                "in",
                self.order_id.pricelist_id.ids
                if self.order_id.is_expo
                else self._get_valid_pricelists(),
            ),
        ]
        min_price_item = []
        pricelist_items = self.pricelist_item_id.search(domain)
        if self.order_id.promo_onyx:
            min_price_item = min(
                pricelist_items,
                key=lambda item: item.fixed_price if item.fixed_price else float("inf"),
                default=None,
            )
        if not min_price_item:
            # Buscar el ítem con el menor precio después de descuento
            min_price_item = min(
                pricelist_items,
                key=lambda item: item.fixed_price if item.fixed_price else float("inf"),
                default=None,
            )

        return min_price_item

    @api.model
    def get_catalog_price_for_product(self, product):
        """Precio mínimo después de descuento desde las listas de
        precios válidas, SIN depender de un pedido real (self.order_id
        no existe en el catálogo ni en el cotizador externo).

        Es la misma idea de get_item_with_min_price_after_discount,
        pero recortada a la rama que no necesita pedido: siempre usa
        _get_valid_pricelists() (sin la rama de is_expo/promo_onyx,
        que solo tienen sentido dentro de un sale.order ya creado).

        Si el producto no tiene ningún ítem en esas listas de precios,
        cae a product.lst_price para no devolver 0.0 sin explicación.
        """
        domain = [
            ('product_tmpl_id', 'in', product.product_tmpl_id.ids),
            ('pricelist_id', 'in', self._get_valid_pricelists()),
        ]
        pricelist_items = self.env['product.pricelist.item'].search(domain)
        min_price_item = min(
            pricelist_items,
            key=lambda item: item.fixed_price if item.fixed_price else float('inf'),
            default=None,
        )
        if min_price_item and min_price_item.fixed_price:
            return min_price_item.fixed_price
        return product.lst_price

    @api.model
    def get_free_qty_and_dot_range_for_product(self, product):
        """Cantidad libre de usar (stock disponible no reservado) y
        rango de DOT, calculados directamente desde stock.quant — sin
        pasar por un sale.order.line real ni por pickings.

        Pensado para el cotizador externo (módulo ztyres_promotions),
        que cotiza productos antes de que exista cualquier pedido: ahí
        no hay self.product_id ni self.order_id, solo un
        product.product suelto que llega del payload del cotizador.
        Por eso es @api.model y recibe el producto como parámetro, en
        vez de leerlo de un registro real de sale.order.line.

        Es PURAMENTE INFORMATIVO: no participa en
        get_item_with_min_price_after_discount ni en
        _get_pricelist_price, así que no afecta el precio. Tampoco
        toca _compute_rangos_dots (esa sigue leyendo picking_ids como
        siempre, para pedidos ya surtidos) — esta es una vía aparte
        que lee el stock libre porque en el cotizador todavía no hay
        pedido ni picking.

        Reutiliza rango_fechas() para no duplicar la lógica de
        formateo de años (un solo año, rango, o "N/A" si no hay DOT
        válido en el stock disponible).
        """
        quants = self.env['stock.quant'].search([
            ('product_id', '=', product.id),
            ('quantity', '>', 0),
            ('location_id.usage', '=', 'internal'),
        ])
        free_qty = sum(q.quantity - q.reserved_quantity for q in quants)
        dot_range = self.rango_fechas(quants.mapped('lot_id.name'))
        return free_qty, dot_range
    
    def _get_pricelist_price(self):
        
        if self.order_id.is_expo:
            search_domain = [
                ("product_tmpl_id", "in", self.product_id.product_tmpl_id.ids),
                ("pricelist_id", "in", self.order_id.pricelist_id.ids)
            ]            
        else:
            search_domain = [
            ("product_tmpl_id", "in", self.product_id.product_tmpl_id.ids),
            ("pricelist_id", "=", 122),
            ("lot_name", "=", self.single_dot),
        ]
        
        pricelist_item = self.env["product.pricelist.item"].search(
            search_domain, limit=1
        )
        if pricelist_item and not self.order_id.is_expo:
            self.list_origin in ["PROMOCIÓN DOT", "LISTA PROMO DOT"]
            self.list_origin = pricelist_item.pricelist_id.name
            return pricelist_item.fixed_price
        
        elif self.order_id.is_expo:
            self.list_origin = self.order_id.pricelist_id.name
            return pricelist_item.fixed_price
        
        # Calcular el precio usando la lista de precios válida
        self.ensure_one()
        self.product_id.ensure_one()
        self.pricelist_item_id = self.get_item_with_min_price_after_discount()
        self.list_origin = self.pricelist_item_id.pricelist_id.name
        self.pricelist_id = self.pricelist_item_id.pricelist_id.id
        price = self.pricelist_item_id._compute_price(
            self.product_id,
            self.product_uom_qty or 1.0,
            self.product_uom or self.product_id.uom_id,
            self.order_id.date_order or fields.Date.today(),
            currency=self.currency_id or self.order_id.company_id.currency_id,
        )
        
        return price
