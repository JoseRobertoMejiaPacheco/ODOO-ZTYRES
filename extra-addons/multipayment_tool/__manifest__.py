# -*- coding: utf-8 -*-
{
    'name': "multipayment_tool",

    'summary': """
        Detalle de aplicación de pagos por factura: pagos previos, notas de
        crédito manuales (monto o porcentaje) y ajuste exacto de centavos.""",

    'description': """
Extiende `apply_payments` con el formulario de detalle por factura
(`multipayment_tool.payment_form`), donde se ven los pagos y notas de crédito
previos y se capturan los nuevos.

Novedades:

* **Nota de crédito manual** por monto fijo o por porcentaje, además del
  catálogo de descuentos preconfigurados. El motivo es obligatorio y se usa
  como concepto del CFDI de egreso.
* **Ajuste exacto de centavos**: la ventana fija de 0.01–0.05 se sustituye por
  una tolerancia configurable, y ahora también se ajusta el residuo del pago,
  no sólo el de la factura.
* Los IDs que estaban en duro (producto, impuesto, forma de pago, diario y
  cuenta de ajuste) pasan a configuración por compañía.
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Accounting/Accounting',
    'version': '16.0.2.0.0',
    'license': 'LGPL-3',

    'depends': ['apply_payments'],

    'assets': {
        'web.assets_qweb': [
            # 'multipayment_tool/static/src/xml/grouped_o2m_widget.xml'
        ],
        'web.assets_backend': [
            # 'multipayment_tool/static/src/xml/grouped_o2m_widget.xml',
            # "multipayment_tool/static/src/css/multipayment_tool.css",
            # "multipayment_tool/static/src/js/grouped_o2m_widget.js"
        ],
    },

    'data': [
        'security/security.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/apply_out_invoice_payments.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': False,
}
