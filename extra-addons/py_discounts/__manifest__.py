# -*- coding: utf-8 -*-
{
    'name': "py_discounts",

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
    'depends': ['ztyres_products'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/py_discounts_internal_type.xml',  # Este archivo depende de modelos que no se han cargado aún
        'views/py_discounts_limit_type.xml',  # Depende de modelos que podrían no estar disponibles
        'views/py_discounts_limits.xml',  # Depende de 'py_discounts_limit_type', que no está cargado aún
        'views/py_discounts_type.xml',  # Similar a los anteriores, depende de modelos no cargados
        'views/py_discounts_py_discounts.xml',  # Este debería ir al final, ya que depende de otros modelos
        'views/menu.xml'  # El menú debe ir al final porque depende de las vistas y modelos previos

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
