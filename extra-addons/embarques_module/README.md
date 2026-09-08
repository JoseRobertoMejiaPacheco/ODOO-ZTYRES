# Embarques — 16.0.1.25.0

## Cambios 16.0.1.25.0

- El destino se recalcula al cambiar la ciudad o localidad de entrega. Una
  localidad anterior ya no puede enviar el traslado a otro municipio.
- Se recupera el **Costo Logístico Manual** y se suma al costo calculado.
- Los dos reportes de separación incluyen **Medida** y ordenan por ella dentro
  de su orden actual de marca y cliente.
- En Destinos, los renglones nuevos se capturan arriba de la lista.
- Los vehículos se administran en un catálogo independiente con Nombre y
  Cubicaje, sin exigir información de Carta Porte.

## Separación y validación de almacén

El encabezado muestra clientes, pedidos, facturas, llantas y el avance de
almacén: **Pedido, Reservado y Hecho**. La validación se realiza por
picking/producto y exige `Pedido = Reservado + Hecho`; no se compensan faltantes
de un producto con sobrantes de otro.

Los botones **Excel por marca** y **Excel marca y cliente** sólo generan el
archivo cuando todas las líneas están conciliadas. Ambos desglosan origen,
producto, lote, pedimento y ubicación origen. El segundo incluye además cliente,
pedido y facturas para facilitar la separación física del embarque.

El reporte por cliente conserva el orden de carga del embarque y agrega una
casilla **Revisado** después de Hecho para marcarla manualmente al imprimir.
El reporte general agrupa por marca según la primera aparición de cada marca en
el embarque; no aplica orden alfabético.
Los dos Excel están diseñados para impresión económica en escala de grises: sin
fondos oscuros, con encabezado gris claro y separadores por cliente/marca.

El módulo arma embarques
y calcula el **descuento directo en factura** que les corresponde.

## La política

El cumplimiento se decide **por embarque** usando cantidad de llantas. El
descuento y su autorización se deciden **por picking**, cruzando la zona de su
destino con los rangos numéricos permitidos. Los m³ son únicamente informativos:

|        | 1200 | 650 | 250 | 120 |
|--------|------|-----|-----|-----|
| Zona 1 | 5%   | 4%  | 3%  | 2%  |
| Zona 2 | 3%   | 2%  | —   | —   |
| Zona 3 | 0%   | 0%  | —   | —   |

Un cruce vacío son las celdas "NO" del Excel: ese rango no aplica en esa zona.
Un cruce con 0% sí aplica, pero no descuenta nada — es la Zona 3.

Además, cada destino declara **qué rangos comerciales admite**. Por ejemplo,
puede admitir 1200 pero no 650, y eso queda capturado en la tabla de destinos.

## Paquetería

Es la otra mitad del Excel: **lo que el cliente paga por pieza** según su
destino.

Cada destino trae *SIN COSTO* o un importe por pieza — 90, 100, 110, 128, 140,
160, 170, 180, 190, 250, 260, 280 o 320.

### Cómo se cobra

Cuando el destino está marcado **Con costo**, se agrega al presupuesto una
línea de **Paquetería** por `piezas × importe`. El campo **Envío gratis desde
(llantas)** define el mínimo propio del destino: con 8 cobra de 1 a 7 y desde
8 el envío es gratis; con 0 siempre cobra. **Sin costo** siempre devuelve
cero. Se recalcula al cambiar líneas o dirección de entrega. Sólo toca
presupuestos en borrador o enviados: una vez confirmado el pedido no se altera
el importe.

La línea de paquetería **no recibe** el descuento del embarque: el descuento
aplica sobre la mercancía, no sobre el flete.

El cobro necesita un producto de servicio, que se crea al instalar y se asigna
en Ajustes ▸ Compañía ▸ Embarques. Sin producto asignado, no se cobra nada.

**Un dato a revisar**: Hermosillo trae "SI" en la columna de paquetería, donde
todos los demás traen importe o SIN COSTO. Quedó **en blanco** — no cobra — y
aparece en el filtro *Paquetería en blanco* de la lista de destinos. Ojo con la
diferencia: *Sin costo* es una decisión (el destino no paga flete); en blanco es
un dato que falta.

## Validaciones de negocio

La tabla de destinos muestra **Correcto**, **Advertencia** o **Error** con el
detalle correspondiente. Se bloquean configuraciones que puedan producir un
cálculo incorrecto: destino sin ciudad, zona o rangos; tarifa negativa,
envío gratis negativo y la contradicción
`Con costo` + `Envío gratis desde 1`.

