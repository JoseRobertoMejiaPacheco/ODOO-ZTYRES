# -*- coding: utf-8 -*-
"""Importación masiva de valores de tarjeta de regalo ("Promo ZT").

La plantilla es la misma forma que la de cupones —código y monto— pero
significa otra cosa y por eso es un asistente aparte:

- El cupón define el alcance de la promoción y siempre genera nota de
  crédito. Aquí el alcance ya está definido por la promoción, y el monto
  normalmente se entrega como tarjeta.
- El cupón tiene tope de piezas por producto. La tarjeta no: si el
  código vale 5 y se compraron 10 llantas, son 50.
"""

from odoo import _, fields, models
from odoo.exceptions import UserError

from ..models.ztyres_promo_config import (
    GIFT_CARD_DELIVERY_NONE,
    GIFT_CARD_SOURCE_PRODUCT,
    POLICY_AMOUNT,
    REWARD_GIFT_CARD,
    SCOPE_SPECIFIC_PRODUCTS,
    UNLIMITED,
)


GIFT_CARD_MINIMUM_WITH_TAX = 50000


class GiftCardExcelWizard(models.TransientModel):
    _name = 'ztyres_promo.gift_card_excel_wizard'
    _inherit = 'ztyres_promo.excel_import_mixin'
    _description = 'Importar valores de tarjeta de regalo desde Excel'

    file = fields.Binary(
        string='Archivo Excel',
        required=True,
        help=(
            'Dos columnas: "codigo" y "monto" (el monto se captura CON IVA '
            'y es por cada pieza vendida).'
        ),
    )
    notas_credito_id = fields.Many2one(
        'ztyres_promo.notas_credito',
        string='Promoción',
        required=True,
    )
    mode = fields.Selection(
        [
            ('replace', 'Reemplazar los valores actuales'),
            ('update', 'Actualizar montos y agregar los nuevos'),
        ],
        string='Modo de carga',
        default='replace',
        required=True,
        help=(
            'Reemplazar deja únicamente los códigos del archivo. '
            'Actualizar cambia el monto de los que ya estaban y agrega los '
            'que faltan, sin duplicarlos.'
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

        # Si un código viene repetido, gana el último renglón. La tabla
        # tiene un índice único por (código, promoción), así que dejar
        # pasar el duplicado abortaría la carga completa con un error de
        # base de datos en vez de un mensaje entendible.
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

        created, updated = self._apply_gift_cards(
            promotion,
            amount_by_code,
            product_by_code,
        )

        configuration_note = self._align_promotion_configuration(promotion)

        message = _(
            'Se cargaron %(nuevos)d código(s) nuevos y se actualizaron '
            '%(cambios)d.'
        ) % {'nuevos': created, 'cambios': updated}
        if configuration_note:
            message += '\n' + configuration_note
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

    def _apply_gift_cards(self, promotion, amount_by_code, product_by_code):
        """Reemplaza o hace upsert, según el modo elegido."""
        gift_card_model = self.env['ztyres_promo.gift_card']

        if self.mode == 'replace':
            promotion.gift_card_ids.unlink()
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
                gift_card_model.create(values)
            return len(values), 0

        existing_by_product = {
            card.product_id.id: card
            for card in promotion.gift_card_ids
        }
        to_create = []
        updated = 0
        for code, amount in amount_by_code.items():
            product = product_by_code.get(code)
            if not product:
                continue
            card = existing_by_product.get(product.id)
            if card:
                if card.amount != amount:
                    card.amount = amount
                updated += 1
                continue
            to_create.append({
                'product_id': product.id,
                'amount': amount,
                'notas_credito_id': promotion.id,
            })
        if to_create:
            gift_card_model.create(to_create)
        return len(to_create), updated

    def _align_promotion_configuration(self, promotion):
        """El Excel define alcance y valor; $50,000 con IVA abre la tarjeta.

        Cada código cargado es un producto participante y su ``monto`` es
        el valor unitario de la tarjeta. No existe un monto general por
        promoción ni hay que configurar un tramo adicional a mano.
        """
        products = promotion.gift_card_ids.mapped('product_id')
        values = {
            'promo_type': POLICY_AMOUNT,
            'reward_type': REWARD_GIFT_CARD,
            'gift_card_source': GIFT_CARD_SOURCE_PRODUCT,
            'gift_card_delivery': GIFT_CARD_DELIVERY_NONE,
            'policy_line_amount_ids': [
                (5, 0, 0),
                (0, 0, {
                    'lower_limit': GIFT_CARD_MINIMUM_WITH_TAX,
                    'upper_limit': UNLIMITED,
                }),
            ],
        }
        if promotion.promo_conditions == SCOPE_SPECIFIC_PRODUCTS:
            values['product_ids'] = [(6, 0, products.ids)]
        promotion.write(values)
        return _(
            'La plantilla definió los productos participantes y su valor '
            'por pieza. La tarjeta se habilita al acumular $50,000 con IVA.'
        )

    # ------------------------------------------------------------------
    # Plantilla
    # ------------------------------------------------------------------
    def _template_definition(self):
        return (
            'plantilla_tarjeta_regalo.xlsx',
            ['codigo', 'monto'],
            [
                ['17756300', 84.07],
            ],
            [
                'Hoja "datos": es la que se importa. No cambie su nombre ni '
                'su posición (debe ser la primera hoja del libro).',
                '',
                'Columna "codigo" (obligatoria): referencia interna del '
                'producto en Odoo. Debe coincidir exactamente.',
                '',
                'Columna "monto" (obligatoria): valor de tarjeta CON IVA '
                'por CADA pieza vendida de ese código — es la columna '
                '"Promo ZT". Si dice 5 y el cliente compra 10 llantas, la '
                'tarjeta es de 50.',
                '',
                'No es un porcentaje, no es el valor total de la tarjeta, y '
                'no tiene tope de piezas.',
                '',
                'El monto se entrega tal cual se captura mientras la '
                'promoción esté configurada como "Solo aviso". Si se '
                'configura para emitir nota de crédito, el sistema le baja '
                'el IVA antes de facturar, porque el timbrado vuelve a '
                'sumarlo: capturar 5 entrega 5, no 5.80.',
                '',
                'Capture el monto como número, sin el signo $ ni comas. Se '
                'aceptan decimales con punto (12.50).',
                '',
                'Un código por renglón. Si un código aparece dos veces, se '
                'toma el monto del último renglón.',
                '',
                'Los montos negativos detienen la carga. Un monto de 0 se '
                'acepta: el código participa del acumulado pero no aporta '
                'valor a la tarjeta.',
                '',
                'La plantilla define los productos participantes: solo los '
                'códigos cargados acumulan compra y generan tarjeta.',
                '',
                'La tarjeta se entrega únicamente cuando esos productos '
                'acumulan al menos $50,000 facturados, IVA incluido.',
                '',
                'Se aceptan encabezados con acentos o mayúsculas '
                '("Código", "Importe", "Promo ZT"): el sistema los '
                'normaliza. Las columnas adicionales se ignoran.',
                '',
                'Modo de carga, al importar: "Reemplazar" deja solo los '
                'códigos del archivo; "Actualizar" cambia el monto de los '
                'ya cargados y agrega los nuevos, sin duplicar.',
            ],
        )
