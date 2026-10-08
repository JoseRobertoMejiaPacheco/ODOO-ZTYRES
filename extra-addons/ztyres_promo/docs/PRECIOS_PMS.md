# Precios PMS: pagar sobre un precio de referencia

## Qué resuelve

En las promociones de siempre, el porcentaje se cobra sobre **lo que se
facturó**. Dos clientes que compraron el mismo código con el mismo
convenio reciben notas de crédito distintas, porque uno lo vendió a
$2,100 y el otro a $1,890.

Con esta promoción el porcentaje se cobra sobre el **precio PMS**: un
precio de referencia por código, el mismo para todos. La nota de crédito
por pieza queda igual sin importar a qué precio se vendió ni qué
descuentos se dieron.

```
descuento por pieza = redondear(precio PMS capturado × % del nivel, 2)
NC de la línea      = redondear(piezas × descuento por pieza ÷ factor IVA)
```

donde el factor de IVA es 1.16 si el PMS se capturó con IVA y 1.0 si no.

El precio al que se facturó **no interviene en el importe**.

**El redondeo por pieza importa.** El convenio fija el descuento por
llanta —"$120.95 por pieza"— y la marca liquida multiplicando esa cifra
ya redondeada. Redondear al final (`piezas × PMS × %`) da unos centavos
de más: en la liquidación real de julio, $1.21 sobre 22 renglones. Basta
para que la liquidación no cuadre contra la del proveedor.

## Lo que NO cambia

**El nivel se sigue eligiendo con lo facturado.** El acumulado es el de
siempre: piezas en política por Cantidad, subtotal real en política por
Monto. El PMS solo cambia la base sobre la que se multiplica el
porcentaje, nunca el tramo alcanzado.

Se hizo así a propósito. La meta del convenio ("llegar a 600 mil") se
mide contra lo que el cliente efectivamente compró; si el acumulado se
midiera con precios de lista, un cliente podría alcanzar un nivel que su
factura no respalda.

## Cómo se captura

Botón **Cargar precios PMS (.xlsx)**, en *Definición de la promoción* →
*Base de cálculo*. Dos columnas:

| codigo | pms |
|---|---:|
| 10871003 | 2141.11 |
| 10492003 | 2212.10 |

`pms` es el precio de **una pieza**. No es un porcentaje, no es un
descuento y no es dinero que se entregue: es la base.

Al importar se eligen tres cosas:

- **Los precios del archivo vienen** con IVA o sin IVA (ver abajo).
- **Cobrar el porcentaje sobre estos precios**: deja la promoción
  calculando sobre el PMS. Sin esta opción los precios quedan cargados
  pero no se usan.
- **Agregar también a los productos participantes**: solo si el alcance
  es una lista de códigos. Viene apagado, porque lo normal es que el
  alcance ya esté definido por marca/rin/medida.

## El IVA

**Los precios PMS son el único importe del módulo que puede venir de las
dos formas.** Todo lo demás se captura con IVA por convención (ver
`IVA_Y_DECIMALES.md`); las listas PMS de las marcas circulan sin IVA
casi siempre, pero no siempre, y por eso se pregunta.

La nota de crédito se emite sobre el subtotal. Si los precios traen IVA,
el sistema se lo baja **al final**, sobre el importe de la línea, y no
al principio sobre el precio.

