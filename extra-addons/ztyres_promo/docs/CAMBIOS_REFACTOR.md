# Refactor de promociones — qué cambió y por qué

Versión `16.0.0.13.0`. Ninguna tabla, campo público ni acción cambió de
nombre: no requiere migración manual de datos.

## 1. Correcciones que cambian resultados

### 1.1 El alcance se ignoraba cuando la política era por rin
`_get_domain()` revisaba primero si la política era *Cantidad Acumulada
por Rin* y, si lo era, regresaba de inmediato con los rines de la tabla
de políticas. Marca, tier, medida, segmento y los rines del propio
alcance se descartaban.

Efecto: la promoción DUNLOP/FALKEN pagaba NC sobre llantas **de
cualquier marca** que tuvieran esos rines. De ahí un solo cliente con
1,278 piezas, $1,602,877.72 de subtotal y $75,495.54 de NC.

Ahora el universo siempre sale del alcance y la política solo lo
restringe. **Los resultados de promociones con esta combinación bajan.**

El mismo defecto estaba en `_promo_line_matches()` (evaluación en vivo
sobre cotizaciones y facturas) y también quedó corregido.

### 1.2 El límite superior de los tramos no se aplicaba
`_get_policy_reward` solo comparaba `valor >= lower_limit` y tomaba el
mayor descuento. La columna *Hasta* era decorativa en las políticas de
Cantidad y Monto, aunque sí funcionaba en las de rin y volumen mensual.

Ahora un tramo aplica cuando `lower_limit <= valor <= upper_limit`. Los
tramos históricos con `Hasta = 0` se migran a `999999999`, así que
mantienen su comportamiento; los que tenían un tope real ahora sí lo
respetan.

### 1.3 Las líneas de resultado en cero eran invisibles para el motor
El campo `line_ids` tenía `domain=[('total_nc_untaxed','>',0)]`. Como
Odoo aplica ese dominio también al leer desde Python, el cálculo del
beneficio por grupo y el recálculo final **nunca veían** a los clientes
cuyo beneficio individual daba cero, aunque el acumulado del grupo sí
alcanzara un tramo. El filtro pasó a la vista.

### 1.4 Grupos + rin mezclaban clientes distintos
`_apply_rim_quantity_group_discounts` reasignaba el monto filtrando el
detalle solo por `rfc`. Dos clientes del mismo grupo con ventas de
mostrador comparten el RFC genérico `XAXX010101000`, así que cada uno se
llevaba el monto de los dos. Ahora se filtra por (cliente, RFC).

### 1.5 El tope de cupones se duplicaba
Las 200 piezas por producto se contaban dentro del armado de cada
resultado, o sea una vez por RFC receptor. Un cliente con facturación
fiscal y de mostrador recibía hasta 400. Ahora el tope se aplica una vez
por cliente, antes de armar los resultados, y dejó de ser una constante:
es el campo `coupon_limit_qty`.

### 1.6 La tabla de tramos equivocada en beneficios por grupo
`_apply_standard_group_discounts` usaba
`policy_line_qty_ids or policy_line_amount_ids`. Si una promoción cambió
de política y quedaron renglones viejos en la otra tabla, se usaba la
tabla incorrecta. Ahora la tabla se elige por la política vigente.

### 1.7 Contador contra contenido
El botón inteligente contaba con `search_count` sin filtro mientras la
lista mostraba solo los mayores a cero. Ahora ambos cuentan lo mismo.

## 2. Claridad del dominio

- `promo_conditions` es **Alcance** y `promo_type` es **Política**. Las
  etiquetas y las ayudas lo dicen.
- `rim_quantity` dejó de ser las dos cosas a la vez. Como alcance
  sobrevive con la etiqueta *Rines de las Políticas (heredado)* para no
  alterar promociones ya creadas, y advierte que incluye todas las
  marcas.
- La matriz `ALLOWED_POLICIES_BY_SCOPE` define qué combinaciones existen
  y una `@api.constrains` la hace cumplir. Cupones queda cerrado sobre
  sí mismo, como pediste.
- Se eliminó el `fields_get()` que escondía *Cupones* del selector de
  política: modificaba el esquema para toda la instancia, incluidas
  exportaciones y llamadas por API.
- Los algoritmos viven en `ztyres_promo.reward_engine`, un solo lugar.

## 3. Convención de límites

`0` ya no significa "sin límite". Se escribe `999999999`:

- es el valor por defecto de `upper_limit` en las cuatro tablas;
- el `init()` de cada tabla convierte los ceros existentes;
- un `onchange` evita volver a guardar un cero;
- el motor sigue leyendo `0` como infinito por si queda algún dato sin
  migrar.

