# -*- coding: utf-8 -*-
{
    'name': 'MX Vendor Bill XML Import (CFDI 4.0)',
    'version': '16.0.4.0.0',
    'category': 'Accounting/Localizations',
    'summary': (
        'Importar CFDI 4.0 desde la orden de compra: asignación de productos, '
        'resolución de conflictos multi-pedido, validación automática de almacén '
        'y facturación automática.'
    ),
    'author': 'Custom',
    'depends': [
        'account',
        'purchase',
        'stock',
        'l10n_mx_edi',
        'l10n_mx_edi_40',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/import_xml_wizard_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
