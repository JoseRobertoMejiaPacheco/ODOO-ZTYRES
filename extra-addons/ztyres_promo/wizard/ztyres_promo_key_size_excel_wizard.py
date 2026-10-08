# -*- coding: utf-8 -*-
"""Carga de la lista de Key Sizes desde Excel.

El archivo es una sola columna de códigos. Los porcentajes ya no van
aquí: viven en la columna "% Key Sizes" de la tabla de niveles, para no
capturar los mismos rangos dos veces.
"""

from odoo import _, fields, models
from odoo.exceptions import UserError


class KeySizeExcelWizard(models.TransientModel):
    _name = 'ztyres_promo.key_size_excel_wizard'
    _inherit = 'ztyres_promo.excel_import_mixin'
    _description = 'Importar Key Sizes de promoción desde Excel'

    file = fields.Binary(
        string='Archivo Excel',
        required=True,
        help='Una sola columna llamada "codigo", con la referencia interna.',
    )
    notas_credito_id = fields.Many2one(
        'ztyres_promo.notas_credito',
        string='Promoción',
        required=True,
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
            'conserva los Key Sizes que ya estaban marcados.'
        ),
    )
    add_to_scope = fields.Boolean(
        string='Agregar también a los productos participantes',
        default=True,
        help=(
            'Los Key Sizes solo cambian el porcentaje: para cobrar tienen '
            'que estar dentro del alcance. Con esta opción los códigos del '
            'archivo se agregan a la lista de productos participantes, sin '
            'quitar los que ya estaban.'
        ),
    )

    # ------------------------------------------------------------------
    # Importación
    # ------------------------------------------------------------------
    def action_import(self):
        self.ensure_one()
        promotion = self.notas_credito_id.exists()
        if not promotion:
            raise UserError(
                _('No se encontró la promoción que se desea actualizar.')
            )

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
        if not products:
            raise UserError(_(
                'Ninguno de los códigos del archivo existe en el catálogo: '
                '%s'
            ) % ', '.join(sorted(codes)[:10]))

        missing_codes = sorted(
            set(codes) - set(products.mapped('default_code'))
        )

        command = (
            [(6, 0, products.ids)]
            if self.mode == 'replace'
            else [(4, product_id) for product_id in products.ids]
        )
        values = {'key_size_product_ids': command}
        if self.add_to_scope:
            # Los Key Sizes no amplían el alcance por sí solos: si no se
            # agregan aquí, el cálculo los deja fuera y su porcentaje
            # especial nunca se paga.
            values['product_ids'] = [
                (4, product_id) for product_id in products.ids
            ]
        promotion.write(values)

        return self._build_notification(promotion, products, codes, missing_codes)

    def _build_notification(self, promotion, products, codes, missing_codes):
        message = _(
            'Se marcaron %(cargados)d producto(s) como Key Size, de '
            '%(leidos)d código(s) leídos.'
        ) % {'cargados': len(products), 'leidos': len(codes)}

        if self.add_to_scope:
            message += _('\nTambién se agregaron a los productos participantes.')

        warnings = []
        if missing_codes:
            warnings.append(_(
                'No se encontraron %(faltan)d código(s): %(lista)s'
            ) % {
                'faltan': len(missing_codes),
                'lista': ', '.join(missing_codes[:10]) + (
                    '…' if len(missing_codes) > 10 else ''
                ),
            })

        # Marcar productos sin capturar la columna no cambia nada: vale
        # más decirlo aquí que dejar que lo descubran al cuadrar la NC.
        levels = promotion._active_policy_lines()
        if levels and not any(line.key_size_discount > 0 for line in levels):
            warnings.append(_(
                'Falta capturar la columna "%% Key Sizes" en la tabla de '
                'niveles: por ahora estos productos cobrarían el porcentaje '
                'general.'
            ))

        if warnings:
            return self._notification(
                message + '\n' + '\n'.join(warnings),
                kind='warning',
            )
        return self._notification(message)

    # ------------------------------------------------------------------
    # Plantilla
    # ------------------------------------------------------------------
    def _template_definition(self):
        return (
            'plantilla_key_sizes.xlsx',
            ['codigo'],
            [
                ['10871003'],
                ['10492003'],
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
                'Un código por renglón, empezando en el renglón 2. Los '
                'códigos repetidos se cargan una sola vez.',
                '',
                'Aquí NO van porcentajes. El porcentaje de los Key Sizes se '
                'captura una sola vez, en la columna "% Key Sizes" de la '
                'tabla de niveles de la promoción: un renglón por tramo, '
                'los mismos tramos de siempre.',
                '',
                'Si un nivel deja esa columna en cero, en ese nivel los Key '
                'Sizes cobran el mismo porcentaje que los demás productos.',
                '',
                'Los Key Sizes NO agregan productos a la promoción. Suman '
                'al acumulado y cobran su porcentaje siempre que el alcance '
                'ya los incluya; por eso la opción "Agregar también a los '
                'productos participantes" viene marcada.',
                '',
                'Se aceptan encabezados con acentos o mayúsculas ("Código", '
                '"CODIGO", "Clave", "SKU"): el sistema los normaliza. Las '
                'columnas adicionales se ignoran.',
            ],
        )
