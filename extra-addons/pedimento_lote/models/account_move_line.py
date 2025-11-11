# -*- coding: utf-8 -*-
from odoo import models, fields, api

def _digits_only(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch.isdigit())

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    pedimentos = fields.Char(
        string="Pedimentos",
        copy=False,
        help="Pedimentos de los lotes que surtieron esta línea. Se llena al postear la factura."
    )

# models/account_move.py
from odoo import models
from itertools import chain

def _digits_only(s):
    return "".join(ch for ch in (s or "") if ch.isdigit())

class AccountMove(models.Model):
    _inherit = "account.move"

    def _compute_pedimentos_for_line(self, line):
        """Regresa (bonito, compacto) para una línea de factura."""
        ped_pretty = set()
        ped_compact = set()

        if line.display_type == 'product' and line.product_id and line.sale_line_ids:
            moves = self.env["stock.move"].search([
                ("sale_line_id", "in", line.sale_line_ids.ids),
                ("state", "in", ["assigned", "done"]),
                ("product_id", "=", line.product_id.id),
            ])
            for mv in moves:
                for sml in mv.move_line_ids:
                    lot = sml.lot_id
                    if lot and lot.pedimento:
                        ped_pretty.add(lot.pedimento.strip())
                        ped_compact.add(_digits_only(lot.pedimento))

        pretty = ", ".join(sorted(ped_pretty)) if ped_pretty else False
        compact = ", ".join(sorted(ped_compact)) if ped_compact else False
        return pretty, compact

    def _fill_customs_numbers_from_lots(self):
        """Rellena pedimentos y l10n_mx_edi_customs_number sólo en esta factura."""
        for line in self.invoice_line_ids:
            pretty, compact = self._compute_pedimentos_for_line(line)
            line.pedimentos = pretty
            line.l10n_mx_edi_customs_number = pretty or False

    def action_post(self):
        for move in self.filtered(lambda m: m.move_type in ("out_invoice", "out_refund")):
            move._fill_customs_numbers_from_lots()
        return super().action_post()

