# IVA y decimales: las dos reglas que atraviesan todo el módulo

Este documento existe porque las dos preguntas que más se repiten al
revisar una nota de crédito son "¿este número trae IVA?" y "¿por qué el
detalle no suma el total?". Las respuestas están dispersas en el código,
donde tienen que estar; aquí están juntas.

## Regla 1 — Todo monto capturado se escribe CON IVA

Es la convención del módulo. El negocio ve los importes facturados: una
tarjeta "de $2,000" son $2,000 en la mano, un cupón "de $150" son $150,
una meta de "50 mil al mes" son 50 mil facturados.

La nota de crédito, en cambio, **se emite siempre sobre el subtotal**, y
el timbrado le vuelve a sumar el IVA. Si un monto capturado se pasara
tal cual, el cliente recibiría 1.16 veces lo prometido. Por eso la
conversión se hace en el último momento, justo donde un monto
configurado se convierte en importe de NC (`reward_engine.untaxed`).

| Qué se captura | ¿Trae IVA? | Qué se hace con él |
|---|---|---|
| Límites *Desde/Hasta* de la tabla de **Monto** | Con IVA | Se bajan a subtotal para comparar contra el acumulado |
| Límites *Desde/Hasta* de la tabla de **Cantidad** | — | Son piezas, no llevan IVA |
| **Monto fijo** en NC por nivel | Con IVA | Se le baja el IVA antes de facturar |
| **Cupón** por pieza | Con IVA | Se le baja el IVA antes de facturar |
| **Tarjeta de regalo** (Promo ZT) | Con IVA | Se entrega tal cual. Solo se le baja el IVA si la promoción se configuró para emitir NC |
| **Porcentajes** (%, % Key Sizes) | — | Se aplican siempre sobre el **subtotal** |
| **Precio PMS** | **Configurable** | Se lleva a subtotal si se capturó con IVA |

El precio PMS es la única excepción, y es deliberada: las listas de las
marcas circulan de las dos formas, así que asumirlo sería apostar. Se
pregunta una vez por promoción, al cargar el archivo. Ver
`PRECIOS_PMS.md`.

### El acumulado nunca se toca

Para comparar el acumulado (sin IVA, es la suma de `price_subtotal`)
contra un límite capturado con IVA, se convierte **el límite**, no el
acumulado:

```
35,000 / 1.16 = 30,172.41    ->  el cliente entra al tramo con 30,172.41 de subtotal
```

El acumulado viaja por todo el motor: es la base de la NC, del desglose
por línea, del reparto de monto fijo y de la tabla de Key Sizes.
Bajarle el IVA obligaría a acordarse de volverlo a subir en cada uno de
esos puntos, y el primero que se olvidara inflaría la NC un 16%. El
límite, en cambio, solo se usa en un lugar.

### La tasa

Se lee de `ir.config_parameter` → `ztyres_promo.tier_amount_tax_rate`,
en porcentaje. Sin configurar, 16. Una tasa de 0 escrita a mano se
respeta (hay promociones sobre productos exentos); un parámetro vacío
**no** se lee como 0, porque `float(False)` da 0.0 sin lanzar excepción
y los límites nunca se convertirían.

Esto asume **una sola tasa por promoción**. Si en la misma promoción
entran productos con IVA frontera (8%) o exentos, el tramo se elige con
una tasa que no es la de esas líneas.

## Regla 2 — Los importes se redondean a centavos en el motor, no al guardarse

Un importe de nota de crédito se paga en centavos. Antes cada método
devolvía el float crudo de la multiplicación y el redondeo ocurría, sin
que nadie lo decidiera, al escribir en un campo `digits=(16, 2)`. Eso
producía dos síntomas:

1. **El detalle no sumaba el total.** En las promociones que calculan
   renglón por renglón (rin, Key Sizes, base PMS) el total era la suma
   de importes *sin* redondear, mientras que lo que se le enseña al
   cliente son renglones *ya* redondeados. Diferencia de uno o dos
   centavos, imposible de explicar.
2. **Comparaciones sobre basura de punto flotante.** Un porcentaje
   heredado de una importación que vale `0.0000000001` hacía que
   `discount > 0` dijera que sí hay descuento, y se cobraba un
   porcentaje que en pantalla se ve como cero.

Ahora todo importe sale redondeado del motor (`round_money`,
`percent_amount`) y **el total es la suma exacta de los renglones ya
redondeados**. Los porcentajes se comparan con `is_zero_percent`, no con
`> 0`.

