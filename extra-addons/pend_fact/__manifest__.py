{
    'name': 'Pendiente de Facturar',
    'version': '16.0.1.0.0',
    'summary': 'Dashboard en tiempo real de entregas pendientes de facturar',
    'description': """
        Detecta qué entregas de venta no han sido facturadas comparando
        movimientos de stock contra facturas y notas de crédito emitidas.
        Incluye análisis por pedido y detección de NC no ligadas.
    """,
    'category': 'Sales/Sales',
    'author': 'Custom',
    'website': '',
    'depends': ['sale_management', 'account', 'stock', 'web'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/dashboard_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pend_fact/static/src/css/dashboard.css',
            'pend_fact/static/src/js/dashboard.js',
        ],
    },
    'images': ['static/description/icon.png'],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