Antes de avanzar un embarque o generar sus reportes se revisan en conjunto el
vehículo, su cubicaje, la ruta, traslados cancelados o duplicados, compañía,
pedido de venta, orden de carga único, destino, ciudad, zona, rangos y producto
de paquetería. Los errores se muestran juntos para corregirlos en una sola
pasada. Los productos sin volumen son advertencias: permiten continuar, pero
quedan visibles para el usuario.

Los rangos activos no pueden duplicar nombre o capacidad; y dentro de una zona
un rango de mayor capacidad no puede tener un porcentaje menor que un rango
inferior.

## Modelos

| Modelo | Tabla | Para qué |
|---|---|---|
| `embarques.embarques` | Embarque | El viaje: traslados, unidad, descuento |
| `embarques.zona` | Zona | Zona 1, 2, 3 |
| `embarques.unidad` | Rango de Transporte | Umbral comercial en llantas |
| `embarques.vehicle` | Vehículo | Nombre y cubicaje de unidades propias o externas |
| `embarques.discount.policy` | Política de Descuento | La matriz de arriba |
| `embarques.destino` | Destino | Ciudad → zona + rangos + paquetería |
| `embarques.stage` | Etapa | Nuevo, En Proceso, En Tránsito, Entregado |
| `embarques.tag` | Etiqueta | |
| `rutas_embarques` | Ruta | |

Más estos campos añadidos a modelos de Odoo:

- `embarques.vehicle` guarda únicamente el nombre y el cubicaje. La unidad
  puede ser propia o externa y no necesita información de Carta Porte.
- Al actualizar desde la versión anterior, las unidades de Carta Porte que ya
  tenían cubicaje se copian al nuevo catálogo y se conservan en los embarques.
- `stock.picking.load_order` — el orden de carga. El picking guarda su descuento,
  solicitud manual, estado, solicitante, revisor y fecha de revisión.
- `sale.order.embarque_discount_percentage` — el porcentaje que el embarque
  fijó, esperando a que se genere la factura.
- `account.move.line.embarque_discount_percentage` y
  `embarque_discount_applied` — la constancia de lo aplicado, que además impide
  aplicarlo dos veces.
- `res.company.paqueteria_product_id` — el producto con el que se cobra el
  flete.

## Cómo se calcula

`Embarques._evaluate_discount()` valida en este orden y se detiene en la primera
que falla, para poder decir exactamente qué faltó:

1. ¿Hay traslados? → *Sin traslados*
2. ¿El destino existe y tiene zona? → *Destino sin política*
3. ¿Tiene rangos numéricos permitidos? → *Sin rangos comerciales*
4. Revisa esos rangos de mayor a menor.
5. ¿El cliente llena solo el rango o el embarque cumple la consolidación:
   desde 250 llantas, máximo 2 clientes y participación mínima individual?
6. Cruce zona × rango → *Sin política* si no hay renglón.

Al cumplir, el porcentaje baja a los pedidos de venta de los traslados y se
conserva también en cada picking. Después se conserva como porcentaje logístico del pedido/embarque. El campo estándar
`discount` de las líneas de factura **no se modifica** por logística. El beneficio se
materializa exclusivamente mediante una **Nota de Crédito logística** asociada a la
factura origen.

Las llantas se cuentan sobre la cantidad **solicitada** en los movimientos, no
la reservada: una llanta sin reservar no tumba por sí sola un descuento ya
calculado.

## Descuento manual por picking

Un embarque puede llevar destinos de zonas distintas. Cada picking recibe el
porcentaje de su ciudad/zona. Puede cumplir porque su cliente llena el rango por
sí solo o porque consolida con el otro cliente del mismo embarque. Ya no depende
de ciudades: se autoriza desde 250 llantas, con máximo 2 clientes y el porcentaje
mínimo capturado en el embarque (50% por defecto). Se suman ambas compras para
comprobar el rango y se valida individualmente la participación. Cada cliente
conserva el porcentaje de su propio destino; nunca se usa el máximo de la pareja.

El vehículo se selecciona desde el catálogo propio de Embarques. Solamente se
capturan **Nombre** y **Cubicaje (m³)**. Esto permite usar unidades propias o
externas sin obligar a registrarlas en Carta Porte.

Los rangos son exclusivamente comerciales. El motor revisa todos los rangos
permitidos de cada destino, de mayor a menor, y selecciona el primero que la
cantidad de llantas del cliente —solo o mediante consolidación válida— alcanza. El
vehículo y sus m³ no intervienen en el porcentaje.

Cada embarque muestra sus **Stops del Embarque** según los clientes distintos.
Ahí mismo se capturan **Máximo de Stops para Consolidar**, **Consolidación desde
(llantas)** y **Participación Mínima por Cliente (%)**. Los valores de negocio
predeterminados son 2, 250 y 50%. Las ciudades del destino ya no habilitan ni
bloquean la consolidación.

