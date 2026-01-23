# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


# ============================================================
#   LÍNEAS DEL WIZARD (TRANSIENTS)
# ============================================================
class SaleOrderValidationLine(models.TransientModel):
    _name = "sale.order.validation.line"
    _description = "Línea de Validación de Productos"

    wizard_id = fields.Many2one(
        "sale.order.validation.wizard",
        ondelete="cascade",
    )

    issue_type = fields.Selection(
        [
            ("no_price", "Sin precio"),
            ("no_reserve", "Sin reserva"),
        ],
        string="Tipo",
        required=True,
    )

    product = fields.Char("Producto", readonly=True)
    demanded = fields.Float("Demandado", readonly=True)
    reserved = fields.Float("Reservado", readonly=True)

    move_id = fields.Many2one("stock.move", string="Movimiento", readonly=True)
    line_id = fields.Many2one("sale.order.line", string="Línea de SO", readonly=True)


# ============================================================
#   WIZARD
# ============================================================
class SaleOrderValidationWizard(models.TransientModel):
    _name = 'sale.order.validation.wizard'
    _description = 'Validación de Reservas y Precios en SO'

    order_id = fields.Many2one(
        'sale.order',
        string="Orden de Venta",
        readonly=True,
    )

    line_ids = fields.One2many(
        "sale.order.validation.line",
        "wizard_id",
        string="Problemas detectados",
    )
    
    has_reserve_issue = fields.Boolean()
    has_price_issue = fields.Boolean()

    # -------------------------
    # ACCIONES DEL WIZARD
    # -------------------------
    def action_remove_no_price(self):
        self.ensure_one()
        lines = self.line_ids.filtered(lambda l: l.issue_type == "no_price")
        lines.mapped('line_id').unlink()
        return self.order_id.action_confirm()
    
    def action_reserve_available(self):
        """
        Ajusta la cantidad pedida en la SO al stock realmente disponible.
        Ejemplo:
        - Pedía 100, reservado 100, disponible real = 80 → pone 80.
        """
        self.ensure_one()
        lines = self.line_ids.filtered(lambda l: l.issue_type == "no_reserve")        
        for l in lines:
            so_line = l.line_id              # sale.order.line real
            available_qty = l.reserved       # cantidad disponible detectada

            if not so_line:
                continue

            # ⚠️ Evitar dejar cantidad negativa o None
            if available_qty is None or available_qty < 0:
                available_qty = 0

            # 🔥 AQUÍ modificamos la cantidad pedida en la línea
            so_line.product_uom_qty = 0
            lines.mapped('move_id')._do_unreserve()
            so_line.product_uom_qty = available_qty            
        # Reintentar confirmar
        return self.order_id.action_confirm()
    
    def action_remove_not_reserved(self):
        """
        Elimina de la SO todas las líneas que no tuvieron reserva suficiente.
        """
        self.ensure_one()
        lines = self.line_ids.filtered(lambda l: l.issue_type == "no_reserve")
        lines.mapped('line_id').unlink()
        return self.order_id.action_confirm()
    
    def action_recompute_prices(self):
        """
        Recalcula los precios de las líneas que estaban sin precio.
        Se vuelve a ejecutar la lógica estándar de Odoo para asignar precio.
        """
        self.ensure_one()
        lines = self.line_ids.filtered(lambda l: l.issue_type == "no_price")

        for l in lines:
            so_line = l.line_id
            if not so_line:
                continue

            # 🔄 Recalcular precio usando la lógica nativa
            so_line._compute_price_unit()
        # Reintenta confirmar luego del recálculo
        return self.order_id.action_confirm()
    
# ============================================================
#   OVERRIDE DE action_confirm EN SALE.ORDER
# ============================================================
class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        for order in self:
            not_reserved = []
            no_price = []

            # -------------------------
            # DETECTAR LÍNEAS SIN PRECIO
            # -------------------------
            for line in order.order_line:
                if not line.price_unit or line.price_unit == 0:
                    no_price.append({
                        'line_id': line,
                        'product': line.product_id.display_name,
                    })

            # -------------------------
            # DETECTAR LÍNEAS SIN RESERVA
            # -------------------------
            for picking in order.picking_ids.filtered(lambda p: p.show_check_availability):
                for move in picking.move_ids_without_package:
                    demanded = move.product_uom_qty
                    reserved = move.reserved_availability
                    if reserved < demanded:
                        not_reserved.append({
                            'move_id': move,
                            'line_id': move.sale_line_id,
                            'product': move.product_id.display_name,
                            'demanded': demanded,
                            'reserved': reserved,
                        })

            # -------------------------
            # SI HAY PROBLEMAS → ABRIR WIZARD
            # -------------------------
            if no_price or not_reserved:

                wizard = self.env["sale.order.validation.wizard"].create({
                    "order_id": order.id,
                    "has_price_issue": bool(no_price),
                    "has_reserve_issue": bool(not_reserved),
                })

                # LÍNEAS SIN PRECIO
                for item in no_price:
                    self.env["sale.order.validation.line"].create({
                        "wizard_id": wizard.id,
                        "issue_type": "no_price",
                        "product": item["product"],
                        "line_id": item["line_id"].id,
                    })

                # LÍNEAS SIN RESERVA
                for item in not_reserved:
                    self.env["sale.order.validation.line"].create({
                        "wizard_id": wizard.id,
                        "issue_type": "no_reserve",
                        "product": item["product"],
                        "demanded": item["demanded"],
                        "reserved": item["reserved"],
                        "move_id": item["move_id"].id,
                        "line_id": item["line_id"].id,
                    })

                return {
                    "name": _("Validación de Productos"),
                    "type": "ir.actions.act_window",
                    "res_model": "sale.order.validation.wizard",
                    "view_mode": "form",
                    "target": "new",
                    "res_id": wizard.id,
                }

        # SI NO HAY PROBLEMAS → CONFIRMAR NORMAL
        return super().action_confirm()
