# -*- coding: utf-8 -*-
from odoo import fields, models

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    # Tipo de documento aduanero, ej. "01" = Pedimento
    x_tipo_documento = fields.Char(
        string="Tipo de Documento Aduanero",
        help="Clave del tipo de documento aduanero (ej. '01' = Pedimento)."
    )

    # Número de pedimento en formato SAT
    x_num_pedimento = fields.Char(
        string="Número de Pedimento",
        help="Número de pedimento en el formato oficial del SAT."
    )

    # RFC del importador
    x_rfc_impo = fields.Char(
        string="RFC Importador",
        help="RFC del importador registrado en el pedimento."
    )
