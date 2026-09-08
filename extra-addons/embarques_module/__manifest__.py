{
    'name': 'Embarques',
    'version': '16.0.1.26.0',
    'summary': 'Trazabilidad de descuento por línea y destino obligatorio',
    'description': """
Embarques
=========

Arma embarques a partir de traslados y calcula el descuento logístico y genera una nota de crédito separada
que les corresponde, usando las opciones rango-descuento elegidas en cada destino. Un
cliente puede llenar el rango solo o consolidar con otro dentro del embarque.
Se suma la pareja para alcanzar el rango y se valida por separado
qué cliente aporta al menos 50%. Cada picking recibe la política de su propio
destino. El motor revisa los rangos numéricos permitidos de mayor a menor y
nunca toma el porcentaje de otro cliente. La unidad física no interviene.

Lo que no cumple la política puede solicitarse como descuento manual, sujeto a
autorización de Finanzas.
""",
    'author': '',
    'category': 'Inventory',
    'depends': [
        'stock', 'mail', 'sale', 'sale_stock', 'account', 'l10n_mx_edi_stock',
        'base_address_extended', 'l10n_mx_edi_extended', 'discount_profiles',
        'ztyres_timbrado_generico',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/embarques_data.xml',
        'data/paqueteria_product.xml',
        'data/logistico_seed_load.xml',
        'data/vehicle_migration.xml',
        'views/config_views.xml',
        'views/destino_views.xml',
        'views/policy_views.xml',
        'views/embarques_views.xml',
        'views/stock_picking_views.xml',
        'views/res_company_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/menu_views.xml',
    ],
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_configure',
    'assets': {
        'web.assets_backend': [
            'embarques_module/static/src/scss/embarques_form.scss',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
