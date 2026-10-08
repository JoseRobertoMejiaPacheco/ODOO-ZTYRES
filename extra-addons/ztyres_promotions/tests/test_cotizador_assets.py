# -*- coding: utf-8 -*-
from pathlib import Path

from odoo.modules.module import get_module_resource
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCotizadorAssets(TransactionCase):

    @classmethod
    def _asset_text(cls, filename):
        path = get_module_resource(
            'ztyres_promotions',
            'static/src/cotizador_owl',
            filename,
        )
        return Path(path).read_text(encoding='utf-8')

    def test_filas_con_promo_definen_color_de_renglon(self):
        js = self._asset_text('components.js')

        self.assertIn("'in-promo': hasPromoColor()", js)
        self.assertIn('return !!(this.rowColor() || this.finalPrice());', js)
        self.assertIn('`--promo-row-bg: ${winner.tint}`', js)
        self.assertIn('`--promo-row-accent: ${winner.border}`', js)
        self.assertIn('`--promo-row-text: ${winner.text}`', js)

    def test_rango_de_volumen_marca_step_por_indice_o_por_rango(self):
        js = self._asset_text('components.js')

        self.assertIn('t-att-class="{ selected: isStepSelected(pr, step_index) }"', js)
        self.assertIn('t-att-style="stepTextStyle(pr, step_index)"', js)
        self.assertIn("t-att-data-selected=\"isStepSelected(pr, step_index) ? '1' : '0'\"", js)
        self.assertIn('stepSelectedVars(pr)', js)
        self.assertIn('stepTextStyle(pr, index)', js)
        self.assertIn('const selectedKey = this.rangeKey(selectedTier);', js)
        self.assertIn('return !!(key && selectedKey && key === selectedKey);', js)

    def test_promos_no_usan_tooltip_nativo_en_rangos(self):
        js = self._asset_text('components.js')

        self.assertNotIn('t-att-title="step.title"', js)
        self.assertNotIn("conditionCount(pr) + ' condiciones", js)

    def test_promo_seleccionada_sin_sombra_negra(self):
        css = self._asset_text('cotizador_owl.css')

        self.assertIn('.o_ztyres_cotizador .promos-panel .promo-step[data-selected="1"]', css)
        self.assertIn('box-shadow: none !important;', css)
        self.assertIn('background: transparent !important;', css)
        self.assertIn('border: 0 !important;', css)
        self.assertIn('font-weight: 900 !important;', css)
        self.assertIn(
            '.o_ztyres_cotizador .promos-panel .promo-step .step-value',
            css,
        )
        self.assertIn('color: var(--ink) !important;', css)
        self.assertIn('color: var(--step-selected-c, var(--promo-c)) !important;', css)
        self.assertNotIn('--promo-panel-accent', css)
        self.assertNotIn('.promo-step:has(input:checked)', css)
        self.assertNotIn('.promos-panel .promo-step.sel', css)
        self.assertIn('.promo-step[data-selected="1"] .step-range', css)
        self.assertIn('text-decoration: underline;', css)
