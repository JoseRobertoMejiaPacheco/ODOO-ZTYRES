from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    sale_partner_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        related='move_id.sale_line_id.order_id.partner_id',
        store=True,
        readonly=True,
    )