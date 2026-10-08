# -*- coding: utf-8 -*-
"""Importación masiva de productos participantes desde Excel."""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductExcelWizard(models.TransientModel):
    _name = 'ztyres_promo.product_excel_wizard'
    _inherit = 'ztyres_promo.excel_import_mixin'
    _description = 'Importar productos de promoción desde Excel'

    file = fields.Binary(
        string='Archivo Excel',
        required=True,
        help='Una sola columna llamada "codigo", con la referencia interna.',
    )
    mode = fields.Selection(
        [
            ('replace', 'Reemplazar la lista actual'),
            ('add', 'Agregar a la lista actual'),
        ],
        string='Modo de carga',
        default='replace',
        required=True,
        help=(
            'Reemplazar deja únicamente los códigos del archivo. Agregar '
            'conserva los productos que ya estaban cargados.'
        ),
    )
    promotion_id = fields.Many2one(
        'ztyres_promo.notas_credito',
        string='Promoción',
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        context = self.env.context
        if context.get('default_res_model') == 'ztyres_promo.notas_credito':
            values.setdefault('promotion_id', context.get('default_res_id'))
        return values

    # ------------------------------------------------------------------
    # Importación
    # ------------------------------------------------------------------
    def action_import(self):
        self.ensure_one()
        promotion = self._get_promotion()
        data = self._read_excel(required_columns=('codigo',))

        codes = (
            data['codigo']
            .dropna()
            .astype(str)
            .str.strip()
            .replace('', None)
            .dropna()
            .unique()
            .tolist()
        )
        if not codes:
            raise UserError(_(
                'La columna "codigo" está vacía. Capture al menos una '
                'referencia interna de producto.'
            ))

        products = self.env['product.template'].search([
            ('default_code', 'in', codes),
        ])
        missing_codes = sorted(
            set(codes) - set(products.mapped('default_code'))
        )

        if self.mode == 'replace':
            command = [(6, 0, products.ids)]
        else:
            command = [(4, product_id) for product_id in products.ids]

        values = {
            'product_ids': command,
            'not_found': '\n'.join(missing_codes) or False,
        }
        if not promotion.promo_conditions:
            values['promo_conditions'] = 'specific_products'
        promotion.write(values)

        message = _(
            'Se cargaron %(cargados)d producto(s) de %(leidos)d código(s) '
            'leídos.'
        ) % {'cargados': len(products), 'leidos': len(codes)}
        if missing_codes:
            message += _(
                '\nNo se encontraron %(faltan)d código(s): %(lista)s'
            ) % {
                'faltan': len(missing_codes),
                'lista': ', '.join(missing_codes[:10]) + (
                    '…' if len(missing_codes) > 10 else ''
                ),
            }
            return self._notification(message, kind='warning')
        return self._notification(message)

    def _get_promotion(self):
        self.ensure_one()
        promotion = self.promotion_id or self.env[
            'ztyres_promo.notas_credito'
        ].browse(self.env.context.get('default_res_id'))
        promotion = promotion.exists()
        if not promotion:
            raise UserError(
                _('No se encontró la promoción que se desea actualizar.')
            )
        return promotion

    # ------------------------------------------------------------------
    # Plantilla
    # ------------------------------------------------------------------
    def _template_definition(self):
        return (
            'plantilla_codigos_productos.xlsx',
            ['codigo'],
            [
                ['LLA-DUN-19565R15-91H'],
                ['LLA-FAL-20555R16-91V'],
                ['LLA-PIR-22545R17-94Y'],
            ],
            [
                'Hoja "datos": es la que se importa. No cambie su nombre ni '
                'su posición (debe ser la primera hoja del libro).',
                '',
                'Columna "codigo" (obligatoria): referencia interna del '
                'producto en Odoo, el campo "Referencia interna" de la '
                'ficha del producto. Debe coincidir exactamente, incluidos '
                'guiones y ceros a la izquierda.',
                '',
                'Un código por renglón, empezando en el renglón 2. No deje '
                'renglones vacíos en medio: se ignoran, pero confunden al '
                'revisar.',
                '',
                'Los códigos repetidos se cargan una sola vez.',
                '',
                'Los códigos que no existan en Odoo no detienen la carga: '
                'se listan al terminar y quedan guardados en el campo '
                '"Códigos no encontrados" de la promoción.',
                '',
                'Se aceptan encabezados con acentos o mayúsculas '
                '("Código", "CODIGO", "Clave", "SKU"): el sistema los '
                'normaliza. Las columnas adicionales se ignoran.',
                '',
                'Modo de carga, al importar: "Reemplazar" deja solo los '
                'códigos del archivo; "Agregar" conserva los que ya '
                'estaban en la promoción.',
            ],
        )
