# -*- coding: utf-8 -*-
"""
Vocabulario del dominio de promociones.

Este archivo existe para que quede escrito en UN solo lugar cuáles son
los dos ejes independientes de una promoción, que antes estaban
mezclados y provocaban resultados incorrectos:

    EJE 1 - ALCANCE  (campo `promo_conditions`)
        Responde: ¿QUÉ productos participan?
        Nunca decide cuánto se otorga.

    EJE 2 - POLÍTICA (campo `promo_type`)
        Responde: ¿CÓMO se calcula el beneficio sobre lo que participa?
        Nunca decide qué productos entran.

El error histórico fue que `rim_quantity` y `coupons` vivían en los dos
selectores a la vez, así que una promoción con alcance
"Combinación de Características" (marca DUNLOP/FALKEN + rines R16..R26)
pero política "Cantidad Acumulada por Rin" terminaba ignorando marca y
rines del alcance, y tomaba como universo TODOS los productos cuyo rin
apareciera en la tabla de políticas -- de cualquier marca. De ahí las
NC infladas.

Regla dura del refactor: el universo SIEMPRE sale del alcance. La
política solo puede RESTRINGIR ese universo (intersección), nunca
ampliarlo.
"""

# ---------------------------------------------------------------------------
# Convención de límite superior
# ---------------------------------------------------------------------------
# Antes: 0 en "Hasta" significaba "sin límite superior". Eso obligaba a
# leer un 0 como infinito, que es exactamente lo contrario de lo que
# parece. Ahora el infinito se escribe explícito.
UNLIMITED = 999999999

# Se sigue interpretando 0 como infinito SOLO al leer datos viejos que
# todavía no pasaron por la migración de `init()`.
LEGACY_UNLIMITED = 0


def normalize_upper_limit(value):
    """Devuelve el límite superior efectivo de un tramo."""
    if not value or value <= LEGACY_UNLIMITED:
        return UNLIMITED
    return value


# ---------------------------------------------------------------------------
# EJE 1: ALCANCE - ¿qué productos participan?
# ---------------------------------------------------------------------------
SCOPE_TIRE_FEATURE = 'tire feature'
SCOPE_ATTRIBUTE_COMBINATION = 'attribute_combination'
SCOPE_SPECIFIC_PRODUCTS = 'specific_products'
SCOPE_COUPONS = 'coupons'
# Valor heredado. Antes se llamaba "Cantidad Acumulada por Rin" y hacía
# de alcance y de política al mismo tiempo. Se conserva el valor
# almacenado para no migrar datos, pero ya solo significa alcance:
# "participan los rines listados en la tabla de políticas".
SCOPE_RIM_POLICY = 'rim_quantity'

SCOPE_SELECTION = [
    (SCOPE_TIRE_FEATURE, 'Característica de Llanta (OR)'),
    (SCOPE_ATTRIBUTE_COMBINATION, 'Combinación de Características (AND)'),
    (SCOPE_SPECIFIC_PRODUCTS, 'Productos / Códigos Específicos'),
    (SCOPE_COUPONS, 'Cupones por Producto'),
    (SCOPE_RIM_POLICY, 'Rines de las Políticas (heredado)'),
]

# Alcances que se configuran eligiendo características de llanta.
FEATURE_SCOPES = (SCOPE_TIRE_FEATURE, SCOPE_ATTRIBUTE_COMBINATION)

# ---------------------------------------------------------------------------
# EJE 2: POLÍTICA - ¿cómo se calcula el beneficio?
# ---------------------------------------------------------------------------
POLICY_QUANTITY = 'quantity'
POLICY_AMOUNT = 'amount'
POLICY_MONTHLY_VOLUME = 'monthly_volume'
POLICY_RIM_QUANTITY = 'rim_quantity'
POLICY_COUPONS = 'coupons'

POLICY_SELECTION = [
    (POLICY_QUANTITY, 'Cantidad'),
    (POLICY_AMOUNT, 'Monto'),
    (POLICY_MONTHLY_VOLUME, 'Volumen Mensual'),
    (POLICY_RIM_QUANTITY, 'Cantidad Acumulada por Rin'),
    (POLICY_COUPONS, 'Cupones'),
]

# Políticas que usan las tablas de tramos genéricas (lower/upper/%/monto fijo).
TIER_POLICIES = (POLICY_QUANTITY, POLICY_AMOUNT)

# ---------------------------------------------------------------------------
# Matriz de combinaciones válidas
# ---------------------------------------------------------------------------
# Esto es lo que pediste explícito: los cupones son un caso cerrado y no
# se mezclan con nada; el resto de los alcances admiten cualquier política.
ALLOWED_POLICIES_BY_SCOPE = {
    SCOPE_TIRE_FEATURE: (
        POLICY_QUANTITY,
        POLICY_AMOUNT,
        POLICY_MONTHLY_VOLUME,
        POLICY_RIM_QUANTITY,
    ),
    SCOPE_ATTRIBUTE_COMBINATION: (
        POLICY_QUANTITY,
        POLICY_AMOUNT,
        POLICY_MONTHLY_VOLUME,
        POLICY_RIM_QUANTITY,
    ),
    SCOPE_SPECIFIC_PRODUCTS: (
        POLICY_QUANTITY,
        POLICY_AMOUNT,
        POLICY_MONTHLY_VOLUME,
        POLICY_RIM_QUANTITY,
    ),
    SCOPE_COUPONS: (POLICY_COUPONS,),
    SCOPE_RIM_POLICY: (POLICY_RIM_QUANTITY,),
}

# Alcances cuya política queda determinada por el propio alcance.
FORCED_POLICY_BY_SCOPE = {
    SCOPE_COUPONS: POLICY_COUPONS,
    SCOPE_RIM_POLICY: POLICY_RIM_QUANTITY,
}

# ---------------------------------------------------------------------------
# Tipos de beneficio
# ---------------------------------------------------------------------------
REWARD_PERCENTAGE = 'percentage'
REWARD_FIXED_AMOUNT = 'fixed_amount'

REWARD_SELECTION = [
    (REWARD_PERCENTAGE, 'Porcentaje'),
    (REWARD_FIXED_AMOUNT, 'Monto fijo en NC'),
]

# Tope de piezas bonificadas por producto en promociones de cupones.
DEFAULT_COUPON_LIMIT_QTY = 200