## 4. UX del formulario

- Cabecera con **Resumen de la configuración**: la promoción explicada
  en español antes de calcular ("Participan… / Beneficio… / Reglas…").
- Franja amarilla de **avisos**: rines que están en la política pero
  fuera del alcance, huecos entre tramos, criterios faltantes.
- Pestaña **Definición** con los dos ejes numerados: 1. Alcance,
  2. Política. Cada tabla de tramos aparece solo con su política.
- Los campos de características se declaran **una sola vez** (antes
  estaban duplicados en dos bloques del mismo formulario).
- Resultados con sumas por columna, la columna **Detalle del beneficio**
  y el `% efectivo` bien etiquetado.
- Exclusiones de clientes y facturas juntas; presentación y topes
  informativos aparte.
- Vista de lista y buscador con Alcance, Política y agrupaciones.

## 5. Otros ajustes

- `min_qty` dejó de ser un campo muerto: es un requisito adicional de
  piezas para alcanzar un tramo. Con `0` no cambia nada, que es el valor
  de todos los registros existentes.
- `limite_qty` y `limite_amount` siguen sin intervenir en el cálculo;
  ahora está escrito en la etiqueta y en la vista.
- Los CFDI de líneas `partial` (topadas por cupón) ya se incluyen en la
  relación de origen de la NC.
- El detalle se crea en lote y los acumulados por cliente se calculan
  una sola vez; antes se recorría el detalle completo dentro de un ciclo
  por cliente y por RFC.
- Validación nueva: un mismo rin no puede estar en dos tramos que se
  traslapen.

## 6. Qué revisar después de instalar

1. Abra las promociones por rin y confirme que los rines del alcance
   incluyen los de la tabla de políticas (el aviso amarillo lo señala).
2. Revise que ningún tramo haya quedado con `Hasta` en un valor bajo por
   error: ahora sí se respeta.
3. Vuelva a calcular una promoción del periodo cerrado y compare contra
   el resultado anterior. Las diferencias esperadas son a la baja y se
   explican en la columna *Detalle del beneficio*.

## 7. Carga de códigos y cupones (16.0.0.14.0)

### Layout
La lista de productos estaba dentro de un `<group>`. En un group el
formulario se dibuja a dos columnas, así que el x2many quedaba
comprimido en una tira angosta con “Agregar una línea” colgando a la
izquierda y los botones flotando arriba, junto a la etiqueta suelta de
“Listas de Precios”. Ahora la lista va fuera del group, a ancho
completo, con la barra de botones arriba y los códigos no encontrados en
una franja de aviso en lugar de un campo de texto suelto. La pestaña
Cupones quedó igual, con la aclaración de que el monto es por pieza.

### Asistentes de importación
Los dos comparten `ztyres_promo.excel_import_mixin`:

- **Encabezados tolerantes.** Antes el archivo tenía que traer
  exactamente `codigo` y `monto` en minúsculas y sin acentos; “Código” o
  “Monto NC” fallaban. Ahora se normalizan acentos, mayúsculas y
  espacios, se aceptan sinónimos (`clave`, `sku`, `referencia interna`,
  `importe`, `monto por pieza`…) y el error dice qué columnas sí venían.
- **Botón “Descargar plantilla”** en cada asistente: genera el .xlsx con
  la hoja `datos` primero —`pandas` lee la primera hoja, así que el
  instructivo no puede ir antes— y una hoja `instrucciones`.
- **Vista con el formato a la vista**: tabla de ejemplo con los
  encabezados exactos, antes de subir nada.
- **Modo de carga**: reemplazar o agregar/actualizar.
- **Cupones sin duplicados.** El asistente siempre creaba renglones
  nuevos: cargar dos veces el mismo archivo dejaba el cupón duplicado y
  el producto se bonificaba dos veces. Ahora reemplaza o hace upsert por
  producto.
- **Validaciones**: montos negativos detienen la carga; un archivo sin
  renglones válidos avisa en lugar de terminar en silencio.

Las plantillas también van en `docs/plantillas/` por si se necesitan sin
entrar a Odoo.

---

# Versión `16.0.0.28.0` — decimales y precios PMS

No cambia ningún nombre de tabla, campo ni acción existente. Agrega la
tabla `ztyres_promo.pms_price` y tres campos a la promoción
(`key_size_base`, `pms_price_taxed`, `pms_price_ids`). No requiere
migración manual: las promociones existentes quedan con
`key_size_base = 'invoiced'`, que es el comportamiento que ya tenían.

