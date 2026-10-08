# -*- coding: utf-8 -*-
"""Importación masiva de cupones por producto desde Excel."""

from odoo import _, fields, models
from odoo.exceptions import UserError


class CouponExcelWizard(models.TransientModel):
    _name = 'ztyres_promo.coupon_excel_wizard'
    _inherit = 'ztyres_promo.excel_import_mixin'
    _description = 'Importar cupones de promoción desde Excel'

    file = fields.Binary(
        string='Archivo Excel',
        required=True,
        help='Dos columnas: "codigo" y "monto" (el monto se captura CON IVA).',
    )
    notas_credito_id = fields.Many2one(
        'ztyres_promo.notas_credito',
        string='Promoción',
        required=True,
    )
    mode = fields.Selection(
        [
            ('replace', 'Reemplazar los cupones actuales'),
            ('update', 'Actualizar montos y agregar los nuevos'),
        ],
        string='Modo de carga',
        default='replace',
        required=True,
        help=(
            'Reemplazar deja únicamente los cupones del archivo. '
            'Actualizar cambia el monto de los productos que ya estaban y '
            'agrega los que faltan, sin duplicarlos.'
        ),
    )

    # ------------------------------------------------------------------
    # Importación
    # ------------------------------------------------------------------
    def action_import(self):
        self.ensure_one()
        import pandas as pd

        promotion = self.notas_credito_id.exists()
        if not promotion:
            raise UserError(
                _('No se encontró la promoción que se desea actualizar.')
            )

        data = self._read_excel(required_columns=('codigo', 'monto'))
        data = data.dropna(subset=['codigo', 'monto']).copy()
        data['codigo'] = data['codigo'].astype(str).str.strip()
        data['monto'] = pd.to_numeric(data['monto'], errors='coerce')
        data = data.dropna(subset=['monto'])

        negative = data[data['monto'] < 0]
        if not negative.empty:
            raise UserError(_(
                'Hay montos negativos en el archivo: %s. Corrija el archivo '
                'y vuelva a cargarlo.'
            ) % ', '.join(negative['codigo'].astype(str).head(10)))

        # Si un código viene repetido, gana el último renglón.
        amount_by_code = {
            row.codigo: float(row.monto)
            for row in data.itertuples(index=False)
        }
        if not amount_by_code:
            raise UserError(_(
                'El archivo no tiene renglones con código y monto válidos.'
            ))

        products = self.env['product.template'].search([
            ('default_code', 'in', list(amount_by_code)),
        ])
        product_by_code = {
            product.default_code: product
            for product in products
        }
        missing_codes = sorted(set(amount_by_code) - set(product_by_code))

        created, updated = self._apply_coupons(
            promotion,
            amount_by_code,
            product_by_code,
        )

        # Cargar cupones define por sí mismo el alcance de la promoción.
        # También corrige promociones antiguas donde Cupones estaba
        # seleccionado como Tipo de Política.
        if created or updated:
            promotion.write({'promo_conditions': 'coupons'})

        message = _(
            'Se crearon %(nuevos)d cupón(es) y se actualizaron %(cambios)d.'
        ) % {'nuevos': created, 'cambios': updated}
        if missing_codes:
            message += _(
                '\nProductos no encontrados (%(faltan)d): %(lista)s'
            ) % {
                'faltan': len(missing_codes),
                'lista': ', '.join(missing_codes[:10]) + (
                    '…' if len(missing_codes) > 10 else ''
                ),
            }
            return self._notification(message, kind='warning')
        return self._notification(message)

    def _apply_coupons(self, promotion, amount_by_code, product_by_code):
        """Reemplaza o hace upsert, según el modo elegido.

        El comportamiento anterior siempre creaba renglones nuevos: cargar
        dos veces el mismo archivo dejaba el cupón duplicado y el producto
        se bonificaba dos veces.
        """
        coupon_model = self.env['ztyres_promo.coupon']

        if self.mode == 'replace':
            promotion.coupon_ids.unlink()
            values = [
                {
                    'product_id': product_by_code[code].id,
                    'amount': amount,
                    'notas_credito_id': promotion.id,
                }
                for code, amount in amount_by_code.items()
                if code in product_by_code
            ]
            if values:
                coupon_model.create(values)
            return len(values), 0

        existing_by_product = {
            coupon.product_id.id: coupon
            for coupon in promotion.coupon_ids
        }
        to_create = []
        updated = 0
        for code, amount in amount_by_code.items():
            product = product_by_code.get(code)
            if not product:
                continue
            coupon = existing_by_product.get(product.id)
            if coupon:
                if coupon.amount != amount:
                    coupon.amount = amount
                updated += 1
                continue
            to_create.append({
                'product_id': product.id,
                'amount': amount,
                'notas_credito_id': promotion.id,
            })
        if to_create:
            coupon_model.create(to_create)
        return len(to_create), updated

    # ------------------------------------------------------------------
    # Plantilla
    # ------------------------------------------------------------------
    def _template_definition(self):
        return (
            'plantilla_cupones.xlsx',
            ['codigo', 'monto'],
            [
                ['LLA-DUN-19565R15-91H', 150],
                ['LLA-FAL-20555R16-91V', 200],
                ['LLA-PIR-22545R17-94Y', 350.5],
            ],
            [
                'Hoja "datos": es la que se importa. No cambie su nombre ni '
                'su posición (debe ser la primera hoja del libro).',
                '',
                'Columna "codigo" (obligatoria): referencia interna del '
                'producto en Odoo. Debe coincidir exactamente.',
                '',
                'Columna "monto" (obligatoria): pesos CON IVA por CADA pieza '
                'vendida de ese producto. No es un porcentaje y no es el '
                'monto total del cupón.',
                '',
                'El monto se captura CON IVA, como se le promete al '
                'cliente. Al generar la nota de crédito el sistema le baja '
                'el IVA, porque el timbrado vuelve a sumarlo: capturar 150 '
                'genera una NC de 129.31 y el cliente recibe 150.',
                '',
                'Capture el monto como número, sin el signo $ ni comas. Se '
                'aceptan decimales con punto (350.50).',
                '',
                'Un producto por renglón. Si un código aparece dos veces, '
                'se toma el monto del último renglón.',
                '',
                'Los montos negativos detienen la carga. Un monto de 0 se '
                'acepta: el producto participa pero no genera NC.',
                '',
                'Los encabezados alternos que se aceptan ("Importe", '
                '"Monto NC") significan lo mismo: monto CON IVA.',
                '',
                'Tope de piezas: la promoción bonifica como máximo el '
                'número de piezas configurado en "Tope de piezas por '
                'producto (cupones)" —200 por omisión— por producto y por '
                'cliente. Las piezas excedentes quedan marcadas como '
                'parciales en el detalle.',
                '',
                'Cargar este archivo define el alcance de la promoción como '
                '"Cupones por Producto": los productos del archivo son los '
                'únicos participantes, no hace falta elegir características.',
                '',
                'Se aceptan encabezados con acentos o mayúsculas '
                '("Código", "Importe", "Monto NC"): el sistema los '
                'normaliza. Las columnas adicionales se ignoran.',
                '',
                'Modo de carga, al importar: "Reemplazar" deja solo los '
                'cupones del archivo; "Actualizar" cambia el monto de los '
                'productos ya cargados y agrega los nuevos, sin duplicar.',
            ],
        )
