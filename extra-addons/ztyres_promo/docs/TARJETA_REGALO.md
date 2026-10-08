# Tarjeta de regalo ("Promo ZT")

Promoción de referencia: **B/F-0801PZT** (Bridgestone / Firestone).

> Llévate una tarjeta de regalo por el valor indicado en la columna de
> Promo ZT. Compra mínima de 50 mil pesos netos al mes.

## Configuración correcta

Se carga un `.xlsx` con dos columnas, `codigo` y `monto`. Los códigos del
archivo son los productos participantes y el monto es el valor de tarjeta
por cada pieza. Por ejemplo, `17756300 | 84.07` entrega **$84.07 por pieza**.

El sistema configura automáticamente una compra mínima de **$50,000 con
IVA**. Antes de llegar a ese acumulado no se entrega tarjeta. Al alcanzarlo,
el valor es:

```
tarjeta = Σ (piezas del código × monto del código)
```

Si la columna dice **5** y el cliente compra **10** llantas, la tarjeta
es de **50**. **No hay tope de piezas** (a diferencia de los cupones,
que sí lo tienen).

Un código que no está en la plantilla **no participa, no suma al acumulado
y no genera tarjeta**. No existe un valor general por nivel para esta
promoción.

## Entrega (`gift_card_delivery`)

| Valor | Qué hace |
|---|---|
| `none` (por omisión) | Calcula y muestra el valor. **No emite ni timbra NC.** |
| `nc` | Además emite una NC por ese importe, bajándole el IVA antes de facturar. |

El default es `none` porque es el error reversible: si hacía falta la
NC se prende el selector y se recalcula. Al revés no — una NC timbrada
de más ya salió al SAT.

Con `nc`, al valor capturado se le baja el IVA porque el timbrado
vuelve a sumarlo: una tarjeta de **$50** genera una NC de **$43.10** y
el cliente recibe **$50**.

## La palabra "netos" del convenio

El mínimo se guarda **CON IVA** y el motor lo baja a subtotal para comparar.
La palabra *"netos"* del convenio significa neto de descuentos y
devoluciones, no sin IVA:

> Compra mínima de 50 mil pesos **netos** al mes

En estos convenios **"netos" significa neto de descuentos y
devoluciones, no sin IVA**. La meta ya viene facturada, así que se
captura tal cual:

```
Capturar 50,000  ->  el nivel abre en 43,103.45 de subtotal
                 ->  que es exactamente 50,000 facturados          ✓
```

Capturar 58,000 "para compensar el IVA" sería el error: exigiría 58,000
facturados y la promoción quedaría más difícil de alcanzar de lo que se
pactó con el fabricante.

La carga de esta Promo ZT deja el mínimo en 50,000 automáticamente; no es
necesario capturar un tramo general.

## Qué hace cada pieza del código

| Archivo | Responsabilidad |
|---|---|
| `ztyres_promo_config.py` | Constantes de origen y entrega |
| `ztyres_promo_current_policy.py` | Modelo `ztyres_promo.gift_card` (código → monto) y columna Promo ZT en los dos tipos de nivel |
| `ztyres_promo_reward_engine.py` | `gift_card_qualifies`, `gift_card_value`, `gift_card_product_amounts` |
| `..._eval.py` | `_evaluate_gift_card`: cotizaciones y facturas en vivo |
| `..._calculo.py` | Rama de tarjeta en el cálculo histórico y reparto por grupo |
| `wizard/..._gift_card_excel_wizard.py` | Carga del `.xlsx` y plantilla descargable |

## Cosas que estaban rotas y quedaron corregidas

1. **`Calcular NC` abortaba** en cualquier promoción de tarjeta: caía en
   la validación de porcentajes y lanzaba *"todos los porcentajes deben
   ser mayores que cero"*, aunque la tarjeta no captura porcentaje.
2. **El campo `line_ids` traía `domain=[('total_nc_untaxed','>',0)]`**,
   contradiciendo su propio comentario. Con tarjetas —importe de NC
   cero— la promoción se calculaba bien y se veía vacía; además dejaba
   las líneas en cero fuera del beneficio de grupo, que es justo el bug
   que ese comentario dice haber arreglado.
3. **El aviso en la cotización decía "¡Ganaste $0.00!"**, porque el
   monto salía de `ganado`, que en una tarjeta sin NC es cero por
   diseño. Ahora `{monto}` trae el valor de la tarjeta y existe además
   el marcador `{tarjeta}`.
4. **Solo funcionaba con política por Monto**: `_evaluate_gift_card`
   leía siempre `policy_line_amount_ids`, así que una tarjeta con
   política por Cantidad no se entregaba nunca.

## Reparto entre RFC receptores

Un cliente que factura con RFC fiscal y de mostrador genera **dos**
renglones de resultado. Con la plantilla por código no hay nada que
repartir (cada receptor paga por sus piezas), pero con valor fijo por
nivel sí: se reparte proporcional al subtotal, igual que el monto fijo.
Entregar el valor completo en cada renglón duplicaría la tarjeta.

Lo mismo con `apply_on_groups`: el grupo comparte el acumulado que abre
el nivel, no el importe. El grupo ayuda a **calificar**, no a cobrar dos
veces.