## 1. Decimales (cambia importes, por centavos)

### 1.1 El total no era la suma del detalle
En las promociones que calculan renglón por renglón —rin y Key Sizes—
cada línea se multiplicaba sin redondear y el total era la suma de esos
floats. El detalle que se le enseña al cliente, en cambio, muestra
renglones ya redondeados a centavos: **las dos cifras no cuadraban**.

Ahora todo importe sale redondeado del motor (`round_money`,
`percent_amount`) y el total es la suma exacta de los renglones. Las
diferencias son de centavos y pueden ir en cualquier dirección.

### 1.2 Las piezas se truncaban
`int(quantity)` en los textos auditables y en el campo `quantity` del
resultado, que es `Integer`. Las cantidades vienen de sumas de floats y
las notas de crédito restan, así que `274.99999` es lo normal: un
cliente con 275 llantas aparecía con **274**. Ahora se redondea
(`format_quantity`, `_result_quantity`).

### 1.3 El `% efectivo` no se podía comprobar
Se guardaba con 2 decimales, así que multiplicarlo por el subtotal para
verificar la NC en Excel no daba: con un efectivo real de
`4.65401926 %` sobre $1,337,501.34, el `4.65` guardado devolvía
$62,193.81 contra $62,247.57 reales, y `4.6540` devolvía $62,247.31.

Ahora son **8 decimales**, la precisión con la que la multiplicación
devuelve el total al centavo (con 6 se desvía medio peso en subtotales
de cien millones). Sigue siendo informativo — el importe que manda es
`Total NC` — pero ya se puede comprobar a mano.

### 1.4 Comparaciones de porcentaje sobre floats
`discount > 0` daba verdadero para un `0.0000000001` heredado de una
importación, y se cobraba un porcentaje que en pantalla se ve como cero.
Ahora se usa `is_zero_percent`.

## 2. IVA: una inconsistencia real
En la evaluación en vivo (cotizaciones y facturas), los **cupones**
usaban el monto capturado **sin bajarle el IVA**, mientras el cálculo
definitivo sí lo bajaba. Un cupón de $150 se anunciaba en la cotización
como "$150 ganados" y la nota de crédito terminaba pagando **$129.31**.
Corregido: el cotizador y la NC final vuelven a dar el mismo número.

El resto ya era coherente. La tabla completa de qué lleva IVA y qué no
está en [IVA_Y_DECIMALES.md](IVA_Y_DECIMALES.md).

## 3. Promoción nueva: descuento sobre precios PMS
El porcentaje se cobra sobre un precio de referencia por código
(`precio PMS × piezas`) en lugar del subtotal facturado, así que la NC
por pieza es la misma sin importar a qué precio se vendió. El nivel se
sigue eligiendo con lo facturado. Se carga con un Excel de dos columnas,
`codigo` y `pms`, y al importar se declara si los precios vienen con o
sin IVA. Ver [PRECIOS_PMS.md](PRECIOS_PMS.md).

Se combina con Key Sizes sin conflicto: los Key Sizes deciden **qué**
porcentaje, la base decide **sobre qué**.

## 3B. El detalle del beneficio ahora cuadra

El `% efectivo` no reconstruye el `Total NC`, y subirlo a 4 decimales no
lo arregló: el total es la suma de importes redondeados a centavos, no
el producto de una multiplicación. En el ejemplo de `KEY_SIZES.md`, 4
decimales se desvían 4 centavos y 6 aciertan ese reparto pero no otros.

La columna **Detalle del beneficio** pasó de decir solo piezas y
porcentaje —con lo que el importe no se podía verificar— a traer cada
grupo con **la base** sobre la que se aplicó y el importe que salió, y
la suma al final:

```
Acumulado $684,450.00 | Base: 275 pza x 4.20% sobre $595,550.00 = $25,013.10
 + Key Sizes: 60 pza x 6.00% sobre $88,900.00 = $5,334.00 | Total $30,347.10
```

Aplica igual a las promociones por rin. El `breakdown` que devuelven
`rim_amounts` y `key_size_amounts` pasó de 4 a 5 elementos
(`nombre, %, piezas, base, importe`); solo lo consumen los dos
formateadores del propio motor.

## 4. Tests que ya venían fallando (se corrigió el test, no la conducta)

Al correr la suite salieron cuatro fallas ajenas a estos cambios. Las
tres de `ztyres_promo` eran tests escritos antes de decisiones de
negocio posteriores:

