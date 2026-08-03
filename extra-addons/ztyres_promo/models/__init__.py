# -*- coding: utf-8 -*-
# Vocabulario del dominio y motor de cálculo: sin dependencias de otros
# modelos, por eso van primero.
from . import ztyres_promo_config
from . import ztyres_promo_reward_engine

# Tablas de configuración y de resultados.
from . import ztyres_promo_current_policy
from . import ztyres_promo_lines
from . import ztyres_promo_notas_credito_lines

# ztyres_promo.notas_credito: modelo base + extensiones (_inherit) en
# archivos separados por responsabilidad. El orden de import no afecta
# el comportamiento (Odoo fusiona todas las clases _inherit en el mismo
# modelo final), pero se mantiene así por legibilidad:
#   base -> alcance/dominio -> cálculo -> facturación -> utilidades
from . import ztyres_promo_notas_credito
from . import ztyres_promo_notas_credito_domain
from . import ztyres_promo_notas_credito_calculo
from . import ztyres_promo_notas_credito_facturacion
from . import ztyres_promo_notas_credito_zip
from . import ztyres_promo_notas_credito_eval

# Evaluación de promoción "ganada" en cotización/orden/factura, y su
# integración con sale.order / account.move (y sus líneas).
from . import ztyres_promo_document_promo_mixin
from . import ztyres_promo_sale_order
from . import ztyres_promo_sale_order_line
from . import ztyres_promo_account_move
from . import ztyres_promo_account_move_line
