# models/stock_move_line.py
from odoo import models, fields

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    pedimento = fields.Char(
        string="Número de Pedimento",
        related="lot_id.pedimento",
        store=True,
        readonly=True,
    )
