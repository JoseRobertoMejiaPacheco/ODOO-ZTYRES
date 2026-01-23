# -*- coding: utf-8 -*-
{
    'name': "ztyres_promo",

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
    'depends': ['ztyres_volumen','ztyres_products'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/ztyres_promo_product_excel_wizard.xml',
        'views/ztyres_promo_current_policy.xml',
        'views/ztyres_promo_lines.xml',
        'views/ztyres_promo_notas_credito_lines.xml',
        'views/ztyres_promo_notas_credito.xml',
        'views/menu_item.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
