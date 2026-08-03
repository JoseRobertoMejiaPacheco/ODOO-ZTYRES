# Arquitectura de `ztyres_promo`

## El modelo mental: dos ejes independientes

Una promoción se define con dos decisiones que no se pueden mezclar:

| Eje | Campo | Pregunta que responde | Qué NO hace |
|---|---|---|---|
| **Alcance** | `promo_conditions` | ¿QUÉ productos participan? | Nunca decide cuánto se otorga |
| **Política** | `promo_type` | ¿CÓMO se calcula el beneficio? | Nunca agrega ni quita productos |

Regla dura:

```
universo = condiciones obligatorias
         AND alcance
         AND restricción de la política (solo si la política restringe)
```

La política **solo puede restringir** el universo que el alcance ya
definió. Nunca lo amplía y nunca lo sustituye.

### Alcances (`promo_conditions`)

| Valor almacenado | Etiqueta | Cómo se arma el universo |
|---|---|---|
| `tire feature` | Característica de Llanta (OR) | `expression.OR` de los criterios marcados; mínimo uno |
| `attribute_combination` | Combinación de Características (AND) | `expression.AND` de los criterios marcados; mínimo dos |
| `specific_products` | Productos / Códigos Específicos | Solo `product_ids` |
| `coupons` | Cupones por Producto | Solo los productos de `coupon_ids` |
| `rim_quantity` | Rines de las Políticas (heredado) | Los rines de `rim_policy_line_ids`, de cualquier marca |

### Políticas (`promo_type`)

| Valor | Tabla de tramos | Restringe el universo |
|---|---|---|
| `quantity` | `policy_line_qty_ids` | No |
| `amount` | `policy_line_amount_ids` | No |
| `monthly_volume` | `monthly_volume_line_ids` | No |
| `rim_quantity` | `rim_policy_line_ids` | Sí: solo rines con tramo |
| `coupons` | `coupon_ids` | No (el alcance ya es el mismo) |

### Combinaciones válidas

`ALLOWED_POLICIES_BY_SCOPE` en `models/ztyres_promo_config.py` es la
fuente de verdad, y una `@api.constrains` la hace cumplir:

- Cupones es un caso cerrado: alcance `coupons` ⇒ política `coupons`, y
  nada más.
- Alcance `rim_quantity` (heredado) ⇒ política `rim_quantity`.
- Los otros tres alcances admiten cualquiera de las cuatro políticas no
  exclusivas.

## Convención de límites

`UNLIMITED = 999999999`. Un tramo aplica cuando

```
lower_limit <= valor <= upper_limit
```

y, si se capturó `min_qty`, cuando además las piezas participantes lo
alcanzan. Si varios tramos aplican gana el de mayor `lower_limit`.

Ya no se escribe `0` para decir "sin tope". El `init()` de cada tabla de
tramos convierte los ceros históricos a `999999999`, y el motor sigue
leyendo un `0` como infinito por si queda algún dato sin migrar.

## Flujo de `Calcular NC`

`action_calcular_nc()` en `ztyres_promo_notas_credito_calculo.py`:

1. `_validate_configuration()` — alcance y política completos y coherentes;
2. `_clear_previous_lines()`;
3. `_create_detailed_lines()` — dos búsquedas globales (todo el periodo y
   el universo participante) y creación en lote del detalle;
4. `_update_missing_partner_vat_warning()`;
5. `_apply_coupon_limits()` — solo en cupones, una vez por cliente;
6. `_create_result_lines()` — un resultado por (cliente, RFC receptor);
7. `_apply_group_rewards()` — si aplican grupos, el tramo se reelige con
   el acumulado del grupo;
8. `_recompute_nc_amounts()`.

## Motor de beneficios

`ztyres_promo.reward_engine` (AbstractModel, sin estado) concentra:

- `tier_reward` — tramos de cantidad y monto;
- `rim_discount` / `rim_amounts` / `format_rim_breakdown` — por rin;
- `monthly_volume_discount`;
- `coupon_amounts`.

Lo usan tanto el cálculo masivo como la evaluación en vivo
(`..._eval.py`), así que una cotización y la NC final no pueden divergir.
`ztyres_promo.notas_credito_lines` conserva `_get_policy_reward`,
`_get_discount_percent` y `_get_monthly_volume_discount` como
delegadores, por compatibilidad con código externo.

## Separación por RFC receptor

El receptor se lee directamente de
`account.move.line.edi_vat_receptor`. `ztyres_timbrado_generico` lo
guarda junto con `account.move.line.group_id` cuando calcula
`account.move.edi_vat_receptor`; promociones no vuelve a resolver ni el
RFC ni el grupo.

El detalle y el resumen se agrupan por `partner_id + rfc`: un mismo
cliente con operaciones fiscales y de mostrador genera dos resultados y
dos notas de crédito. El monto fijo alcanzado se reparte entre esos
receptores en proporción a su subtotal positivo, con el redondeo
asignado al último, para que la suma sea exactamente el premio.

## Beneficio por grupo de clientes

Con `apply_on_groups = si` el tramo se determina con el acumulado del
grupo y luego se reasigna a cada resultado:

- tramos: `_apply_tier_group_rewards`;
- volumen mensual: `_apply_monthly_volume_group_rewards`;
- por rin: `_apply_rim_group_rewards`, que reasigna **por (cliente, RFC)**
  y no solo por RFC.

Los cupones no participan del beneficio de grupo.

## Auditoría del resultado

`ztyres_promo.notas_credito_lines.reward_detail` guarda en texto cómo se
compuso el importe: tramo alcanzado, acumulado usado y aporte de cada
rin. En promociones por rin, `reward_percent` es el porcentaje
**efectivo** (NC ÷ subtotal), no un valor capturado: por eso puede salir
un `4.71` que no aparece en ninguna tabla.

## Validación obligatoria de RFC

El cálculo no se revierte si falta el RFC receptor. Marca la línea,
guarda la lista de documentos, muestra una notificación roja, deja la
alerta en el formulario y bloquea `action_confirmar_nc()` desde el
servidor. Hay que corregir el RFC y volver a calcular.

## Responsabilidad de cada archivo

- `ztyres_promo_config.py` — vocabulario del dominio y matriz de combinaciones.
- `ztyres_promo_reward_engine.py` — todos los algoritmos de beneficio.
- `ztyres_promo_notas_credito.py` — campos, coherencia alcance/política, UI.
- `ztyres_promo_notas_credito_domain.py` — alcance → dominio de búsqueda.
- `ztyres_promo_notas_credito_calculo.py` — orquestación del cálculo masivo.
- `ztyres_promo_notas_credito_lines.py` — modelo de resultado.
- `ztyres_promo_lines.py` — detalle auditable.
- `ztyres_promo_current_policy.py` — tablas de tramos y sus validaciones.
- `ztyres_promo_notas_credito_facturacion.py` — creación y timbrado de NC.
- `ztyres_promo_notas_credito_eval.py` — evaluación sobre un documento.
- `ztyres_promo_document_promo_mixin.py` — presentación del resultado informativo.

## Configuración técnica pendiente

Siguen como constantes al inicio de
`ztyres_promo_notas_credito_facturacion.py`: diario de NC, producto de
bonificación y método de pago de condonación. El siguiente paso
recomendable es volverlos parámetros de compañía.