1. Quien arma el embarque captura **Descuento Solicitado (%)** y el motivo.
2. El picking pasa a *Por autorizar*. **El descuento vigente no cambia**
   mientras tanto.
3. Finanzas —grupo *Autorizar descuento manual*— usa **Autorizar** o
   **Rechazar** en el renglón o formulario del picking. Finanzas no captura el porcentaje: sólo
   aprueba o niega lo que se pidió.
4. Lo autorizado queda marcado como manual en ese picking y el recálculo
   automático ya no lo pisa.

Hay un tope: lo solicitado no puede superar el mejor porcentaje que la matriz
otorgue a los rangos permitidos de los destinos involucrados. Si no hay política
aplicable, no hay tope y la decisión queda entera en Finanzas.

### Rastro de auditoría

El embarque lleva chatter (`mail.thread` / `mail.activity.mixin`). Cada paso del
descuento queda registrado con autor y fecha:

- **Solicitud** — quién pidió, qué porcentaje y con qué motivo.
- **Autorización** — quién autorizó, porcentaje y motivo de la solicitud.
- **Rechazo** — quién rechazó y a qué porcentaje automático se regresó.
- **Retiro del manual** — quién liberó el embarque al cálculo automático.

Además llevan seguimiento automático (`tracking`) los campos Etapa, Ruta,
Descuento Aplicado, Descuento Solicitado y Estado del Descuento.

Los campos `discount_requested_by`, `discount_approved_by` y
`discount_approval_date` conservan el **último** estado, para poder filtrar y
reportar sin leer el chatter.

## Captura manual de los destinos

Los registros de `embarques.destino` se capturan exclusivamente desde
**Embarques ▸ Configuración ▸ Destinos**. El módulo no contiene ciudades
precargadas ni acciones para importar políticas.

En cada destino también puede capturarse **Localidad SAT**
(`l10n_mx_edi.res.locality`). Es una referencia fiscal opcional para Carta
Porte, se muestra junto a Ciudad y Estado y debe pertenecer al mismo estado.
No interviene en rutas, consolidación, descuentos ni paquetería.

La columna **Validación** se refresca al editar ciudad, localidad, zona,
rangos o paquetería. Si se captura una tarifa positiva y Paquetería está
vacía, se interpreta automáticamente como **Con costo**; esto evita conservar
la advertencia «paquetería sin definir» cuando la tarifa ya fue capturada.
El recálculo almacenado queda a cargo de `@api.depends`, evitando llamadas
recursivas desde `write()`.
**Sin costo** y una tarifa/mínimo son mutuamente excluyentes: al elegir Sin
costo se limpian y bloquean ambos importes. Si un dato existente tiene tarifa
positiva, la migración lo conserva cambiando el tipo a **Con costo**.

## Qué se quedó fuera a propósito

Todo esto existía en la versión anterior y ya no sostenía nada:

- **Catálogo de descuentos** (`embarques.invoice.discount`). El porcentaje vive
  en la matriz y viaja como número; no hay que mantener un catálogo aparte.
- El **cargo por llantas mínimas** que traía la versión anterior
  (`min_llantas` + costo por llanta genérico). Lo reemplazó la paquetería con
  los importes reales del Excel, que es la misma idea pero con datos.
- La consolidación heredada por ciudades. Ahora la regla vive en cada embarque:
  mínimo 250 llantas, máximo 2 clientes y 50% mínimo por cliente de manera
  predeterminada.
- **Descuento único en el embarque**. Ahora el picking conserva su propio
  cálculo y autorización.
- `semaforo`, `bus`, `volumen_disponible`, `priority`, `color`, `sequence` en el
  embarque: nunca se escribían.
- El campo **Notas** del embarque (el chatter cubre lo mismo y con autor).
- Referencias a campos de Studio (`x_studio_vol_uni`, `x_studio_cantidad`,
  `x_studio_reservado`, `x_studio_estatus_apartado`). El volumen y el peso ahora
  salen de `product.volume` y `product.weight`.
- Los archivos `cleanup_*.xml`.

## Costo logístico, facturación múltiple y cierre

El **Costo Logístico** se calcula sobre el **Total del Embarque antes de IVA**.
Cuando los pickings tienen porcentajes distintos se calcula la parte antes de
IVA de cada picking por su porcentaje y después se suman los importes. El campo
anterior **Facturado antes de IVA** ya no se utiliza ni se muestra.

