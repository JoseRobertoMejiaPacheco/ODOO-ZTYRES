# Promoción Ganada — puntos frágiles a vigilar

Este documento existe para un solo propósito: que quien toque
`discount_profiles` o el PDF de cotización/factura en el futuro sepa
que **`ztyres_promo` depende de esa estructura exacta**, y no se
sorprenda con un error de `xpath` al actualizar cualquiera de los dos
módulos.

## 1. Acople con el PDF de cotización/orden (el más frágil)

**Dónde está:**
`ztyres_promo/views/ztyres_promo_report_sale_order.xml` — anclajes
dentro del mismo template:

```xml
<xpath expr="//div[@t-if='doc.payment_discount_text']" position="after">                            <!-- resumen del documento -->
<xpath expr="//th[@name='th_taxes']" position="attributes">                                          <!-- ocultar encabezado Impuestos -->
<xpath expr="//td[@class='text-end o_price_total']/preceding-sibling::td[1]" position="attributes">  <!-- ocultar celda Impuestos -->
<xpath expr="//th[@name='th_subtotal']" position="after">                                            <!-- encabezado columna Promoción Ganada -->
<xpath expr="//td[@class='text-end o_price_total']" position="after">                                <!-- celda columna Promoción Ganada -->
```

**Por qué existe:** `discount_profiles` reemplaza (`position="replace"`)
el contenido completo de la vista `sale.report_saleorder_document`, así
que no queda ningún anclaje original de Odoo disponible. `ztyres_promo`
se engancha directamente a la tabla de productos y al `<div>` que
`discount_profiles` ya trae en su plantilla para mostrar
`payment_discount_text`. La celda de Impuestos no tiene `name` propio
en esa tabla, así que se ubica por posición (siempre justo antes de la
celda de Subtotal, con o sin columna de Descuento presente) en vez de
por atributo.

**Qué lo puede romper** (en `discount_profiles`, archivo `views/views.xml`,
template `report_saleorder_document_custom_header`):

- Eliminar o renombrar el campo `payment_discount_text` en `sale.order`.
- Cambiar ese `<div t-if="doc.payment_discount_text" ...>` por otra
  condición o quitarlo del template.
- Reordenar las columnas de la tabla de productos (ej. mover Impuestos
  a otro lugar que no sea justo antes de Subtotal), renombrar
  `th_taxes`/`th_subtotal`, o agregar/quitar columnas.
- Volver a reemplazar/reestructurar el bloque de
  "SECCIÓN DE TÉRMINOS Y CONDICIONES AL FINAL" o la tabla de productos.
- Bajar la `priority` de esa vista por debajo de la nuestra (20), o que
  alguien le suba la propia a un valor ≥ 20 — invertiría el orden de
  composición y nuestro anclaje podría no existir todavía cuando se
  aplique nuestro xpath.

**Si se rompe, el síntoma es exactamente el mismo error ya visto antes:**
`El elemento "<xpath expr="...">" no se puede localizar en la vista principal`,
pero esta vez al generar el PDF de cotización/orden (no en la lista).

**Dependencia formal:** por esto, `ztyres_promo/__manifest__.py` ahora
tiene `discount_profiles` en `depends` — es un acople real y a
propósito, no accidental.

## 2. PDF de factura (acople más liviano)

**Dónde está:**
`ztyres_promo/views/ztyres_promo_report_invoice.xml` — anclajes:

```xml
<xpath expr="//div[@class='clearfix mb-4']" position="after">          <!-- resumen del documento -->
<xpath expr="//th[@name='th_taxes']" position="attributes">            <!-- ocultar encabezado Impuestos -->
<xpath expr="//td[@name='td_taxes']" position="attributes">            <!-- ocultar celda Impuestos -->
<xpath expr="//th[@name='th_subtotal']" position="after">              <!-- encabezado columna Promoción Ganada -->
<xpath expr="//td[@class='text-end o_price_total']" position="after">  <!-- celda columna Promoción Ganada -->
```

Ninguno depende de `discount_profiles` — son puntos del propio Odoo
(`account.report_invoice_document`), que ese módulo no toca.
`discount_profiles` también se engancha en el primero, pero como
inserción "after" (agrega un hermano), no un reemplazo, así que ambos
módulos conviven sin pisarse.

