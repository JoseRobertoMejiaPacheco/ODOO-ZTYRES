# -*- coding: utf-8 -*-
"""Carga de la tabla de precios PMS desde Excel.

El archivo trae dos columnas, `codigo` y `pms`. La segunda NO es dinero
que se le entregue al cliente: es el precio de referencia sobre el que
se aplica el porcentaje del nivel. Un archivo idéntico cargado en el
asistente de cupones significaría otra cosa completamente distinta —ahí
el número ES la nota de crédito por pieza— y por eso son dos asistentes
y dos tablas, aunque el .xlsx se vea igual.

Si el precio viene con IVA o sin IVA se decide aquí, al cargar, y se
guarda en la promoción: es el dato que más fácil se asume mal y el que
cambia el resultado un 16%.
"""

from odoo import _, fields, models
from odoo.exceptions import UserError

from ..models.ztyres_promo_config import (
    BASE_PMS,
    PRICE_TAX_SELECTION,
    PRICE_UNTAXED,
    REWARD_PERCENTAGE,
    TIER_POLICIES,
    POLICY_AMOUNT_RIM,
    SCOPE_SPECIFIC_PRODUCTS,
)


class PmsPriceExcelWizard(models.TransientModel):
    _name = 'ztyres_promo.pms_price_excel_wizard'
    _inherit = 'ztyres_promo.excel_import_mixin'
    _description = 'Importar precios PMS de promoción desde Excel'

    file = fields.Binary(
        string='Archivo Excel',
        required=True,
        help='Dos columnas: "codigo" y "pms" (precio por UNA pieza).',
    )
    notas_credito_id = fields.Many2one(
        'ztyres_promo.notas_credito',
        string='Promoción',
        required=True,
    )
    mode = fields.Selection(
        [
            ('replace', 'Reemplazar los precios actuales'),
            ('update', 'Actualizar precios y agregar los nuevos'),
        ],
        string='Modo de carga',
        default='replace',
        required=True,
        help=(
            'Reemplazar deja únicamente los códigos del archivo. '
            'Actualizar cambia el precio de los que ya estaban y agrega '
            'los que faltan, sin duplicarlos.'
        ),
    )
    price_taxed = fields.Selection(
        selection=PRICE_TAX_SELECTION,
        string='Los precios del archivo vienen',
        default=PRICE_UNTAXED,
        required=True,
        help=(
            'Se guarda en la promoción. La nota de crédito se calcula '
            'sobre el subtotal: si los precios traen IVA, el sistema se '
            'lo baja antes de aplicar el porcentaje.'
        ),
    )
    set_as_base = fields.Boolean(
        string='Cobrar el porcentaje sobre estos precios',
        default=True,
        help=(
            'Deja la promoción configurada para calcular sobre el precio '
            'PMS x piezas. Sin esta opción los precios quedan cargados '
            'pero el beneficio se sigue pagando sobre el subtotal '
            'facturado.'
        ),
    )
    add_to_scope = fields.Boolean(
        string='Agregar también a los productos participantes',
        default=False,
        help=(
            'Agrega los códigos del archivo a la lista de productos '
            'participantes, sin quitar los que ya estaban. Déjelo '
            'apagado si el alcance de la promoción ya está definido por '
            'características (marca, rin, medida).'
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

        data = self._read_excel(required_columns=('codigo', 'pms'))
        data = data.dropna(subset=['codigo', 'pms']).copy()
        data['codigo'] = data['codigo'].astype(str).str.strip()
        # `to_numeric` y no `float()`: una celda con "1,234.50" o con un
        # espacio no numérico reventaba la carga completa con un
        # ValueError de Python en vez de un mensaje entendible.
        data['pms'] = pd.to_numeric(data['pms'], errors='coerce')
        data = data.dropna(subset=['pms'])

        negative = data[data['pms'] < 0]
        if not negative.empty:
            raise UserError(_(
                'Hay precios negativos en el archivo: %s. Un precio PMS es '
                'una base de cálculo, no un descuento; corrija el archivo '
                'y vuelva a cargarlo.'
            ) % ', '.join(negative['codigo'].astype(str).head(10)))

        # Si un código viene repetido gana el último renglón, igual que
        # en la plantilla de tarjeta: la tabla tiene índice único por
        # (código, promoción) y dejar pasar el duplicado abortaría la
        # carga entera con un error de base de datos.
        price_by_code = {
            row.codigo: float(row.pms)
            for row in data.itertuples(index=False)
        }
        if not price_by_code:
            raise UserError(_(
                'El archivo no tiene renglones con código y precio '
                'válidos. Revise que la columna "pms" traiga números.'
            ))

        products = self.env['product.template'].search([
            ('default_code', 'in', list(price_by_code)),
        ])
        product_by_code = {
            product.default_code: product
            for product in products
        }
        missing_codes = sorted(set(price_by_code) - set(product_by_code))

        created, updated = self._apply_prices(
            promotion,
            price_by_code,
            product_by_code,
        )
        self._align_promotion_configuration(promotion, products)

        return self._build_notification(
            promotion,
            created,
            updated,
            missing_codes,
        )

    def _apply_prices(self, promotion, price_by_code, product_by_code):
        """Reemplaza o hace upsert, según el modo elegido."""
        price_model = self.env['ztyres_promo.pms_price']

        if self.mode == 'replace':
            promotion.pms_price_ids.unlink()
            values = [
                {
                    'product_id': product_by_code[code].id,
                    'price': price,
                    'notas_credito_id': promotion.id,
                }
                for code, price in price_by_code.items()
                if code in product_by_code
            ]
            if values:
                price_model.create(values)
            return len(values), 0

        existing_by_product = {
            record.product_id.id: record
            for record in promotion.pms_price_ids
        }
        to_create = []
        updated = 0
        for code, price in price_by_code.items():
            product = product_by_code.get(code)
            if not product:
                continue
            record = existing_by_product.get(product.id)
            if record:
                if record.price != price:
                    record.price = price
                updated += 1
                continue
            to_create.append({
                'product_id': product.id,
                'price': price,
                'notas_credito_id': promotion.id,
            })
        if to_create:
            price_model.create(to_create)
        return len(to_create), updated

    def _align_promotion_configuration(self, promotion, products):
        """Deja la promoción calculando sobre lo que se acaba de cargar.

        El IVA de los precios se escribe siempre, aunque no se marque la
        casilla de la base: la tabla ya quedó guardada y el dato de cómo
        se capturó pertenece a esa tabla, no a la decisión de usarla.
        """
        values = {'pms_price_taxed': self.price_taxed}
        # amount_rim siempre se liquida sobre PMS. En las demás políticas
        # se conserva la casilla opcional de siempre.
        if promotion._get_policy() == POLICY_AMOUNT_RIM or self.set_as_base:
            values['key_size_base'] = BASE_PMS
        # Si el alcance es Productos/Códigos Específicos, cargar el PMS en
        # amount_rim también alimenta esa lista: no obliga al usuario a subir
        # dos veces exactamente los mismos códigos. Para alcance por marca o
        # características, la tabla PMS solo actúa como restricción adicional.
        if products and (
            self.add_to_scope
            or (promotion._get_policy() == POLICY_AMOUNT_RIM
                and promotion._get_scope() == SCOPE_SPECIFIC_PRODUCTS)
        ):
            values['product_ids'] = [
                (4, product_id) for product_id in products.ids
            ]
        promotion.write(values)

    def _build_notification(self, promotion, created, updated, missing_codes):
        message = _(
            'Se cargaron %(nuevos)d precio(s) nuevos y se actualizaron '
            '%(cambios)d.'
        ) % {'nuevos': created, 'cambios': updated}

        if self.set_as_base:
            message += _(
                '\nLa promoción quedó configurada para cobrar el '
                'porcentaje sobre el precio PMS x piezas.'
            )
        if self.add_to_scope:
            message += _(
                '\nTambién se agregaron a los productos participantes.'
            )

        warnings = []
        if missing_codes:
            warnings.append(_(
                'No se encontraron %(faltan)d código(s) en el catálogo: '
                '%(lista)s'
            ) % {
                'faltan': len(missing_codes),
                'lista': ', '.join(missing_codes[:10]) + (
                    '…' if len(missing_codes) > 10 else ''
                ),
            })

        # Cargar los precios sin una política que aplique porcentajes no
        # cambia nada, y es mejor decirlo aquí que dejar que lo
        # descubran cuadrando la NC.
        if promotion._get_policy() not in TIER_POLICIES:
            warnings.append(_(
                'La política actual no usa niveles con porcentaje, así '
                'que estos precios no se van a usar. Cambie la política a '
                'Cantidad o Monto.'
            ))
        elif promotion._effective_reward_type() != REWARD_PERCENTAGE:
            warnings.append(_(
                'El Tipo de Beneficio no es Porcentaje: un monto fijo o '
                'una tarjeta no se multiplican por ninguna base, así que '
                'estos precios no se van a usar.'
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
            'plantilla_precios_pms.xlsx',
            ['codigo', 'pms'],
            [
                ['10871003', 2141.11],
                ['10492003', 2212.10],
            ],
            [
                'Hoja "datos": es la que se importa. No cambie su nombre ni '
                'su posición (debe ser la primera hoja del libro).',
                '',
                'Columna "codigo" (obligatoria): referencia interna del '
                'producto en Odoo, el campo "Referencia interna" de la '
                'ficha. Debe coincidir exactamente, incluidos guiones y '
                'ceros a la izquierda.',
                '',
                'Columna "pms" (obligatoria): precio de referencia de UNA '
                'pieza de ese código. No es un porcentaje, no es un '
                'descuento y no es dinero que se entregue: es la base '
                'sobre la que se aplica el porcentaje del nivel.',
                '',
                'La nota de crédito de cada renglón sale de: precio PMS x '
                'piezas vendidas x porcentaje del nivel alcanzado. El '
                'precio al que se facturó no interviene.',
                '',
                'Capture el precio como número, sin el signo $ ni comas. Se '
                'aceptan decimales con punto (2141.11).',
                '',
                'Al importar se elige si los precios vienen CON o SIN IVA. '
                'Las listas PMS suelen venir sin IVA. Equivocarse ahí '
                'cambia la nota de crédito un 16%: compare un código '
                'contra su factura antes de aprobar la promoción.',
                '',
                'Un código por renglón. Si un código aparece dos veces, se '
                'toma el precio del último renglón.',
                '',
                'Los precios negativos detienen la carga. Un precio de 0 se '
                'acepta: ese código participa del acumulado pero no genera '
                'nota de crédito.',
                '',
                'Un producto que participe en la promoción y no esté en '
                'este archivo cobra sobre su subtotal facturado, como '
                'siempre. El formulario avisa cuáles son cuando el alcance '
                'es una lista de códigos.',
                '',
                'Se aceptan encabezados con acentos o mayúsculas ("Código", '
                '"PMS", "Precio PMS"): el sistema los normaliza. Las '
                'columnas adicionales se ignoran.',
                '',
                'Modo de carga, al importar: "Reemplazar" deja solo los '
                'códigos del archivo; "Actualizar" cambia el precio de los '
                'ya cargados y agrega los nuevos, sin duplicar.',
            ],
        )