Antes de publicar cualquier factura, el módulo vuelve a sincronizar el
descuento de cada línea desde sus pedidos de venta. Esto cubre la creación
múltiple de facturas y facturas que agrupan varios pedidos. Se conserva el
descuento comercial base y se reemplaza únicamente el componente logístico,
evitando duplicarlo. Si una sola línea mezcla pedidos con porcentajes distintos
—o pedidos con y sin embarque— se bloquea la publicación y se pide separarla.

Las etapas sólo pueden avanzar una posición: Nuevo → En Proceso → En Tránsito
→ Entregado. No se permite saltar ni regresar. Para entrar a **Entregado**,
todos los traslados deben estar Hechos y Pedido debe coincidir con Reservado +
Hecho. Una vez Entregado, el embarque queda bloqueado en la vista y en el
servidor: no se puede editar, recalcular, aprobar descuentos, cambiar traslados
ni eliminar el registro. Al consultar o generar reportes de un embarque ya
entregado no se vuelven a ejecutar las validaciones de preparación; si se
intenta avanzarlo nuevamente, se informa directamente que ya está Entregado.

## Captura simplificada

En **Destinos**, **Nombre manual** siempre está visible y editable. Si se captura,
tiene prioridad como nombre mostrado; si queda vacío, el nombre se obtiene de
la **Localidad SAT** y después de **Ciudad / Municipio**. Por ejemplo, Localidad
Los Mochis + Municipio Ahome + Estado Sinaloa se muestra como **Los Mochis**,
salvo que se haya escrito otro Nombre manual.

En **Rangos y Descuentos**, cada registro es una combinación reutilizable, por
ejemplo **650 → 4%** o **650 → 3%**. En cada destino se seleccionan varias de
estas combinaciones mediante etiquetas; no existen cabeceras ni perfiles.

## Carga inicial LOGISTICO- AGOSTO 2026

Al instalar o actualizar se cargan de forma idempotente 9 zonas, los rangos
1200, 650, 250, 120 y 30, las combinaciones únicas de rango y descuento, y
1,093 destinos únicos del archivo fuente. Una misma zona puede usar porcentajes
distintos para el mismo rango según el destino.

El cargador busca Estado por su código oficial y compara Localidad SAT y
Ciudad/Municipio ignorando acentos. Si no encuentra el lugar en los catálogos
de Odoo, conserva el texto fuente en **Nombre manual**. Los registros ya
cargados, identificados por su clave de plantilla, no se sobrescriben en una
actualización posterior.

Los nombres manuales se consideran duplicados por **Nombre + Estado**, no sólo
por nombre. Esto permite casos reales como Tepetongo, Zacatecas y Tepetongo,
Michoacán. Antes de crear, el cargador también busca si ya existe el mismo
destino oficial o manual y lo reutiliza sin duplicarlo.

Los valores N/A simplemente no se seleccionan. Un registro con 0% significa que
el rango sí aplica, pero no otorga descuento. Cada destino puede seleccionar
varias etiquetas, aunque nunca dos porcentajes diferentes para el mismo rango.

El costo de paquetería por pieza proviene de la fila individual de Hoja1. El
mínimo para envío gratis se toma de Hoja2: 100 piezas hasta 164 km, 250 piezas
de 165 a 385 km y 650 piezas de 386 a 1,152 km. Los recorridos mayores quedan
con cero como mínimo pendiente, tal como aparece incompleta la tabla fuente.

## Instalación

```bash
./odoo-bin -i embarques_module -d TU_BASE --stop-after-init
```

Al ser módulo nuevo, si ya tienes instalada la versión anterior **desinstálala
primero** y considera que eso borra sus tablas — incluidos los embarques ya
capturados. Si necesitas conservarlos, dímelo y armo el script de traspaso.

Dependencias principales: `stock`, `mail`, `sale`, `sale_stock`, `account`,
`l10n_mx_edi_stock`, `base_address_extended` y `l10n_mx_edi_extended`. La
ciudad debe estar capturada como `city_id` en la dirección de entrega; la
Localidad SAT es complementaria y opcional.

## Puntos a definir

1. **Qué cuenta como llanta.** `Embarques._is_llanta()` cuenta cualquier
   producto almacenable o consumible. Si sólo son ciertas categorías, es una
   línea en ese hook.
2. **Llenar la unidad es estricto**: `llantas >= capacidad_llantas`, sin
   tolerancia. Los m³ sólo estiman la ocupación física del camión.
3. **Suma vs. cascada** cuando la línea ya trae descuento propio: hoy se suman,
   no se combina con `sale.order.line.discount`; el porcentaje logístico se usa sólo para calcular la NC.
4. **Paquetería por pieza vs. por envío.** Los importes se cobran multiplicados
   por las piezas. Si en realidad son tarifa plana por envío, se ajusta en
   `EmbarquesDestino._paqueteria_unit_cost()`.
