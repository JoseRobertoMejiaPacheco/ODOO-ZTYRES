# -*- coding: utf-8 -*-
{
    'name': "Aplicación de Pagos Múltiple (apply_payments)",

    'summary': """
        Aplica un pago a varias facturas, con ajuste automático de diferencias
        de centavos y notas de crédito manuales por monto o porcentaje.""",

    'description': """
Aplicación de Pagos Múltiple
============================

* Aplica un pago (account.payment) contra varias facturas de cliente.
* **Ajuste automático de diferencias**: si al terminar sobran o faltan centavos
  (dentro de una tolerancia configurable), se genera un asiento de ajuste y se
  concilia, dejando la factura y el pago en cero **exacto**, para que el
  complemento de pago pueda timbrarse sin rechazos del SAT.
* **Nota de crédito manual** por monto fijo o por porcentaje, con motivo
  obligatorio. Puede generarse como ajuste contable o como NC real (CFDI de
  egreso, out_refund) ligada a la factura original.
* Todos los importes se redondean con la precisión de la moneda del pago.
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Accounting/Accounting',
    'version': '16.0.2.0.0',
    'license': 'LGPL-3',

    'depends': ['account', 'contacts', 'l10n_mx_edi'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/apply_out_invoice_paymets.xml',
        'views/templates.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': False,
}
