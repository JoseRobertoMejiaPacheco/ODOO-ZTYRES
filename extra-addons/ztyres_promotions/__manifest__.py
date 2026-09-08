# -*- coding: utf-8 -*-
{
    'name': "Ztyres Promociones",

    'summary': """
        Cotizador de llantas con promociones. Reutiliza el motor de
        ztyres_promo (alcance + política) y expone el resultado dentro
        de Odoo, en una página pública y en una API externa con key.""",

    'description': """
Cotizador de promociones Ztyres
================================
Las promociones se calculan con el motor de ztyres_promo (Notas de
Crédito). Ahí una promoción se define con dos ejes declarativos:
`promo_conditions` (ALCANCE: qué productos participan) y `promo_type`
(POLÍTICA: cómo se calcula el beneficio). Este módulo no tiene motor
propio — el suyo (ztyres_promotions.rule) fue eliminado; solo adapta
sus orígenes de líneas al motor de ztyres_promo.

La API externa se protege con una key compartida, guardada en
ir.config_parameter bajo ztyres_promotions.EXTERNAL_API_KEY y editable
desde Ajustes > Técnico > Parámetros del sistema. Vacía = API externa
deshabilitada.
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Sales/Sales',
    'version': '16.0.4.7.3',
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
