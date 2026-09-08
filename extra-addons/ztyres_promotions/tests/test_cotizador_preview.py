# -*- coding: utf-8 -*-
"""Tests del preview del cotizador.

Este archivo vive en ztyres_promotions y NO en ztyres_promo, porque
`get_promotions_preview` está definido aquí. ztyres_promo no depende de
este módulo (la dependencia va al revés), así que un test del cotizador
metido allá truena con AttributeError en cuanto se corre ztyres_promo
solo.

Correr con:
    odoo -d TU_BD -u ztyres_promotions --test-enable --stop-after-init \
         --workers=0 --log-level=test
"""

from odoo.tests import tagged

from odoo.addons.ztyres_promo.tests.common import PromoTestCommon
from odoo.addons.ztyres_promo.models.ztyres_promo_config import (
    GIFT_CARD_SOURCE_PRODUCT,
    POLICY_AMOUNT,
    POLICY_QUANTITY,
    POLICY_RIM_QUANTITY,
    REWARD_GIFT_CARD,
    REWARD_PERCENTAGE,
    SCOPE_RIM_POLICY,
    SCOPE_SPECIFIC_PRODUCTS,
    UNLIMITED,
)


@tagged('post_install', '-at_install')
class TestCotizadorPreview(PromoTestCommon):

    def test_goodyear_75_conserva_decimal_en_datos_y_calculo(self):
        promo = self._promo(
            nombre='Goodyear 7.5%',
            promo_conditions=SCOPE_SPECIFIC_PRODUCTS,
            product_ids=[(6, 0, [self.p_goodyear_16.product_tmpl_id.id])],
            promo_type=POLICY_QUANTITY,
            reward_type=REWARD_PERCENTAGE,
            policy_line_ids=[(0, 0, {
                'lower_limit': 1,
                'upper_limit': UNLIMITED,
                'discount': 7.5,
            })],
        )
        serialized = self.env['sale.order'].get_cotizador_promos()
        row = next(item for item in serialized if item['id'] == promo.id)
        tier = row['tiers'][0]

        self.assertEqual(tier['discount'], 7.5)
        product = {'product_id': self.p_goodyear_16.id, 'price': 1000.0}
        self.assertAlmostEqual(
            self.env['sale.order']._cotizador_promo_discount(product, row, tier),
            75.0,
            places=2,
        )

    def test_simulador_usa_base_pms_y_porcentaje_key_size(self):
        """PMS cambia la base; Key Size cambia el porcentaje."""
        product = {'product_id': self.p_goodyear_16.id, 'price': 1000.0}
        promo = {
            'promo_type': POLICY_QUANTITY,
            'reward_type': REWARD_PERCENTAGE,
            'product_ids': [self.p_goodyear_16.id],
            'key_size_product_ids': [self.p_goodyear_16.id],
            'pms_price_by_product': {str(self.p_goodyear_16.id): 800.0},
            'pms_tax_factor': 1.0,
        }
        tier = {'discount': 5.0, 'key_size_discount': 7.5}

        self.assertAlmostEqual(
            self.env['sale.order']._cotizador_promo_discount(
                product, promo, tier,
            ),
            60.0,  # 800 PMS × 7.5%, no 1,000 lista × 5%.
            places=2,
        )

    def test_pms_redondea_por_pieza_antes_de_retirar_iva(self):
        product = {'product_id': self.p_goodyear_16.id, 'price': 1000.0}
        promo = {
            'promo_type': POLICY_QUANTITY,
            'reward_type': REWARD_PERCENTAGE,
            'product_ids': [self.p_goodyear_16.id],
            'key_size_product_ids': [self.p_goodyear_16.id],
            'pms_price_by_product': {str(self.p_goodyear_16.id): 1817.20},
            'pms_tax_factor': 1.16,
        }
        # Convenio: round(1,817.20 × 5%) = 90.86 CON IVA.
        # Motor/NC: round(90.86 / 1.16) = 78.33 SIN IVA. Al mostrarse
        # con IVA vuelve a $90.86, como en la hoja del proveedor.
        self.assertAlmostEqual(
            self.env['sale.order']._cotizador_promo_discount(
                product, promo, {'discount': 3.0, 'key_size_discount': 5.0},
            ),
            78.33,
            places=2,
        )

    def test_simulador_pms_sin_precio_del_codigo_cae_a_lista(self):
        product = {'product_id': self.p_goodyear_16.id, 'price': 1000.0}
        promo = {
            'promo_type': POLICY_QUANTITY,
            'reward_type': REWARD_PERCENTAGE,
            'product_ids': [self.p_goodyear_16.id],
            'key_size_product_ids': [],
            'pms_price_by_product': {},
        }
        self.assertAlmostEqual(
            self.env['sale.order']._cotizador_promo_discount(
                product, promo, {'discount': 5.0},
            ),
            50.0,
            places=2,
        )

    def test_promocion_archivada_no_aparece_en_cotizador(self):
        promo = self._promo(
            active=False,
            promo_conditions=SCOPE_RIM_POLICY,
            promo_type=POLICY_RIM_QUANTITY,
            rim_policy_line_ids=[
                (0, 0, {
                    'lower_limit': 1,
                    'upper_limit': UNLIMITED,
                    'rim_ids': [(6, 0, [self.rim16.id])],
                    'discount': 5.0,
                }),
            ],
        )

        promo_ids = {
            item['id']
            for item in self.env['sale.order'].get_cotizador_promos()
        }

        self.assertNotIn(promo.id, promo_ids)

    def _gift_card_coupon_promo(self):
        return self._promo(
            nombre='Promo ZT 50k',
            promo_conditions=SCOPE_SPECIFIC_PRODUCTS,
            product_ids=[(6, 0, [self.p_goodyear_16.product_tmpl_id.id])],
            promo_type=POLICY_AMOUNT,
            reward_type=REWARD_GIFT_CARD,
            gift_card_source=GIFT_CARD_SOURCE_PRODUCT,
            promo_display_mode='both',
            policy_line_amount_ids=[(0, 0, {
                'lower_limit': 50000,
                'upper_limit': UNLIMITED,
            })],
            gift_card_ids=[(0, 0, {
                'product_id': self.p_goodyear_16.product_tmpl_id.id,
                'amount': 84.07,
            })],
        )

    def test_promo_zt_serializa_cupon_por_producto(self):
        promo = self._gift_card_coupon_promo()
        serialized = self.env['sale.order'].get_cotizador_promos()
        row = next(item for item in serialized if item['id'] == promo.id)

        self.assertEqual(row['reward_type'], REWARD_GIFT_CARD)
        self.assertEqual(row['tiers'][0]['discount'], 0.0)
        self.assertEqual(row['coupons'][0]['amount_with_tax'], 84.07)
        self.assertAlmostEqual(row['coupons'][0]['amount'], 72.4741, places=4)

    def test_preview_resta_cupon_sin_generar_nc(self):
        self._gift_card_coupon_promo()
        self.p_goodyear_16.lst_price = 50000.0

        preview = self.env['sale.order'].get_promotions_preview(
            self.partner.id,
            [{'product_id': self.p_goodyear_16.id, 'qty': 1}],
        )

        benefit = preview['promo_ganada']
        self.assertIsNotNone(benefit)
        self.assertAlmostEqual(
            benefit['per_product'][self.p_goodyear_16.id],
            84.07 / 1.16,
            places=2,
        )

    def test_preview_con_promo_por_rin_no_truena(self):
        """Regresión de `reward_engine._quantity_of`.

        El cotizador arma `_NcEvalLine`, objetos Python sueltos sin
        `_fields`. `_quantity_of` consultaba `line._fields` directamente,
        así que CUALQUIER promoción por rin (o con Key Sizes) reventaba
        con AttributeError en el preview, aunque funcionara perfecto
        sobre una orden o una factura.
        """
        self._promo(
            promo_conditions=SCOPE_RIM_POLICY,
            promo_type=POLICY_RIM_QUANTITY,
            rim_policy_line_ids=[
                (0, 0, {
                    'lower_limit': 1, 'upper_limit': UNLIMITED,
                    'rim_ids': [(6, 0, [self.rim16.id])],
                    'discount': 5.0,
                }),
            ],
        )
        preview = self.env['sale.order'].get_promotions_preview(
            self.partner.id,
            [{'product_id': self.p_goodyear_16.id, 'qty': 10}],
        )
        self.assertIn('promo_ganada', preview)

    def test_partner_id_como_string_no_truena(self):
        """El <select> del frontend manda el id como texto.

        `get_promotions_preview` hace int(partner_id) justo por esto: sin
        el cast, browse() trata "11296" como iterable de caracteres y
        revienta con "Expected singleton" más adelante.
        """
        preview = self.env['sale.order'].get_promotions_preview(
            str(self.partner.id),
            [{'product_id': self.p_goodyear_16.id, 'qty': 4}],
        )
        self.assertEqual(len(preview['lines']), 1)

    def test_politica_comercial_solo_acepta_porcentajes_autorizados(self):
        Order = self.env['sale.order']
        self.assertEqual(Order._cotizador_policy_total_pct({
            'volumen': '1',
            'logistico': '4',
            'financiero': '3',
        }), 8.0)
        self.assertEqual(Order._cotizador_policy_total_pct({
            'volumen': '5',       # no autorizado
            'logistico': '3',     # no autorizado
            'financiero': '4',    # no autorizado
        }), 0.0)
