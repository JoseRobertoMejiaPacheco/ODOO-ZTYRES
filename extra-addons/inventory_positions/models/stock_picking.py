from odoo import _, api, fields, models


class Picking(models.Model):

    _inherit = "stock.picking"
    
    def do_unreserve(self):
        self.move_ids.with_context(unreserve=True)._do_unreserve()
        self.package_level_ids.filtered(lambda p: not p.move_ids).unlink()