**Verificado contra el arch real** (Odoo 16, confirmado por el usuario
vía Ajustes > Técnico > Vistas — a diferencia de los primeros intentos,
que adivinaron mal `account_invoice_line_subtotal`/posición relativa
para Impuestos). Dos detalles a tener presentes si esta plantilla
cambia en el futuro:
- La celda de Subtotal **no tiene** atributo `name` propio, solo
  `class="text-end o_price_total"` (coincide, por casualidad, con el
  mismo class que usa la tabla de la cotización).
- Las columnas de producto están dentro de
  `<t t-if="line.display_type == 'product'">` (no
  `<t t-if="not line.display_type">` como en la cotización) — si se
  toca esa condición, hay que ajustar el `t-if` de nuestra celda nueva
  también.

Solo se rompería si el propio Odoo/`account` cambiara esa estructura
en una actualización de versión, o si algún otro módulo instalado la
modifica.

## 3. Texto de la promoción ganada (configurable por promoción)

**Dónde está:** campo `promo_ganada_message` en
`ztyres_promo.notas_credito` (`models/ztyres_promo_notas_credito.py`),
visible en el bloque principal del formulario de la promoción.

El texto que se muestra ya **no lo redacta el código** — lo escribe
quien configura la promoción, usando texto libre más estos marcadores
(se reemplazan automáticamente):

- `{promocion}` — nombre de la promoción
- `{monto}` — monto ganado en NC, ya formateado como moneda
- `{porcentaje}` — porcentaje de descuento (vacío en promociones de
  tipo Cupones, que no tienen %)

Si el texto trae un marcador que no reconocemos (typo, por ejemplo),
se deja tal cual en el mensaje en vez de romper el cálculo. El texto
se trata siempre como texto plano, no HTML: si alguien escribe `<`,
`>` o `&` se muestran literalmente, no se interpretan como markup.

Si una promoción no tiene este campo configurado (por ejemplo,
promociones creadas antes de que existiera el campo), se usa una
frase por defecto de respaldo — el sistema no se rompe, solo se ve
menos personalizado.

Esto solo aplica a la parte **Global** de `promo_display_mode`. El
desglose **Por Producto** sigue teniendo un formato fijo (producto →
monto), no es configurable por texto.

## 4. Corte de fecha temporal (recordatorio para quitar)

**Dónde está:**
`ztyres_promo/models/ztyres_promo_document_promo_mixin.py`,
constante `_PROMO_EVAL_CUTOFF_DATE = date(2026, 7, 19)`.

Documentos con fecha anterior a esa siempre dan `0` / texto vacío, a
propósito, para no "revivir" miles de cotizaciones/facturas históricas
al instalar el módulo. No es algo que se pueda romper por otro módulo,
pero es fácil olvidar que está ahí — está marcado como **TEMPORAL** en
el propio código, con instrucciones de qué borrar cuando ya no se
necesite.

## 5. `display_type` NO significa lo mismo en sale.order.line y account.move.line

**Dónde está:** `ztyres_promo/models/ztyres_promo_notas_credito_eval.py`,
método `evaluate_document`, filtro de `matched_lines`.

Este fue un bug real (ya corregido) que vale la pena documentar porque
es fácil reintroducirlo: en `sale.order.line`, una línea de producto
normal tiene `display_type = False` (falso). Pero en
`account.move.line`, una línea de producto normal tiene
`display_type = 'product'` — un **string, o sea "verdadero"**. Filtrar
con `not line.display_type` funciona en cotizaciones/órdenes pero
**excluye todas las líneas de producto reales** en facturas, dejando
todo en cero silenciosamente (ni error, ni cálculo, ni texto, ni PDF —
exactamente el síntoma que se reportó).

La corrección: en vez de asumir "falsy = producto", se excluye
explícitamente por valor conocido de sección/nota:

```python
lines.filtered(
    lambda l: l.product_id
    and l.display_type not in ('line_section', 'line_note')
    and self._promo_line_matches(l)
)
```

Esto funciona igual en ambos modelos. Si en el futuro se agrega
soporte para otro modelo de líneas (ej. `purchase.order.line`), hay
que verificar primero qué valor toma `display_type` ahí para una línea
de producto normal — no asumir que es igual a los otros dos.


