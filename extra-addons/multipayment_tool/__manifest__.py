# -*- coding: utf-8 -*-
{
    'name': "multipayment_tool",

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
    'depends': ['apply_payments'],
'assets': {
    'web.assets_qweb': [        
    #'multipayment_tool/static/src/xml/grouped_o2m_widget.xml'
    ],
    'web.assets_backend': [
        #'multipayment_tool/static/src/xml/grouped_o2m_widget.xml',
        # "multipayment_tool/static/src/css/multipayment_tool.css",
        # "multipayment_tool/static/src/js/grouped_o2m_widget.js"
        
    ],
},
    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'security/security.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/apply_out_invoice_payments.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
