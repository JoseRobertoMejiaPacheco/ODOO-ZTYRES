# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class AccountInvoiceReport(models.Model):

    _inherit = 'account.invoice.report'

    """
    Propiedad de llantas
    """
    tire_measure_id = fields.Many2one('ztyres_products.tire_measure', string='Medida')
    face_id = fields.Many2one('ztyres_products.face', string='Cara')
    layer_id = fields.Many2one('ztyres_products.layer', string='Capas')
    manufacturer_id = fields.Many2one('ztyres_products.manufacturer', string='Fabricante')
    brand_id = fields.Many2one('ztyres_products.brand', string='Marca')
    model_id = fields.Many2one('ztyres_products.model', string='Modelo')
    speed_id = fields.Many2one('ztyres_products.speed', string='Velocidad')
    index_of_load_id = fields.Many2one('ztyres_products.index_of_load', string='Indice de carga')
    floor_depth_id = fields.Many2one('ztyres_products.floor_depth', string='Produndidad de Dibujo')
    country_id = fields.Many2one('res.country', string='Origen')
    segment_id = fields.Many2one('ztyres_products.segment', string='Segmento')
    tier_id = fields.Many2one('ztyres_products.tier', string='Tier')
    type_id = fields.Many2one('ztyres_products.type', string='Tipo')
    supplier_segment_id = fields.Many2one('ztyres_products.supplier_segment', string='Segmento de proveedor')
    original_equipment_id = fields.Many2one('ztyres_products.original_equipment', string='Equipamiento original')
    usage_id = fields.Many2one('ztyres_products.usage', string='Uso')
    e_mark_id = fields.Many2one('ztyres_products.e_mark', string='E-Mark')
    s_mark_id = fields.Many2one('ztyres_products.s_mark', string='S-Mark')
    ccc_id = fields.Many2one('ztyres_products.ccc', string='CCC')
    tire = fields.Boolean(string='Es llanta?',tracking=True)
    



    def _select(self):
        return super()._select() + """,template.tire_measure_id,
template.face_id,
template.layer_id,
template.manufacturer_id,
template.brand_id,
template.model_id,
template.speed_id,
template.index_of_load_id,
template.floor_depth_id,
template.country_id as country_id_pt,
template.segment_id,
template.tier_id,
template.type_id,
template.supplier_segment_id,
template.original_equipment_id,
template.usage_id,
template.e_mark_id,
template.s_mark_id,
template.ccc_id,
template.tire"""