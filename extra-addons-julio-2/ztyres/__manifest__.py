# -*- coding: utf-8 -*-
{
    'name': "Ztyres",

    'summary': """
        Personalizaciones y modificaciones realizadas a Odoo Enterprise 14.0 para la empresa ZTYRES.""",
    'description': """
    Guía de modificaciones

    Se describe de manera breve la funcionalidad, modificación, permiso ó característica instalada.
    * Rango de DOT agregado en órdenes y cotizaciones de venta.
    * Combinación de dos o más cotizaciones de venta.
    * Listado de llantas con stock disponible en los documentos de órdenes y cotizaciones de venta.""",
    'author': "José Roberto Mejía Pacheco",
    'maintainer': 'José Roberto Mejía Pacheco',
    'website': "https://mx.linkedin.com/in/jrmpacheco",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Customizations',
    'version': '14.0.0.1',
    'external_dependencies' : {
        'python' : [],
    },    
    
    # any module necessary for this one to work correctly
    # 'l10n_mx_edi'
    'depends': ['ztyres_price_list','mail', 'stock', 'product', 'contacts', 'base', 'sale', 'sale_management', 'account'],
    'application': False,
    'installable': True,
    'auto_install': False,
    'price': 4000.00,
    'currency': 'USD',
    'license': 'LGPL-3',
    'sequence': 1,

    # always loaded
    'data': [
        'security/security.xml',
        'views/account_views.xml',
        # 'security/ir.model.access.csv',
        'views/account_move.xml',
        'views/sale_order_report.xml',
        'views/sale_views.xml',
        'wizard/sale_order_cancel_reason.xml',
        'views/stock_valuation_layer_resume_history_views.xml',
        'views/stock_valuation_layer_resume_line_views.xml',
        'views/product_template_views.xml',
        'views/ir_actions_report_templates.xml',    
    ],
        'qweb': [
        
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

}
