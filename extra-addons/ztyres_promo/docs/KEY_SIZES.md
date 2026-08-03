# Key Sizes: productos que cobran otro porcentaje

## Cómo se captura

Todo vive en **una sola tabla**, la de niveles de siempre. Se le agregó
una columna:

| Desde | Hasta | Porcentaje (%) | % Key Sizes |
|---:|---:|---:|---:|
| 35,000 | 299,999 | 3.00 | 4.00 |
| 300,000 | 599,999 | 3.60 | 5.00 |
| 600,000 | 1,199,999 | 4.20 | 6.00 |
| 1,200,000 | 999999999 | 4.80 | 7.00 |

Y abajo, una lista de productos: los **Key Sizes**. Nada más.

No hay que volver a capturar los rangos: los niveles son los mismos, y
la columna nueva solo dice qué cobra ese grupo de productos en cada
nivel.

**Una columna en cero significa "cobran igual que los demás".** Si en el
primer nivel los Key Sizes no tienen trato especial, deje ese renglón en
cero y listo.

## Las tres reglas

1. **Los Key Sizes suman al acumulado.** Participan como cualquier otra
   llanta y ayudan a alcanzar el objetivo. Solo cambia el porcentaje con
   el que se les paga.

2. **El nivel se elige con el acumulado completo**, con los Key Sizes
   incluidos. La columna nueva no interviene en la elección del nivel,
   solo en el pago.

3. **La lista de Key Sizes no agrega productos a la promoción.** Es la
   regla dura del módulo: el universo sale del alcance, la política solo
   puede restringirlo. Un Key Size que el alcance deje fuera no genera
   NC. Por eso el asistente de carga trae marcada la opción *Agregar
   también a los productos participantes*.

## Cómo se calcula

1. Se suman todas las líneas participantes del cliente (o del grupo si
   *Aplican Grupos* está en Sí): ese es el acumulado.
2. Con el acumulado se elige el nivel.
3. Cada línea cobra su porcentaje: el de la columna **% Key Sizes** si
   el producto está en la lista y esa columna no está en cero; el
   general si no.

Ejemplo con la tabla de arriba:

```
Acumulado              684,450.00
Nivel alcanzado    600,000-1,199,999   general 4.20%  | Key Sizes 6.00%

Producto             pza       Subtotal        %   Key            NC
10871003             180     385,400.00     4.20           16,186.80
10492003              95     210,150.00     4.20            8,826.30
185/65R15-B250        60      88,900.00     6.00    sí      5,334.00
----------------------------------------------------------------------
TOTAL                335     684,450.00                    30,347.10

% efectivo del resumen  4.433794 %
```

Sin la línea del Key Size el acumulado habría sido 595,550 y el cliente
se habría quedado en el nivel de 3.60%.

## El porcentaje del resumen es efectivo

Igual que en la política por rin, la columna **% efectivo** del resumen
no es un porcentaje capturado en ningún lado: es NC ÷ subtotal, la
mezcla de porcentajes de ese cliente. Un `4.43 %` es normal.

El importe que manda es `Total NC`, no ese porcentaje. El campo
`reward_percent` se guarda con dos decimales y **solo se muestra**: si
el total se reconstruyera multiplicando subtotal × ese porcentaje, se
perderían pesos en cada cliente. Por eso `_recompute_nc_amounts()` no
toca las promociones con Key Sizes, igual que ya no toca las de rin.

La columna **Detalle del beneficio** desglosa de dónde salió:

```
Acumulado $684,450.00 | Base: 275 pza x 4.20% + Key Sizes: 60 pza x 6.00%
```

## Carga por Excel

Botón **Cargar Key Sizes (.xlsx)** en la pestaña *Definición de la
promoción*. Una sola columna:

| codigo |
|---|
| 10871003 |
| 10492003 |

Los porcentajes no van en el archivo: se capturan una sola vez en la
columna de la tabla de niveles. Si carga la lista sin haber capturado
esa columna, el asistente lo avisa al terminar.

## Limitaciones

- **Un solo grupo de Key Sizes por promoción.** Todos los productos de
  la lista comparten la columna. Si algún día necesita dos familias con
  porcentajes distintos entre sí en el mismo nivel, hace falta otra
  columna (o volver a una tabla aparte); dígalo y se agrega.
- Solo aplican con política por **Cantidad** o por **Monto**. Con
  Volumen Mensual, Cupones o Cantidad Acumulada por Rin se ignoran, y el
  formulario lo avisa.
- Solo aplican con Tipo de Beneficio **Porcentaje**. Un monto fijo por
  nivel no se puede diferenciar por producto.
- El aviso de "Key Size fuera del alcance" solo se puede comprobar con
  certeza cuando el alcance es *Productos / Códigos Específicos*. En los
  alcances por características habría que resolver el dominio contra
  todo el catálogo, y un aviso a medias sería peor que ninguno.