El orden no es intercambiable. El convenio fija el descuento por pieza
sobre su propio precio de lista ("$120.95 por llanta, tomado del PMS con
IVA"); bajarle el IVA al precio antes de sacar el porcentaje redondea un
número intermedio que el convenio nunca menciona, y el resultado se
desvía centavos del papel del proveedor. **Equivocarse aquí
mueve la NC un 16%**, en la dirección que le toque:

| Se capturó | Se marcó | Resultado |
|---|---|---|
| sin IVA | sin IVA | correcto |
| con IVA | con IVA | correcto |
| con IVA | sin IVA | NC **16% más alta** de lo pactado |
| sin IVA | con IVA | NC **16% más baja** de lo pactado |

Antes de aprobar: tome un código, compare su precio PMS contra el precio
unitario de una factura real. Si son parecidos, el archivo viene sin
IVA; si el PMS es ~16% mayor, viene con IVA.

## Dos promociones en una: PMS y listas normales

Es el caso real, no una excepción rara. Un mismo convenio suele cubrir
dos poblaciones de códigos:

- Los que están en la **tabla PMS** (cargados a mano desde el archivo
  de la marca): cobran sobre `precio PMS × piezas`.
- Los de las **listas de mayoreo y outlet**, que ya están en Odoo con
  su precio correcto y no aparecen ni en el PMS ni en los Key Sizes:
  cobran sobre su **subtotal facturado**.

Se capturan como **una sola promoción**. No hace falta partirla en dos:
basta con que la tabla PMS traiga solo los códigos que van sobre PMS.
El resto cae al subtotal facturado por sí solo.

La columna **Detalle del beneficio** separa las dos poblaciones para
que cada una se pueda cuadrar por su lado:

```
Acumulado $1,012,002.20
  | Base (PMS):       40 pza x 4.20% sobre  $65,615.52 =  $2,755.86
  + Base (facturado): 35 pza x 4.20% sobre  $54,050.00 =  $2,270.10
  + Key Sizes (PMS): 372 pza x 4.80% sobre $809,255.83 = $38,843.10
  | Total $43,869.06
```

Cuando la promoción no usa PMS en absoluto, las etiquetas se quedan en
`Base` y `Key Sizes`: no hay ambigüedad que aclarar.

## Un participante sin precio PMS

Cobra sobre su **subtotal facturado**, como siempre. No se le pone base
cero.

Es una decisión deliberada: la base cero le quitaría la nota de crédito
a ese cliente sin que nadie se enterara hasta que reclamara. El fallback
se avisa en dos lugares — en los avisos amarillos del formulario (cuando
el alcance es una lista de códigos y se puede saber con certeza) y en la
columna **Detalle del beneficio** del resultado.

## Se combina con Key Sizes

Son dos ejes distintos y funcionan juntos:

- **Key Sizes** decide *qué porcentaje* cobra cada producto.
- **Base PMS** decide *sobre qué* se aplica ese porcentaje.

Una promoción puede tener las dos cosas: los Key Sizes cobran su columna
de porcentaje, y todos cobran sobre precio PMS.

## Ejemplo real (Bridgestone/Firestone, julio)

Convenio: 4.20% general, 4.80% para los Key Sizes, sobre precio PMS.

```
Código      pza    Facturado   PMS unit.      %   Desc/pza          NC
10871003     20    48,637.00    2,519.83   4.80     120.95    2,419.00   KEY
10281003     16    25,594.08    1,599.12   4.80      76.76    1,228.16   KEY
18488003     12    33,577.92    2,938.39   4.80     141.04    1,692.48   KEY
17160003     20    37,215.80    1,902.85   4.20      79.92    1,598.40
14961003    200   473,942.00    2,523.83   4.80     121.14   24,228.00   KEY
   ... (22 renglones en total)
--------------------------------------------------------------------------
TOTAL       340  1,337,501.34                                65,556.71
```

Sobre el subtotal facturado, la misma promoción habría pagado
$62,167.00: **$3,389.71 menos**. Esa diferencia es exactamente el
motivo de la promoción — el PMS es más alto que el precio al que se
vendió.

El **Total NC** es la suma exacta de los renglones ya redondeados a
centavos. El `% efectivo` del resumen (aquí 4.4338%) es NC ÷ subtotal
facturado: no es un porcentaje capturado y no sirve para reconstruir el
importe — con base PMS ni siquiera daría el mismo número, porque el
importe no salió del subtotal facturado.

## Limitaciones

- Solo con política por **Cantidad** o por **Monto**, y solo con Tipo de
  Beneficio **Porcentaje**. Un monto fijo o una tarjeta no se
  multiplican por ninguna base; el formulario lo avisa y el cálculo los
  ignora.
- **Un precio por código y por promoción.** No hay precios por cliente,
  por lista ni por fecha. Si el PMS cambia a media promoción, hay que
  decidir con cuál se paga el periodo completo y volver a cargar.
- El aviso de "participante sin precio PMS" solo se puede comprobar con
  certeza cuando el alcance es *Productos / Códigos Específicos*. En los
  alcances por características habría que resolver el dominio contra
  todo el catálogo, y un aviso a medias sería peor que ninguno.
- Si se elige la base PMS y **no hay tabla cargada**, el cálculo se
  detiene con un error. Es el único descuido que de otro modo pasaría
  desapercibido: la promoción pagaría sobre lo facturado sin avisar.