### Por qué `round_money` redondea dos veces

`float_round` decide bien el centavo —redondea medio hacia arriba, que
es lo que se espera de dinero, mientras que el `round()` de Python
redondea al par y convertiría `0.015` en `0.01`— pero devuelve el
resultado como `numero_de_centavos × 0.01`, y esa multiplicación
reintroduce ruido binario:

```
float_round(84.07, 0.01)  ->  84.07000000000001
```

El centavo es correcto, pero el número deja de ser **igual** al float
que produce escribir `84.07`, y eso rompe cualquier comparación exacta
aguas abajo (lo detectó el cotizador de `ztyres_promotions`, que
serializa el importe y lo compara contra el valor capturado). El
`round()` final no puede cambiar el centavo —ya está decidido— solo
elige el float más cercano a ese decimal.

### Piezas: se redondean, no se truncan

Las cantidades llegan de sumas de floats, y las notas de crédito restan,
así que un `274.99999` es lo normal y no la excepción. `int(274.99999)`
da **274**: ese número se imprimía en la columna *Detalle del beneficio*
de un cliente que había comprado 275 llantas, y se guardaba en el campo
`quantity` del resultado, que es un `Integer`. Ahora se redondea antes
(`format_quantity`, `_result_quantity`).

### El `% efectivo` se guarda con 8 decimales para poder comprobarlo

En las promociones por rin, con Key Sizes o con base PMS, la columna
**% efectivo** no es un porcentaje capturado en ningún lado: es
`NC ÷ subtotal`, la mezcla de porcentajes de ese cliente. Un
`4.65401926 %` es normal.

Se guarda con **8 decimales** porque esa es la precisión con la que el
número, tecleado en Excel o en la calculadora, devuelve el `Total NC`
al centavo. Con menos decimales la cuenta "no da":

| Decimales | Excel devuelve | Contra los $62,247.57 reales |
|---|---:|---:|
| 2 (`4.65`) | 62,193.81 | −53.76 |
| 4 (`4.654`) | 62,247.31 | −0.26 |
| 6 (`4.654019`) | 62,247.57 | cuadra |
| 8 (`4.65401926`) | 62,247.57 | cuadra |

(caso real: subtotal $1,337,501.34)

Son 8 y no 6 por margen: el error de redondear el porcentaje crece con
el subtotal. Con 6 decimales, un subtotal de 100 millones ya se desvía
50 centavos; con 8, medio centavo.

**Ojo con el redondeo de la vista**: si el reporte o el Excel muestran
el porcentaje con menos decimales, la comprobación vuelve a fallar. Hay
que multiplicar por el valor completo.

El importe que manda sigue siendo `Total NC`, que es la suma de los
renglones. El porcentaje sirve para comprobarlo, no para producirlo:
nadie lo multiplica dentro del módulo.

### Nunca se reconstruye un importe desde el porcentaje

`_recompute_nc_amounts()` rehacía el total con
`price_subtotal × reward_percent / 100`, leyendo el porcentaje **del
campo**, o sea ya redondeado. Caso real: subtotal $1,337,501.34 con un
efectivo de `4.6540192625 %` → el campo guardaba `4.65` y la NC salía
en **$62,193.81** en vez de **$62,247.57**. $53.76 menos, por cliente.
Con cuatro decimales habría dado $62,247.31: tampoco es correcto.

Tenía excepciones (`if rim or key_sizes: return`) para los casos que
calculan renglón por renglón, pero era una lista que había que
acordarse de ampliar —la base PMS hubo que agregarla a mano— y la
promoción **por grupo con porcentaje plano nunca estuvo protegida**,
porque su rama solo escribía el porcentaje y dependía de ese recálculo.

Ahora cada rama escribe su propio importe en el momento de calcularlo
(`_prepare_result_vals` al crear el resultado, y cada
`_apply_*_group_rewards` al reasignarlo por grupo). El método se
conserva como no-op por compatibilidad.

## Dónde vive cada cosa

| Concepto | Archivo |
|---|---|
| `untaxed`, `round_money`, `percent_amount`, `format_quantity` | `models/ztyres_promo_reward_engine.py` |
| Conversión de límites de tramo | `reward_engine._tier_bounds` |
| `_effective_percent`, `_result_quantity` | `models/ztyres_promo_notas_credito_calculo.py` |
| Precio PMS a subtotal | `notas_credito._pms_unit_price_untaxed` |
