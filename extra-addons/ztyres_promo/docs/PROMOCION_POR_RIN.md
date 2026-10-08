# Promoción por cantidad acumulada y rin

## Cómo se configura ahora

Son **dos decisiones separadas**:

1. **Alcance de Productos** — qué llantas participan. Para una promoción
   de marcas, elija *Combinación de Características* y marque Marca +
   Rines.
2. **Tipo de Política** — elija *Cantidad Acumulada por Rin* y capture
   la tabla de tramos.

La tabla de rines **no define quién participa**, solo el porcentaje que
cobra cada rin. Si un rin aparece en la tabla pero el alcance no lo
incluye, no genera NC, y el formulario lo avisa arriba en amarillo.

> El alcance *Rines de las Políticas (heredado)* existe para promociones
> viejas: ahí sí participa cualquier llanta con ese rin, **de cualquier
> marca**. Es el comportamiento que producía NC infladas cuando la
> promoción era de marcas específicas.

## Ejemplo: DUNLOP / FALKEN

Alcance — Combinación de Características (AND):

- Marcas: DUNLOP, FALKEN
- Rines: R13, R14, R15, R16, R17, R18, R19, R20, R21, R22, R23, R24, R26,
  R17.50, R19.50, R22.50, R24.50

Política — Cantidad Acumulada por Rin:

| Desde | Hasta | Rines | Porcentaje |
|---:|---:|---|---:|
| 50 | 149 | R13, R14, R15 | 2.00 |
| 50 | 149 | R16 y superiores | 3.00 |
| 150 | 299 | R13, R14, R15 | 3.00 |
| 150 | 299 | R16 y superiores | 4.00 |
| 300 | 999999999 | R13, R14, R15 | 4.00 |
| 300 | 999999999 | R16 y superiores | 5.00 |

Puntos a cuidar:

- **Los rines del alcance y los de la tabla deben coincidir.** Si el
  alcance solo trae R16+, los tramos de R13–R15 nunca aplican.
- **`Hasta` se escribe 999999999**, no 0. En la captura original el
  último renglón tenía `99,999,999` (un dígito menos) y el de arriba
  `999,999,999`: con la validación nueva ambos siguen funcionando, pero
  conviene dejar los dos en `999999999`.
- **No traslape rangos para un mismo rin.** Una validación lo impide:
  si un rin puede cobrar dos porcentajes en el mismo tramo, el resultado
  depende del orden de lectura y no se puede explicar.

## Cómo se calcula

1. Se filtran las líneas facturadas del periodo que cumplen el alcance
   **y** cuyo rin tiene tramo.
2. Se suma la cantidad de todas esas líneas: ese es el **acumulado**
   (por cliente, o por grupo si *Aplican Grupos* está en Sí).
3. Con el acumulado se elige el tramo.
4. Cada línea cobra el porcentaje que su rin tiene en ese tramo.

Ejemplo: 200 pza de R16 por $400,000 y 100 pza de R14 por $100,000.
Acumulado = 300 → tramo alto.

```
R16: 400,000 x 5% = 20,000
R14: 100,000 x 4% =  4,000
NC total          = 24,000
% efectivo        = 24,000 / 500,000 = 4.80 %
```

## Por qué el resumen muestra un porcentaje "raro"

En esta política el porcentaje del resumen es **efectivo**: NC dividida
entre subtotal. Un `4.71 %` no está capturado en ninguna parte, es la
mezcla de rines de ese cliente. La columna **Detalle del beneficio** de
la lista de resultados desglosa el acumulado y el aporte de cada rin,
por ejemplo:

```
Acumulado 1278 pza | R14: 100 pza x 4.00% + R16: 1178 pza x 5.00%
```
