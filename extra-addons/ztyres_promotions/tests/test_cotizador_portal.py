# -*- coding: utf-8 -*-
import json
from types import SimpleNamespace
from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.ztyres_promo.tests.common import PromoTestCommon
from odoo.addons.ztyres_promotions.controllers.controllers import PromotionsExternalAPI


@tagged('post_install', '-at_install')
class TestCotizadorPortal(PromoTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        portal_group = cls.env.ref('base.group_portal')
        cls.portal_user = cls.env['res.users'].with_context(
            no_reset_password=True,
            tracking_disable=True,
        ).create({
            'name': 'Portal Cotizador',
            'login': 'portal_cotizador_test',
            'password': 'portal_cotizador_test',
            'partner_id': cls.partner.id,
            'groups_id': [(6, 0, [portal_group.id])],
        })
        cls.non_tire_product = cls.env['product.product'].create({
            'name': 'Producto No Llanta Portal Test',
            'default_code': 'PORTAL-NO-TIRE',
            'type': 'product',
            'tire': False,
            'lst_price': 1000.0,
        })

    def _request(self, data=None, headers=None):
        env = self.env(user=self.portal_user)
        return SimpleNamespace(
            env=env,
            httprequest=SimpleNamespace(
                data=json.dumps(data or {}).encode('utf-8'),
                headers=(
                    {'X-Ztyres-Cotizador': '1'}
                    if headers is None else headers
                ),
                host='example.test',
                host_url='http://example.test/',
                args={},
            ),
        )

    def _json_response(self, response):
        return json.loads(response.get_data(as_text=True))

    def test_portal_ve_solo_su_partner_en_selector(self):
        controller = PromotionsExternalAPI()
        with patch('odoo.addons.ztyres_promotions.controllers.controllers.request',
                   self._request()):
            data = self._json_response(controller.cotizador_partners())

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], self.partner.id)

    def test_portal_puede_calcular_con_llanta_autorizada(self):
        controller = PromotionsExternalAPI()
        with patch('odoo.addons.ztyres_promotions.controllers.controllers.request',
                   self._request({
                       'partner_id': self.env.ref('base.main_partner').id,
                       'lines': [{'product_id': self.p_goodyear_16.id, 'qty': 2}],
                   })):
            data = self._json_response(controller.cotizador_quote())

        self.assertIn('lines', data)
        self.assertEqual(data['lines'][0]['product_id'], self.p_goodyear_16.id)

    def test_portal_no_puede_cotizar_producto_que_no_es_llanta(self):
        controller = PromotionsExternalAPI()
        with patch('odoo.addons.ztyres_promotions.controllers.controllers.request',
                   self._request({
                       'partner_id': self.partner.id,
                       'lines': [{'product_id': self.non_tire_product.id, 'qty': 1}],
                   })):
            response = controller.cotizador_quote()

        self.assertEqual(response.status_code, 400)
        self.assertIn('error', self._json_response(response))

    def test_portal_requiere_header_oficial_para_post(self):
        controller = PromotionsExternalAPI()
        with patch('odoo.addons.ztyres_promotions.controllers.controllers.request',
                   self._request({
                       'partner_id': self.partner.id,
                       'lines': [{'product_id': self.p_goodyear_16.id, 'qty': 1}],
                   }, headers={})):
            response = controller.cotizador_quote()

        self.assertEqual(response.status_code, 403)
