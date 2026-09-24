from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestPaqueteriaChargeToggle(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.paqueteria_product = cls.env.ref(
            'embarques_module.product_paqueteria')
        cls.company.paqueteria_product_id = cls.paqueteria_product
        cls.zona = cls.env['embarques.zona'].create({'name': 'Zona Test'})
        cls.unidad = cls.env['embarques.unidad'].search([
            ('capacidad_llantas', '=', 1),
        ], limit=1) or cls.env['embarques.unidad'].create({
            'capacidad_llantas': 1,
        })
        cls.policy = cls.env['embarques.discount.policy'].search([
            ('unidad_id', '=', cls.unidad.id),
            ('percentage', '=', 0.0),
            ('company_id', '=', cls.company.id),
        ], limit=1) or cls.env['embarques.discount.policy'].create({
            'unidad_id': cls.unidad.id,
            'percentage': 0.0,
            'company_id': cls.company.id,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Llanta Test',
            'type': 'product',
            'invoice_policy': 'order',
            'list_price': 1000.0,
        })
        cls.env['stock.quant']._update_available_quantity(
            cls.product,
            cls.env.ref('stock.stock_location_stock'),
            10.0,
        )
        cls.partner = cls.env['res.partner'].with_user(2).create({
            'name': 'Cliente Paquetería Test',
            'city': 'Ciudad Paquetería Test',
        })
        receivable = cls.env['account.account'].search([
            ('account_type', '=', 'asset_receivable'),
            ('company_id', '=', cls.company.id),
            ('deprecated', '=', False),
        ], limit=1)
        if receivable:
            cls.partner.property_account_receivable_id = receivable
        cls.destino = cls.env['embarques.destino'].create({
            'manual_name': 'Ciudad Paquetería Test',
            'zona_id': cls.zona.id,
            'discount_policy_ids': [(6, 0, cls.policy.ids)],
            'unidad_ids': [(6, 0, cls.unidad.ids)],
            'paqueteria_estado': 'con_costo',
            'paqueteria_cost': 50.0,
            'company_id': cls.company.id,
        })
        cls.route = cls.env['rutas_embarques'].create({
            'name': 'Ruta Paquetería Test',
        })
        cls.vehicle = cls.env['embarques.vehicle'].create({
            'name': 'Unidad Paquetería Test',
            'capacity_m3': 100.0,
        })

    def _new_order(self):
        return self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'forma_envio': 'Paqueteria interna',
            'x_studio_val_pago': True,
            'unlock_financial': True,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 4.0,
                'price_unit': 1000.0,
            })],
        })

    def _paqueteria_lines(self, order):
        return order.order_line.filtered(
            lambda line: line.product_id == self.paqueteria_product)

    def test_embarque_toggle_removes_paqueteria_charge_from_invoice(self):
        order = self._new_order()
        line = self._paqueteria_lines(order)

        self.assertEqual(len(line), 1)
        self.assertEqual(line.product_uom_qty, 4.0)
        self.assertEqual(line.price_unit, 50.0)

        order.action_confirm()
        picking = order.picking_ids[:1]
        self.assertTrue(picking)

        embarque = self.env['embarques.embarques'].create({
            'ruta_id': self.route.id,
            'vehicle_id': self.vehicle.id,
            'pedidos_ids': [(6, 0, picking.ids)],
        })
        picking.charge_paqueteria = False

        line = self._paqueteria_lines(order)
        self.assertEqual(len(line), 1)
        self.assertEqual(line.product_uom_qty, 0.0)
        self.assertEqual(line.price_unit, 0.0)
        self.assertFalse(picking.charge_paqueteria)
        self.assertIn(picking, embarque.pedidos_ids)

        invoice = order._create_invoices()
        paqueteria_invoice_lines = invoice.invoice_line_ids.filtered(
            lambda line: line.product_id == self.paqueteria_product)

        self.assertFalse(paqueteria_invoice_lines)

    def test_paqueteria_charge_is_per_embarque_picking_line(self):
        charged_order = self._new_order()
        free_order = self._new_order()
        charged_order.action_confirm()
        free_order.action_confirm()
        charged_picking = charged_order.picking_ids[:1]
        free_picking = free_order.picking_ids[:1]

        embarque = self.env['embarques.embarques'].create({
            'ruta_id': self.route.id,
            'vehicle_id': self.vehicle.id,
            'pedidos_ids': [(6, 0, (charged_picking | free_picking).ids)],
        })
        free_picking.charge_paqueteria = False

        charged_line = self._paqueteria_lines(charged_order)
        free_line = self._paqueteria_lines(free_order)
        self.assertIn(charged_picking, embarque.pedidos_ids)
        self.assertIn(free_picking, embarque.pedidos_ids)
        self.assertTrue(charged_picking.charge_paqueteria)
        self.assertFalse(free_picking.charge_paqueteria)
        self.assertEqual(charged_line.product_uom_qty, 4.0)
        self.assertEqual(charged_line.price_unit, 50.0)
        self.assertEqual(free_line.product_uom_qty, 0.0)
        self.assertEqual(free_line.price_unit, 0.0)

        charged_invoice = charged_order._create_invoices()
        free_invoice = free_order._create_invoices()
        self.assertTrue(charged_invoice.invoice_line_ids.filtered(
            lambda line: line.product_id == self.paqueteria_product))
        self.assertFalse(free_invoice.invoice_line_ids.filtered(
            lambda line: line.product_id == self.paqueteria_product))
