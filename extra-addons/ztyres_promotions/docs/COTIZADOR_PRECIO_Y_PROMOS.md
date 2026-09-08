# Cotizador · orden de precios y panel de promociones (v16.0.4.7.0)

## 1. El orden de los descuentos

El precio que ve el vendedor se arma en este orden, y **ese orden importa**
porque cada paso define la base del siguiente:

```
precio de lista
  − Mayoreo 10%        → PRECIO BASE   (columna "Precio")
  − política comercial   (sobre la base)
  − promociones          (sobre la base)
  = "Pr Promo"
```

Antes, Mayoreo se restaba al final junto con los demás descuentos. Eso
producía dos problemas:

1. La columna Precio mostraba un número que el cliente **nunca pagaba** en
   Bridgestone/Firestone de la lista Mayoreo.
2. La promoción se calculaba sobre esa base inflada. Con lista $1,000 y una
   promo de 7.5%, el sistema descontaba $75 cuando el precio real de partida
   eran $900 y correspondían $67.50.

Ejemplo completo con lista $1,000, Mayoreo, política 6% y promo 7.5%:

| Concepto | Importe |
|---|---:|
| Precio de lista | 1,000.00 |
| Precio base (−10% Mayoreo) | **900.00** |
| Política comercial 6% | −54.00 |
| Promoción 7.5% | −67.50 |
| **Pr Promo** | **778.50** |

El ahorro reportado (13.5%) cuadra exactamente con política + promoción,
porque Mayoreo ya no es un renglón de ahorro: vive dentro del precio base.

Dónde vive esta regla (si cambia una, hay que cambiar la otra):

- Frontend: `basePriceOf()` en `static/src/cotizador_owl/components.js`
- Servidor: `_cotizador_base_price()` en `models/sale_order.py`

**Excepción — base PMS.** Las promociones con precio PMS pactado calculan su
porcentaje sobre ese precio, que es independiente de la lista y de Mayoreo.
No se tocan.

## 2. La tarjeta de regalo NO baja el precio

La tarjeta de regalo es un valor que el cliente **recibe**, no un descuento
sobre la llanta (ver `ztyres_promo/docs/TARJETA_REGALO.md`: con
`gift_card_delivery='none'`, que es el default, ni siquiera emite nota de
crédito). Restarla del precio unitario hacía ver la llanta más barata de lo
que se cobra — el "precio con descuento potencial" salía engañoso.

Por eso:

- Tiene **columna propia** ("Tarjeta") en el catálogo y en ambos Excel.
- `promoUnitDiscount` / `_cotizador_promo_discount` devuelven **0** para
  `reward_type == 'gift_card'`.
- En el ticket del pedido aparece como línea aparte, después del total.
- En el Excel va en un recuadro posterior al total, con la leyenda de que no
  descuenta el precio de las llantas.

**El cupón / apoyo fijo por pieza es otra cosa y sí descuenta.** Tiene tope de
piezas y se refleja en la NC del pedido. Solo se sacó del precio la tarjeta
de regalo.

## 3. Columna K/B retirada

Se quitó del catálogo. El % de Key Size ya viaja dentro del beneficio de la
promoción y el −10% de Mayoreo ya viene aplicado en la columna Precio; marcar
además con una letra obligaba a recalcular mentalmente algo que la aritmética
ya resolvió. El `title` de la columna Precio explica el −10% cuando aplica.

Si se agrega o quita una columna del catálogo hay que actualizar el contador
de `rowStyle()` en `CatalogRow` (hoy 15 fijas + extras), o las bandas de color
de promoción dejan de cubrir la fila completa.

## 4. Panel de promociones · escalera de incentivo

Cada tramo dejó de ser una frase larga y pasó a ser un peldaño con tres
piezas separadas: **rango · regla · beneficio**. La frase completa sigue viva
en el `title`, con la misma redacción que el Excel (`tierLabel` en
`components.js` ↔ `_cotizador_promo_detail` en `sale_order.py`).

Tres detalles de CSS que conviene no repetir por error:

- El bloque de la escalera va **al final** de `cotizador_owl.css`. Arriba hay
  varias capas de parches que redefinen `.facet-head` y `.facet-tier`; una
  regla colocada antes queda pisada por orden de cascada.
- **Pero el orden no basta cuando la especificidad difiere.** Las reglas
  heredadas escritas como `.side-left .promos-panel X` (4 clases) le ganan a
  `.promos-panel X` (3 clases) aunque estén mucho más arriba. Por eso el
  nombre salía con `clamp(11.5px, 0.78vw, 14px)` —14px en monitor grande— y
  se comía tres renglones mientras el peldaño iba a 10px. Todo lo que deba
  ganar ese pulso se repite con las mismas 4 clases al final de la hoja.
- El peldaño es un `<label>` (para que el radio siga siendo accesible), así
  que hereda el `label` global del cotizador, que impone MAYÚSCULAS y 11px.
  Hay que devolverle su tipografía explícitamente.
- La columna izquierda mide `clamp(118px, 8.6vw, 200px)`: en un monitor de
  1600px son ~137px reales. A ese ancho el porcentaje a la derecha deja unos
  40px al rango y las palabras se parten letra por letra. El panel se mide a
  sí mismo con `@container (max-width: 165px)` y baja el porcentaje bajo el
  rango. La consulta mide el **área de contenido**, no el ancho exterior.

### El panel scrollea; no comprime

El panel es `display: flex` en columna, así que sus hijos son items flex y
**por omisión se encogen** (`flex-shrink: 1`). Con varias promociones abiertas
eso no producía scroll sino tarjetas aplastadas: los peldaños se comprimían
unos contra otros y el contenido se recortaba sin barra. `flex: 0 0 auto` en
los hijos directos hace que cada promoción conserve su alto natural, el
contenido desborde y el panel scrollee.

Tampoco hay que poner `overflow: visible` en `.side-left .promos-panel`: una
versión anterior de la hoja ya resolvió el scroll con `max-height: 100%` +
`overflow-y: auto` y el `h2` sticky adentro. Al forzar `visible`, el
`max-height` seguía aplicando desde aquel bloque y el contenido se salía sin
barra — las últimas promociones quedaban inalcanzables.

## 5. Nombre de la promoción en el cotizador

Campo nuevo `cotizador_name` en `ztyres_promo.notas_credito` (etiqueta
"Nombre en el cotizador"). Los nombres administrativos repiten el mismo
prefijo — "08-26 Promoción Volumen Mensual …" son ~30 caracteres iguales
antes de lo único que distingue una promo de otra — y en la columna angosta
no llegaba a verse.

Se serializa como `display_label` y se usa en el panel, los tooltips, el
desglose de ahorros y ambos Excel. **Si se deja vacío cae al nombre completo**
y nada cambia: llenarlo es opcional y se puede hacer promo por promo.
