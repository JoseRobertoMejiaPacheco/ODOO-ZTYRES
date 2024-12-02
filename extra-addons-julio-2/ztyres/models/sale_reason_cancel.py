from odoo import _, api, fields, models


class SaleReasonCancel(models.Model):
    _name = 'ztyres.sale_reason_cancel'
    _description = 'Motivo de cancelación'

    name = fields.Char(string='Nombre')
    description = fields.Char(string='Descripción')

    @api.model
    def create(self, values):
        result = super().create(values)
        return result