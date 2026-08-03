# -*- coding: utf-8 -*-
{
    'name': 'ZTYRES Promociones',
    'summary': 'Cálculo de promociones y generación de notas de crédito',
    'description': """
        Administra promociones con dos ejes independientes: el ALCANCE
        (qué productos participan) y la POLÍTICA (cómo se calcula el
        beneficio: cantidad, monto, cupones, volumen mensual o cantidad
        acumulada por rin). Calcula resultados por cliente, por RFC
        receptor o por grupo, y genera las notas de crédito.
    """,
    'author': 'ZTYRES',
    'category': 'Sales',
    'version': '16.0.0.21.0',
    # discount_profiles reemplaza el reporte de cotización; esta
    # dependencia garantiza que nuestras herencias QWeb carguen después.
    'depends': [
        'ztyres_volumen',
        'ztyres_timbrado_generico',
        'ztyres_products',
        'web',
        'sale',
        'account',
        'discount_profiles',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/ztyres_promo_product_excel_wizard.xml',
        'wizard/ztyres_promo_coupon_excel_wizard.xml',
        'wizard/ztyres_promo_key_size_excel_wizard.xml',
        'views/ztyres_promo_current_policy.xml',
        'views/ztyres_promo_lines.xml',        
        'views/ztyres_promo_notas_credito_lines.xml',
        'views/ztyres_promo_notas_credito.xml',
        'views/menu_item.xml',
        'views/ztyres_promo_sale_account_views.xml',
        'views/ztyres_promo_report_invoice.xml',
        'views/ztyres_promo_report_sale_order.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
