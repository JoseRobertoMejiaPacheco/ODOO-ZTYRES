# -*- coding: utf-8 -*-
{
    'name': 'Dashboard Reservas',
    'version': '16.0.1.0.0',
    'summary': 'Dashboard de antigüedad de pedidos reservados por vendedor',
    'description': """
        Dashboard que muestra la antigüedad de los pedidos en estado 'assigned'
        (reservados), filtrado automáticamente por vendedor según el usuario logueado.
        Los administradores y usuarios con permiso especial pueden ver todos los pedidos.
    """,
    'category': 'Inventory/Dashboard',
    'author': 'Custom',
    'depends': ['stock', 'sale_management', 'web'],
    'data': [
        'security/dashboard_reservas_security.xml',
        'security/ir.model.access.csv',
        'views/dashboard_reservas_views.xml',
        'views/dashboard_reservas_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'dashboard_reservas/static/src/css/dashboard.css',
            'dashboard_reservas/static/src/js/dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
