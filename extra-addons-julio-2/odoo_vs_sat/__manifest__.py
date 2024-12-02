# -*- coding: utf-8 -*-
{
    'name': "Odoo vs SAT (EE)",

    'summary': """
        Módulo para conciliar las cuentas de clientes entre Odoo y los registros del SAT,
        detectando diferencias, duplicidades y asegurando la alineación contable-fiscal.
        Ideal para empresas que gestionan grandes volúmenes de facturas y pagos.""",

    'description': """
            Este módulo facilita la conciliación entre Odoo y el SAT, permitiendo:

                - Comparación de facturas, pagos y saldos de clientes.
                - Identificación de diferencias en montos y registros entre Odoo y el SAT.
                - Detección y manejo de duplicidades.
                - Generación de reportes detallados que muestran discrepancias y coincidencias.

            Optimiza la gestión fiscal y contable, ayudando a cumplir con las normativas
            tributarias.
    """,

    'author': "José Roberto Mejía Pacheco",
    'website': "https://www.linkedin.com/in/jrmpacheco/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['account','l10n_mx_edi'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'application': True,
    'external_dependencies': {
        'python': ['pandas', 'python-dotenv'],  # Añadir aquí las dependencias externas
    },    
}
