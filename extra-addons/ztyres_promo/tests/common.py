# -*- coding: utf-8 -*-
"""Fixtures compartidos por los tests de promociones.

Vive aquí, en ztyres_promo, porque es el módulo que define el motor.
ztyres_promotions lo importa con:

    from odoo.addons.ztyres_promo.tests.common import PromoTestCommon

Construir el vocabulario de ztyres_products tiene tres trampas, y por eso
está centralizado en un solo lugar (ver comentarios en setUpClass).
"""

from datetime import date

from odoo.tests import TransactionCase


class PromoTestCommon(TransactionCase):

    # Fecha del documento y de vigencia de las promociones. Es un
    # `date` a propósito: el motor la compara contra campos Date de
    # Odoo, que ya vienen convertidos.
    DOC_DATE = date(2026, 6, 15)

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # -- Vocabulario --------------------------------------------
        # OJO con dos modelos que NO se crean con {'name': ...}:
        #   ztyres_products.rim   -> se crea con `number` (Float);
        #                            `rim_name` ('R16') es computed store.
        #   ztyres_products.width -> igual, `number`; `name` es computed.
        #   ztyres_products.profile -> igual.
        cls.rim16 = cls.env['ztyres_products.rim'].create({'number': 16.0})
        cls.rim17 = cls.env['ztyres_products.rim'].create({'number': 17.0})
        cls.rim18 = cls.env['ztyres_products.rim'].create({'number': 18.0})

        width = cls.env['ztyres_products.width'].create({'number': 205.0})
        profile = cls.env['ztyres_products.profile'].create({'number': 55.0})
        separator = cls.env['ztyres_products.separator'].create(
            {'character': '/'}
        )

        def measure(rim):
            return cls.env['ztyres_products.tire_measure'].create({
                'width_id': width.id,
                'separator_id': separator.id,
                'profile_id': profile.id,
                'rim_id': rim.id,
            })

        cls.measure16 = measure(cls.rim16)
        cls.measure17 = measure(cls.rim17)
        cls.measure18 = measure(cls.rim18)

        Brand = cls.env['ztyres_products.brand']
        cls.goodyear = Brand.create({'name': 'GOODYEAR'})
        cls.pirelli = Brand.create({'name': 'PIRELLI'})
        cls.dunlop = Brand.create({'name': 'DUNLOP'})

        Tier = cls.env['ztyres_products.tier']
        cls.tier_premium = Tier.create({'name': 'PREMIUM'})
        cls.tier_value = Tier.create({'name': 'VALUE'})

        # -- Productos ----------------------------------------------
        # El rin NO es un campo del producto: el motor lo lee por
        # `product.tire_measure_id.rim_id`. Un producto sin medida
        # completa es invisible para el alcance por rin y para
        # cualquier política rim_quantity.
        cls.p_goodyear_16 = cls._tire('GY-16', cls.goodyear, cls.tier_premium, cls.measure16)
        cls.p_pirelli_17 = cls._tire('PI-17', cls.pirelli, cls.tier_value, cls.measure17)
        cls.p_dunlop_18 = cls._tire('DU-18', cls.dunlop, cls.tier_premium, cls.measure18)

        cls.partner = cls._test_partner()

    @classmethod
    def _test_partner(cls):
        """Cliente de pruebas.

        `ztyres/models/res_partner.py` bloquea create() con un UserError
        para cualquier usuario que no sea el ID 2. En los tests el uid es
        SUPERUSER_ID (1), así que un create() normal revienta el
        setUpClass entero y ni un solo test llega a correr.

        Primero se reutiliza un cliente que ya exista (más barato y no
        pelea con el guard). Solo si la base no tiene ninguno se crea uno
        haciéndose pasar por el usuario 2, y el registro se vuelve a
        traer en el env de la clase para no mezclar entornos.
        """
        Partner = cls.env['res.partner']
        existing = Partner.search([('customer_rank', '>', 0)], limit=1)
        if existing:
            return existing

        admin = cls.env.ref('base.user_admin', raise_if_not_found=False)
        creator = Partner.with_user(admin.id) if admin else Partner
        created = creator.create({
            'name': 'Cliente de prueba (tests)',
            'customer_rank': 1,
        })
        return Partner.browse(created.id)

    @classmethod
    def _tire(cls, code, brand, tier, tire_measure):
        return cls.env['product.product'].create({
            'name': 'Llanta %s' % code,
            'default_code': code,
            'type': 'product',
            'tire': True,
            'brand_id': brand.id,
            'tier_id': tier.id,
            'tire_measure_id': tire_measure.id,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _promo(self, **vals):
        """Promoción vigente y en un estado que el motor sí evalúa.

        `EVAL_VALID_STATUSES` es ('approve_p', 'done'): una promoción en
        borrador NUNCA aplica, y es el error más fácil de cometer al
        escribir un caso nuevo.
        """
        base = {
            'nombre': 'Promo test',
            'start_date': date(2026, 1, 1),
            'end_date': date(2026, 12, 31),
            'status': 'approve_p',
        }
        base.update(vals)
        return self.env['ztyres_promo.notas_credito'].create(base)

    def _order(self, cart):
        """cart = [(producto, cantidad, precio_unitario), ...]

        `sale_dot._constrains_check_product_availability` rechaza toda
        línea que venda más de lo disponible en stock, y los productos
        del fixture se crean sin inventario. El propio sale_dot deja la
        puerta abierta:

            if not self.env.context.get("check_availability", True):
                return

        Se usa esa bandera en vez de sembrar stock.quant porque lo que
        estamos probando es el cálculo de la promoción, no la reserva de
        inventario. Sembrar stock metería ubicaciones, almacenes y
        movimientos al fixture sin que ninguno participe en el
        resultado. Si algún día hay que probar la constraint en sí, esa
        prueba va en sale_dot y no aquí.
        """
        env = self.env(context=dict(self.env.context, check_availability=False))
        order = env['sale.order'].create({
            'partner_id': self.partner.id,
            'date_order': self.DOC_DATE,
        })
        for product, qty, price in cart:
            env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': product.id,
                'product_uom_qty': qty,
                'price_unit': price,
            })
        return order

    def _evaluate(self, promo, order):
        """Evalúa la promoción contra las líneas de la orden.

        `doc_date` tiene que ser un `datetime.date`, no un string.
        `_promo_is_in_date_range` lo compara directo contra
        `self.start_date`, que Odoo entrega ya convertido a date, y un
        string revienta con TypeError. Los llamadores reales
        (document_promo_mixin) siempre pasan la fecha del documento, que
        ya es un date, así que esto es una regla del fixture y no un
        problema del motor.
        """
        return promo.evaluate_document(
            self.partner,
            self.DOC_DATE,
            order.order_line,
            'product_uom_qty',
        )
