# -*- coding: utf-8 -*-
{
    'name': "sale_customizations",

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


#    #'depends': ['ztyres_price_list','mail', 'stock', 'product', 'contacts', 'base', 'sale', 'sale_management', 'account'],

    # any module necessary for this one to work correctly
    #FIXME 
    'depends': ['base','l10n_mx_edi_40','ztyres_price_list','contacts','account','discount_profiles'],

    # always loaded
    'data': [
        # 'security/security.xml',
        # 'security/ir.model.access.csv',
 'views/sale_order.xml',
 'views/res_partner.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