- `test_monto_fijo_se_reparte_sin_perder_centavos` capturaba un monto
  fijo de 1,000 y esperaba 1,000 de NC. Desde la regla "todo monto
  capturado lleva IVA" el motor devuelve 862.07. Ahora captura 1,160,
  que son 1,000 de NC; lo que el test probaba —el prorrateo sin perder
  centavos— quedó intacto.
- `TestTarjetaDeRegalo` construía la promoción sin declarar
  `gift_card_source`, y el default del campo es `product`: el fixture
  probaba el origen equivocado, el motor buscaba una plantilla por
  código que no existía y devolvía None. Ahora lo declara explícito.
- `test_entrega_como_nc_baja_el_iva` esperaba que la tarjeta emitiera
  NC. **`_gift_card_generates_nc()` devuelve False sin mirar nada**, y
  la vista lo dice, pero el campo `gift_card_delivery` sigue ofreciendo
  la opción "Nota de crédito por el valor de la tarjeta" y hasta avisa
  en rojo que se va a timbrar. **Elegir esa opción no hace nada.** El
  test se actualizó a lo que el motor hace hoy —y no al revés— porque
  la dirección contraria pondría CFDI en el SAT. Queda pendiente
  resolverlo: quitar la opción del selector, o hacer que el método lea
  el campo.

La cuarta (`test_portal_crea_draft_con_snapshot_e_idempotencia`, en
`ztyres_promotions`) falla por disponibilidad de productos en el
cotizador y no toca el cálculo de promociones.

## 3C. El importe ya no se reconstruye desde el porcentaje

Caso real reportado: subtotal $1,337,501.34, efectivo `4.6540192625 %`,
NC correcta **$62,247.57**, Odoo emitía **$62,193.81**. Faltaban $53.76
por cliente.

La causa era `_recompute_nc_amounts()`, que al cerrar el cálculo rehacía
el total con `price_subtotal × reward_percent / 100` leyendo el
porcentaje ya redondeado del campo (`4.65`). Subir el campo a 4
decimales no lo arregla: daría $62,247.31.

El importe correcto no es una multiplicación — es la suma de los
renglones, cada uno con su porcentaje y su base — así que **ninguna**
reconstrucción sirve. Ahora cada rama escribe su propio importe:

- `_prepare_result_vals` al crear el resultado (ya lo hacía);
- `_apply_tier_group_rewards`, rama de porcentaje plano (**no lo hacía**:
  escribía solo el porcentaje y dependía del recálculo — este era el
  camino que perdía dinero);
- `_apply_monthly_volume_group_rewards` (**no lo hacía**);
- `_allocate_group_fixed_amount` (**no lo hacía**);
- las de rin, Key Sizes, base PMS y tarjeta ya lo hacían.

`_recompute_nc_amounts()` queda como no-op por compatibilidad.

**Hay que volver a calcular las promociones ya procesadas**: los
resultados guardados conservan el importe viejo hasta que se recalculen.

## 3D. Precios PMS: redondeo por pieza y conversión de IVA al final

Contrastado contra la liquidación real de Bridgestone/Firestone de julio
(22 renglones, 609 piezas, $1,337,501.34 de subtotal):

- El descuento se redondea **por pieza** antes de multiplicar por las
  llantas. El convenio fija "$120.95 por pieza" y así liquida la marca;
  redondear al final daba $1.21 de más.
- Cuando el PMS se captura con IVA, el IVA se baja **al final**, sobre
  el importe de la línea. Convertir el precio primero desviaba 2
  centavos en esa misma liquidación.

Con las dos correcciones el módulo reproduce la liquidación del
proveedor al centavo.

## 3E. Base facturada: redondeo por grupo

Contrastado contra la hoja "Rin X Key Size" de la promoción de solo Key
Sizes, que trae la regla escrita: *"Primero hace la NC con base de TOTAL
13-16 con el porcentaje de la columna Porcentaje; luego con base a TOTAL
KEY SIZE con el porcentaje de la columna Key Size; después suma"*.

El importe de cada grupo se calcula sobre el subtotal del grupo y el
redondeo ocurre **una sola vez sobre la suma**. El total se reparte
luego entre los renglones (el último de cada grupo absorbe el residuo)
para que el detalle siga sumando el total.

Resultado del caso real: **61,911.79**, exacto.

Los dos redondeos conviven según la base, porque los convenios están
escritos distinto:

| Base | Redondeo | Por qué |
|---|---|---|
| Subtotal facturado | por grupo, total una vez | el convenio define "NC 13-16" y "NC Key Sizes" |
| Precio PMS | por pieza | el convenio define "$120.95 por llanta" |
