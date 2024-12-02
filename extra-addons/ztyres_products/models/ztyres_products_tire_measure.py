# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class TireMeasure(models.Model):
    _name = "ztyres_products.tire_measure"
    _description = "Medida"

    width_id = fields.Many2one("ztyres_products.width", string="Ancho")
    separator_id = fields.Many2one("ztyres_products.separator", string="Separador")
    profile_id = fields.Many2one("ztyres_products.profile", string="Perfil")
    rim_id = fields.Many2one("ztyres_products.rim", string="Rin")
    old_name = fields.Char(string="Medida antigua")
    name = fields.Char(compute="_compute_name", string="Medida",store=True)
    
    @api.depends('width_id','separator_id','rim_id','profile_id')
    def _compute_name(self):
        for rec in self:
            if rec.width_id.name and rec.separator_id.character and rec.profile_id.name and rec.rim_id.rim_name:
                rec.name = '%s%s%s %s'%(rec.width_id.name or '',rec.separator_id.character or '',rec.profile_id.name or '',rec.rim_id.rim_name or '')
            else:
                rec.name = rec.old_name or 'N/A'
