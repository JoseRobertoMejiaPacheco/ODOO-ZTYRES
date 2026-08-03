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
