# -*- coding: utf-8 -*-
{
    'name': "Productos Ztyres",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['product','purchase'],

    # always loaded
    'data': [
        
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/ztyres_products_brand.xml',
        'views/ztyres_products_ccc.xml',
        'views/ztyres_products_e_mark.xml',
        'views/ztyres_products_face.xml',
        'views/ztyres_products_index_of_load.xml',
        'views/ztyres_products_layer.xml',
        'views/ztyres_products_manufacturer.xml',
        'views/ztyres_products_model.xml',
        'views/ztyres_products_original_equipment.xml',
        'views/ztyres_products_s_mark.xml',
        'views/ztyres_products_segment.xml',
        'views/ztyres_products_speed.xml',
        'views/ztyres_products_supplier_segment.xml',
        'views/ztyres_products_tier.xml',
        'views/ztyres_products_tire_measure.xml',
        'views/ztyres_products_type.xml',
        'views/ztyres_products_floor_depth.xml',
        'views/product_template_views.xml',
        'views/ztyres_products_profile.xml',
        'views/ztyres_products_rim.xml',
        'views/ztyres_products_separator.xml',
        'views/ztyres_products_width.xml',        
        'views/ztyres_products_usage.xml',
        'views/ztyres_products_menus.xml',
        
        
        
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
