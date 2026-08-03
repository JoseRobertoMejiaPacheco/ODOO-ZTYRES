# -*- coding: utf-8 -*-
{
    'name': 'Wizard Importacion de Pedido de Venta',
    'version': '16.0.1.0.0',
    'summary': 'Importar lineas de pedido desde Excel con politica de facturacion por pedido',
    'category': 'Sales',
    'author': 'Custom',
    'depends': ['sale_management', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sale_import_wizard_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
