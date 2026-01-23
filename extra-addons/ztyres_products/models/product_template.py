from odoo import _, api, fields, models
import re
from odoo.exceptions import UserError,ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    """
    Propiedad de llantas
    """
    tire_measure_id = fields.Many2one('ztyres_products.tire_measure', string='Medida')
    face_id = fields.Many2one('ztyres_products.face', string='Cara')
    layer_id = fields.Many2one('ztyres_products.layer', string='Capas')
    manufacturer_id = fields.Many2one('ztyres_products.manufacturer', string='Fabricante')
    product_nationality = fields.Selection(related='manufacturer_id.product_nationality')
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
    product_dot_range = fields.Char(compute='_compute_product_dot_range', string='DOT')
    tire = fields.Boolean(string='Es llanta?',tracking=True)
    cui = fields.Char(
        string='CUI',
        compute='_compute_cui',
        store=True,
        readonly=True
    )
    
    hq_id = fields.Many2one('ztyres_products.hq', string='HQ')
    
    volume_f = fields.Float(compute='_compute_volume_f',digits=(10, 3),store=True, string='Volumen Estimado')
    nationality_custom_number = fields.Selection(
        string='Nacionalidad del pedimento',
        selection=[('national', 'Nacional'), ('imported', 'Importado'), ('national/imported', 'Nacional/Importado')]
    )
    
    # @api.constrains('tire', 'tire_measure_id', 'face_id', 'layer_id', 'manufacturer_id',
    #                 'brand_id', 'model_id', 'speed_id', 'index_of_load_id', 'floor_depth_id',
    #                 'country_id', 'segment_id', 'tier_id', 'type_id', 'supplier_segment_id',
    #                 'original_equipment_id', 'usage_id', 'e_mark_id', 's_mark_id', 'ccc_id')
    # def _check_tire_required_fields(self):
    #     for record in self:
    #         if record.tire:  # Si es llanta
    #             if not record.tire_measure_id:
    #                 raise ValidationError('El campo "Medida" es requerido para productos tipo llanta.')
    #             if not record.face_id:
    #                 raise ValidationError('El campo "Cara" es requerido para productos tipo llanta.')
    #             if not record.layer_id:
    #                 raise ValidationError('El campo "Capas" es requerido para productos tipo llanta.')
    #             if not record.manufacturer_id:
    #                 raise ValidationError('El campo "Fabricante" es requerido para productos tipo llanta.')
    #             if not record.brand_id:
    #                 raise ValidationError('El campo "Marca" es requerido para productos tipo llanta.')
    #             if not record.model_id:
    #                 raise ValidationError('El campo "Modelo" es requerido para productos tipo llanta.')
    #             if not record.speed_id:
    #                 raise ValidationError('El campo "Velocidad" es requerido para productos tipo llanta.')
    #             if not record.index_of_load_id:
    #                 raise ValidationError('El campo "Índice de carga" es requerido para productos tipo llanta.')
    #             if not record.country_id:
    #                 raise ValidationError('El campo "Origen" es requerido para productos tipo llanta.')
    #             if not record.segment_id:
    #                 raise ValidationError('El campo "Segmento" es requerido para productos tipo llanta.')
    #             if not record.tier_id:
    #                 raise ValidationError('El campo "Tier" es requerido para productos tipo llanta.')
    #             if not record.type_id:
    #                 raise ValidationError('El campo "Tipo" es requerido para productos tipo llanta.')
    #             if not record.supplier_segment_id:
    #                 raise ValidationError('El campo "Segmento de proveedor" es requerido para productos tipo llanta.')
    #             if not record.usage_id:
    #                 raise ValidationError('El campo "Uso" es requerido para productos tipo llanta.')
    
    @api.depends('tire_measure_id')
    def _compute_volume_f(self):
        for record in self:
            if record.detailed_type == 'product':
                record.volume_f = record.calcular_volumen_llanta()
            else:
                record.volume_f = 0
    
    def calcular_volumen_llanta(self, factor_ajuste=0.002):
        """
        Calcula el volumen para todos los formatos:
        - Europeo: "205 R16" (relación 80% implícita)
        - Estándar: "225/75R16"
        - Especial: "35X12.50R20", "7.00-14"
        """
        if not self.tire_measure_id.name:
            return 0.0

        medida = self.tire_measure_id.name
        medida_limpia = re.sub(r'[^0-9XR./-]', '', medida.replace(" ", "").upper())

        try:
            # Caso 1: Formato europeo "205 R16" (sin relación de aspecto)
            if re.fullmatch(r"\d+R\d+", medida_limpia) and "/" not in medida_limpia and "X" not in medida_limpia:
                ancho = float(medida_limpia.split("R")[0])
                rin = float(medida_limpia.split("R")[1]) * 25.4
                relacion = 0.8  # Relación de aspecto implícita del 80% para formato europeo
                diam_total = (ancho * relacion * 2) + rin
                volumen = ((diam_total ** 2) * ancho) / 1e9 + factor_ajuste

            # Caso 2: Formato "XXYZZRAA" (35X12.50R20)
            elif "X" in medida_limpia and "R" in medida_limpia:
                diam_total_pulg, resto = medida_limpia.split("X")
                ancho_pulg, rin_pulg = resto.split("R")
                diam_total = float(diam_total_pulg) * 25.4
                ancho = float(ancho_pulg) * 25.4
                volumen = ((diam_total ** 2) * ancho) / 1e9 + factor_ajuste

            # Caso 3: Formatos con guión (7.00-14) o estándar (225/75R16)
            else:
                if "-" in medida_limpia:
                    medida_limpia = medida_limpia.replace("-", "X") + "R" + medida_limpia.split("-")[1]
                
                if "/" in medida_limpia:
                    ancho, relacion, rin = re.split(r'[/R]', medida_limpia)
                    relacion = float(relacion) / 100
                else:
                    ancho, _, rin = medida_limpia.split("X")
                    relacion = 1.0
                
                ancho = float(ancho) * (25.4 if "X" in medida_limpia else 1)
                rin = float(rin) * 25.4
                diam_total = (ancho * relacion * 2) + rin
                volumen = ((diam_total ** 2) * ancho) / 1e9 + factor_ajuste

            return round(max(0.01, volumen), 3)  # Mínimo 0.01 m³

        except (ValueError, TypeError, IndexError):
            return 0.0
    
    @api.depends('tire_measure_id.name', 'segment_id.name', 'type_id.name')
    def _compute_cui(self):
        for record in self:
            if record.tire_measure_id and record.segment_id and record.type_id:
                cui = record.tire_measure_id.name + record.segment_id.name + record.type_id.name
                record.cui = cui.replace(" ", "")
            else:
                record.cui = ''    
    def _compute_product_dot_range(self):
        for record in self:
            record.product_dot_range = record.product_variant_id.dot_range
    
    def update_name_ztyres(self):
        for record in self:            
            name = "%s %s%s%s %s %s"%(record.tire_measure_id.name or "",record.face_id.name or "",record.layer_id.name or "",record.speed_id.name or "",record.brand_id.name or "",record.model_id.name or "")
            record.name = name
            record.display_name = name
    
    def write(self, vals):
        # Campos que afectan el nombre de las llantas
        tire_fields = ['tire_measure_id', 'face_id', 'layer_id', 'speed_id', 'brand_id', 'model_id', 'tire']
        
        # Si alguno de estos campos está en los valores a escribir
        if any(field in vals for field in tire_fields):
            res = super(ProductTemplate, self).write(vals)
            # Actualizar nombre después de escribir
            for record in self:
                if record.tire:  # Solo si es llanta
                    name = "%s %s%s%s %s %s" % (
                        record.tire_measure_id.name or "",
                        record.face_id.name or "",
                        record.layer_id.name or "",
                        record.speed_id.name or "",
                        record.brand_id.name or "",
                        record.model_id.name or ""
                    )
                    # Limpiar espacios múltiples
                    name = ' '.join(name.split())
                    # Solo actualizar si el nombre cambió
                    if record.name != name:
                        super(ProductTemplate, record).write({
                            'name': name,
                            'display_name': name
                        })
            return res
        else:
            return super(ProductTemplate, self).write(vals)
    
    @api.model_create_multi
    def create(self, vals_list):
        """También actualizar el nombre al crear un producto nuevo"""
        records = super(ProductTemplate, self).create(vals_list)
        for record in records:
            if record.tire:  # Solo si es llanta
                name = "%s %s%s%s %s %s" % (
                    record.tire_measure_id.name or "",
                    record.face_id.name or "",
                    record.layer_id.name or "",
                    record.speed_id.name or "",
                    record.brand_id.name or "",
                    record.model_id.name or ""
                )
                # Limpiar espacios múltiples
                name = ' '.join(name.split())
                if record.name != name:
                    super(ProductTemplate, record).write({
                        'name': name,
                        'display_name': name
                    })
        return records
    
    treadwear_id = fields.Many2one(
        'ztyres_products.treadwear',
        string='Treadwear'
    )