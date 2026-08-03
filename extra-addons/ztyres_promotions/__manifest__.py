# -*- coding: utf-8 -*-
{
    'name': "Ztyres Promociones",

    'summary': """
        Motor de reglas de promoción estilo Nómina (condición y monto en
        Python), con variables de entorno configurables y sin tablas de
        alcance: todo el filtrado de marca/tier/rin/cliente vive en código.""",

    'description': """
Motor de promociones Ztyres
============================
Las promociones se calculan con el motor de ztyres_promo (Notas de Crédito).
Su condición y su monto se escriben en Python corto, igual que las
reglas salariales de hr.salary.rule, y puede leer el resultado de las
reglas anteriores por su código.

Variables de entorno (ztyres_promotions.config.param) reemplazan los
"números mágicos" en el código: umbrales de volumen, topes de
descuento, RFCs de público en general, etc. — editables desde
Promociones > Configuración > Parámetros del sistema sin tocar código.
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Sales/Sales',
    'version': '16.0.4.1.0',
    'license': 'LGPL-3',

    # ztyres_promo deja de ser una integración opcional: el cotizador
    # consume sus promociones, productos participantes, rangos y motor
    # de evaluación de NC.
    'depends': [
        'product', 'sale', 'account', 'mail', 'ztyres_products', 'sale_dot',
        'ztyres_promo',
    ],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/ztyres_promotions_params_views.xml',
        'views/ztyres_promotions_menus.xml',
        'views/cotizador_owl_templates.xml',
        'views/cotizador_owl_menus.xml',
    ],

    # Cotizador Owl — dos puntos de entrada, mismo componente y mismo
    # Owl nativo de Odoo (sin CDN externo, sin token):
    #   1) web.assets_backend: app interna dentro del webclient, con
    #      sesión, registrada como client action (backend_action.js).
    #   2) ztyres_promotions.assets_cotizador_public: página pública
    #      (sin sesión), montada a mano (public_main.js) sobre el
    #      HTML que sirve el controlador en /ztyres_promotions/cotizador.
    # El CSS está escrito bajo el selector raíz ".o_ztyres_cotizador"
    # para no pisar estilos de Odoo en ningún de los dos casos.
    'assets': {
        'web.assets_backend': [
            'https://fonts.googleapis.com/css2?family=Archivo+Black&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&display=swap',
            'ztyres_promotions/static/src/cotizador_owl/cotizador_owl.css',
            'ztyres_promotions/static/src/cotizador_owl/constants.js',
            'ztyres_promotions/static/src/cotizador_owl/icons.js',
            'ztyres_promotions/static/src/cotizador_owl/api.js',
            'ztyres_promotions/static/src/cotizador_owl/components.js',
            'ztyres_promotions/static/src/cotizador_owl/app.js',
            'ztyres_promotions/static/src/cotizador_owl/backend_action.js',
        ],
        'ztyres_promotions.assets_cotizador_public': [
            'https://fonts.googleapis.com/css2?family=Archivo+Black&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&display=swap',
            'ztyres_promotions/static/src/cotizador_owl/cotizador_owl.css',
            'ztyres_promotions/static/src/cotizador_owl/constants.js',
            'ztyres_promotions/static/src/cotizador_owl/icons.js',
            'ztyres_promotions/static/src/cotizador_owl/api.js',
            'ztyres_promotions/static/src/cotizador_owl/components.js',
            'ztyres_promotions/static/src/cotizador_owl/app.js',
            'ztyres_promotions/static/src/cotizador_owl/public_main.js',
        ],
    },
}
