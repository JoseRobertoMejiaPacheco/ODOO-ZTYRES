# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import re

# Deja solo dígitos del input
def _only_digits(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())

def _format_pedimento(digits: str) -> str:
    digits = re.sub(r'\D', '', digits)  # limpiar espacios o caracteres no numéricos
    if len(digits) == 18:
        a, b, c, d, e = digits[:2], digits[2:4], digits[4:8], digits[8:15], digits[15:18]
        return f"{a}  {b}  {c}  {d}  {e}"
    elif len(digits) == 15:
        a, b, c, d = digits[:2], digits[2:4], digits[4:8], digits[8:15]
        return f"{a}  {b}  {c}  {d}"

class StockLot(models.Model):
    _inherit = "stock.lot"

    pedimento = fields.Char(
        string="Número de Pedimento",
        help="Número de pedimento asociado a este lote. Captúralo pegado; se formatea al guardar."
    )

    @api.onchange("pedimento")
    def _onchange_pedimento_preview(self):
        if self.pedimento:
            digits = _only_digits(self.pedimento)
            self.pedimento = _format_pedimento(digits)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            ped = vals.get("pedimento")
            if ped:
                digits = _only_digits(ped)
                vals["pedimento"] = _format_pedimento(digits) if digits else False
        return super().create(vals_list)

    def write(self, vals):
        if "pedimento" in vals:
            ped = vals.get("pedimento")
            if ped:
                digits = _only_digits(ped)
                vals["pedimento"] = _format_pedimento(digits) if digits else False
        return super().write(vals)
