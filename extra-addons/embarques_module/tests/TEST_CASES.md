# Casos de prueba: rangos y consolidación por embarque

## Regla base

- Consolidación desde: 250 llantas.
- Máximo de stops/clientes: 2.
- Participación mínima individual: 50% del rango evaluado.
- Las ciudades no intervienen en la consolidación.
- Cada cliente conserva el porcentaje de su propio destino.

## Casos

- Rango 250, clientes 125 + 125: suman 250 y ambos cumplen 50%; ambos aplican.
- Rango 250, clientes 100 + 150: suman 250, pero el primero no alcanza 125;
  la pareja no consolida.
- Rango 650, clientes 325 + 325: ambos aplican.
- Rango 650, clientes 500 + 200: suman 700, pero el segundo no alcanza 325;
  la pareja no consolida. El primero tampoco llena individualmente 650.
- Rango 650, clientes 392 + 203: no completan el rango y tampoco cumplen ambos
  la participación; ninguno aplica.
- Rangos 1200 y 650, clientes 600 + 600: aplica el rango 1200.
- Rangos 1200 y 650, clientes 500 + 200: no aplica 1200 ni 650, porque en 650
  el segundo cliente no alcanza el 50%.
- Un solo cliente con 650: cumple individualmente, sin consolidación.
- Dos clientes de ciudades o estados distintos: pueden consolidar si cumplen
  cantidad, rango y participación; la ciudad ya no es una condición.
- Tres clientes dentro del embarque: se permite guardar la ruta, pero sus
  cantidades no se suman para descuento y se muestra advertencia.
- Dos pickings del mismo cliente: cuentan como un solo stop y sus cantidades se
  acumulan para evaluar a ese cliente.
- Cambiar mínimo, máximo o porcentaje: el descuento se recalcula al guardar.
- Intentar guardar máximo mayor a 2, mínimo menor a 250 o porcentaje fuera de
  0–100: debe bloquearse con un mensaje claro.

Los reportes de separación deben seguir bloqueados si Pedido no coincide con
Reservado + Hecho; esta validación es independiente del descuento.

## Paquetería

- Consolidar clientes no crea un cargo adicional por stop.
- La línea de paquetería existente continúa dependiendo del destino y del
  mínimo de envío gratis configurado en el pedido.
- Al seleccionar **Cliente recoge**, el pedido no debe crear línea de
  paquetería; si ya existía, debe eliminarla al guardar o recalcular.
- Al seleccionar **Paquetería del cliente**, el pedido no debe crear línea de
  paquetería; si ya existía, debe eliminarla al guardar o recalcular.
- Al seleccionar **Vendedor lleva**, el pedido no debe crear línea de
  paquetería; si ya existía, debe eliminarla al guardar o recalcular.
- Al volver a una forma de entrega con cargo, debe aplicarse nuevamente la
  tarifa configurada en el destino, sin alterar los demás cálculos.

## Cambio de ciudad y destino

- Cambiar la ciudad de entrega de León a Zapopan, aunque la dirección conserve
  una localidad anterior. El destino debe recalcularse usando Zapopan y nunca
  conservar León de los Aldama.
- Caso de control: `ZTYRES/ENTREGA/CLIENTE/168399` debe detectar Zapopan al
  volver a calcular o avanzar el embarque.

## Costo logístico manual

- Capturar un Costo Logístico Manual y comprobar que el Costo Logístico final
  sea la suma del costo calculado más el importe manual.
- El Costo Logístico Calculado debe conservarse visible por separado.

## Reportes por medida

- Excel por marca: conservar el orden de aparición de las marcas y ordenar las
  medidas dentro de cada marca.
- Excel marca y cliente: conservar el orden de los clientes y las marcas, y
  ordenar las medidas dentro de cada bloque.
- Ambos reportes deben mostrar la columna Medida.

## Vehículos

- Permitir crear unidades propias o externas capturando solamente Nombre y
  Cubicaje.
- Al actualizar, migrar las unidades anteriores de Carta Porte que ya tengan
  cubicaje y conservar su selección en los embarques existentes.

## Integridad de configuración

- Bloquear un destino sin zona o sin rangos permitidos.
- Bloquear `Con costo` junto con `Envío gratis desde = 1`.
- Bloquear rangos activos con el mismo nombre o capacidad.
- Bloquear un vehículo de Carta Porte sin capacidad útil en m³ u operador.
- Bloquear porcentajes decrecientes al aumentar la capacidad dentro de la zona.
- Antes de avanzar o reportar, mostrar juntos los errores de unidad, operador,
  ruta, traslados, orden de carga, destino y producto de paquetería.

## Costo logístico y facturación

- Total antes de IVA de $100,000 y descuento uniforme de 4%: costo logístico
  de $4,000.
- Picking de $60,000 al 4% y otro de $40,000 al 3%: costo de $3,600.
- Crear varias facturas en una operación: todas las líneas embarcadas deben
  llevar el descuento antes de publicar.
- Sincronizar dos veces: el descuento no debe duplicarse.
- Mezclar en una línea pedidos con porcentajes distintos: bloquear publicación.

## Etapas y bloqueo final

- No permitir pasar directamente de Nuevo a En Tránsito o Entregado.
- No permitir regresar de En Tránsito a En Proceso.
- No permitir Entregado si algún traslado no está Hecho.
- No permitir Entregado si Pedido, Reservado y Hecho no están conciliados.
- Después de Entregado, bloquear edición, eliminación, recálculo, descuentos y
  cambios en movimientos relacionados.
# Trazabilidad en factura y destino obligatorio

## Factura

1. Agregar a un embarque un traslado cuyo destino tenga rango y descuento.
2. Calcular el descuento y crear la factura desde el pedido.
3. Publicar la factura.
4. Confirmar que cada línea de producto muestra `% Descuento Logístico` y
   que el descuento estándar conserva la suma comercial correspondiente.
5. Confirmar que `Monto Descuento Logístico` contiene sólo `precio × cantidad
   × porcentaje logístico`, y que la cabecera muestra la suma de las líneas.

## Nota de crédito por producto

1. Desde la factura anterior usar **Agregar nota de crédito**.
2. Conservar al menos una línea de producto y publicar.
3. Confirmar que `% Descuento Logístico` vale `0`.
4. Confirmar que `% Logístico Original` conserva el porcentaje de la factura
   y que `Línea de Factura Origen` apunta a la línea devuelta.
5. Confirmar que el total acreditado coincide con el importe originalmente
   facturado para la cantidad devuelta.
6. Confirmar que `Monto Descuento Logístico` vale `0` en la nota de crédito.

## Cliente sin destino

1. Elegir un traslado cuya dirección de entrega no coincida con ningún
   `embarques.destino` activo.
2. Agregarlo a un embarque y guardar el borrador: debe permitirse.
3. Abrir la lista de embarques: debe mostrarse sin lanzar errores.
4. Pulsar **Avanzar embarque**.
5. Confirmar que sólo en ese momento el sistema bloquea la operación e
   identifica el traslado cuyo destino está sin configurar.

## Orden inicial automático

1. Agregar varios traslados que tengan inicialmente Orden de Carga `10`.
2. Guardar el embarque.
3. Confirmar que quedan `10, 20, 30...` sin mostrar un error de duplicados.
4. Cambiar manualmente el orden y confirmar que los valores únicos capturados
   por el usuario se conservan.
5. En un embarque anterior cuyos traslados aún tengan todos `10`, pulsar
   **Avanzar embarque** y confirmar que se normalizan antes de validar destinos.
