from odoo import models, fields

class ResPartner(models.Model):
    _inherit = "res.partner"

    credit_limit = fields.Float(
        string='Credit Limit',
        help='Credit limit specific to this partner.',
        groups='account.group_account_invoice,'
               'account.group_account_readonly,'
               'permisos_ztyres.group_permisos_especiales_ventas',
        company_dependent=True,
        copy=False,
        readonly=False,
    )