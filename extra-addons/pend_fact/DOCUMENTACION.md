# Módulo `pend_fact` — Documentación técnica

## Índice
1. [Propósito](#propósito)
2. [Arquitectura](#arquitectura)
3. [Estructura de archivos](#estructura-de-archivos)
4. [Backend — Controlador Python](#backend--controlador-python)
5. [Frontend — Componente OWL](#frontend--componente-owl)
6. [Lógica de negocio](#lógica-de-negocio)
7. [Seguridad](#seguridad)

---

## Propósito

Detecta en tiempo real qué entregas de venta **no han sido facturadas**, comparando
movimientos de stock contra facturas y notas de crédito emitidas. Separa en dos categorías:

| Categoría | Condición | Significado |
|---|---|---|
| **Pendiente facturar** | `entrega_neta > facturado_neto` | Se entregó más de lo facturado |
| **Pendiente NC** | `facturado_neto > entrega_neta` | Se facturó más de lo entregado (devolución sin NC) |

La fórmula central es:
```
Entrega neta   = Σ outgoing - Σ incoming   (stock_move done)
Facturado neto = Σ out_invoice - Σ out_refund  (account_move posted)
Pendiente      = Entrega neta - Facturado neto
```

---

## Arquitectura

```
Browser (OWL)
    │
    │  JSON-RPC  /pend_fact/data
    │  JSON-RPC  /pend_fact/orden
    │  JSON-RPC  /pend_fact/auditoria
    │  JSON-RPC  /pend_fact/nc_lineas
    ▼
Odoo HTTP Controller (Python)
    │
    │  SQL nativo (cr.execute)
    ▼
PostgreSQL
    ├── sale_order / sale_order_line
    ├── stock_move / stock_picking / stock_picking_type
    └── account_move / account_move_line / sale_order_line_invoice_rel
```

Se usa **SQL nativo** en lugar del ORM de Odoo porque la query cruza 5 tablas grandes
con agregaciones condicionales (`FILTER (WHERE ...)`). El ORM generaría N+1 queries
o joins ineficientes para este caso.

---

## Estructura de archivos

```
pend_fact/
├── __manifest__.py               # Declaración del módulo
├── __init__.py                   # Importa controllers
├── controllers/
│   ├── __init__.py
│   └── main.py                   # Endpoints JSON-RPC
├── security/
│   ├── security.xml              # Grupos de acceso
│   └── ir.model.access.csv       # Permisos de modelo
├── views/
│   ├── dashboard_views.xml       # ir.actions.client
│   └── menu.xml                  # Menú principal
└── static/
    ├── description/
    │   ├── icon.png              # Icono 128×128 (App Store de Odoo)
    │   └── index.html            # Página de descripción
    └── src/
        ├── css/dashboard.css     # Estilos del dashboard
        ├── js/dashboard.js       # Componente OWL completo
        └── img/icon.svg          # Icono vectorial para el menú
```

---

## Backend — Controlador Python

### `GET /pend_fact/data` — Datos principales

**Parámetros recibidos:**
```json
{ "year": 2025 }
{ "year": 2025, "month": 6 }
{ "date_from": "2025-01-01", "date_to": "2025-03-31" }
```

**Resolución del rango de fechas:**
```python
if date_from and date_to:        # Rango explícito
    start_date = date_from
    end_date   = date_to
elif year and month:             # Mes completo
    last_day   = calendar.monthrange(year, month)[1]
    start_date = f"{year}-{month:02d}-01"
    end_date   = f"{year}-{month:02d}-{last_day}"
else:                            # Año completo
    start_date = f"{year}-01-01"
    end_date   = f"{year}-12-31"
```

---

#### Query principal de pendientes

Calcula entregado y facturado por cada combinación `(orden, producto)` en un solo
paso usando **dos subqueries independientes** como LEFT JOIN, para evitar el producto
cartesiano que se produciría si se unieran stock y facturas directamente.

**Problema que resuelve:** Si una línea de venta tiene 3 movimientos de stock y
2 líneas de factura, un JOIN directo produciría 6 filas (3×2) y los SUM se
multiplicarían incorrectamente.

**Solución:** Cada fuente (stock, facturas) agrega primero por `sale_line_id`,
produciendo exactamente una fila por línea antes del JOIN exterior.

```sql
SELECT
    so.name                                         AS venta,
    MIN(so.date_order)::date                        AS fecha,
    rp.name                                         AS cliente,
    COALESCE(ru.name, 'Sin vendedor')               AS vendedor,
    COALESCE(pt.name->>'es_MX', pt.name->>'en_US')  AS producto,
    -- SUM porque puede haber múltiples sale_order_line del mismo
    -- producto en la misma orden (dividida en varias líneas)
    SUM(COALESCE(mv.entregado,  0))                 AS entregado,
    SUM(COALESCE(mv.devolucion, 0))                 AS devolucion,
    SUM(COALESCE(inv.facturado, 0))                 AS facturado,
    SUM(COALESCE(inv.nc,        0))                 AS nc
FROM sale_order_line sol
JOIN sale_order       so  ON so.id  = sol.order_id
JOIN res_partner      rp  ON rp.id  = so.partner_id
LEFT JOIN res_users   rsu ON rsu.id = so.user_id
LEFT JOIN res_partner ru  ON ru.id  = rsu.partner_id   -- nombre del vendedor
JOIN product_product  pp  ON pp.id  = sol.product_id
JOIN product_template pt  ON pt.id  = pp.product_tmpl_id

-- Subquery 1: Stock (outgoing=entrega, incoming=devolución)
-- Se agrupa por sale_line_id antes del JOIN para evitar producto cartesiano
LEFT JOIN (
    SELECT
        sm.sale_line_id,
        -- FILTER agrega solo las filas que cumplen la condición,
        -- equivalente a SUM(CASE WHEN ... THEN qty ELSE 0 END)
        SUM(sm.product_uom_qty) FILTER (WHERE spt.code = 'outgoing') AS entregado,
        SUM(sm.product_uom_qty) FILTER (WHERE spt.code = 'incoming') AS devolucion
    FROM stock_move sm
    JOIN stock_picking      sp  ON sp.id  = sm.picking_id
    JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
    WHERE sm.state = 'done'                     -- solo movimientos confirmados
      AND spt.code IN ('outgoing', 'incoming')  -- salidas y devoluciones de cliente
    GROUP BY sm.sale_line_id
) mv ON mv.sale_line_id = sol.id

-- Subquery 2: Facturas y NC
-- display_type = 'product': excluye líneas de sección, nota, flete, etc.
-- pt2.type = 'product': excluye servicios (flete, paquetería, mano de obra)
LEFT JOIN (
    SELECT
        slir.order_line_id,
        SUM(aml.quantity) FILTER (WHERE am.move_type = 'out_invoice') AS facturado,
        SUM(aml.quantity) FILTER (WHERE am.move_type = 'out_refund')  AS nc
    FROM sale_order_line_invoice_rel slir   -- tabla puente venta↔factura
    JOIN account_move_line aml ON aml.id = slir.invoice_line_id
    JOIN account_move       am  ON am.id  = aml.move_id
    JOIN product_product   pp2  ON pp2.id = aml.product_id
    JOIN product_template  pt2  ON pt2.id = pp2.product_tmpl_id
    WHERE am.state     = 'posted'                              -- solo facturas confirmadas
      AND am.move_type IN ('out_invoice', 'out_refund')
      AND (aml.display_type = 'product' OR aml.display_type IS NULL)
      AND pt2.type = 'product'                                 -- solo productos almacenables
    GROUP BY slir.order_line_id
) inv ON inv.order_line_id = sol.id

WHERE so.date_order >= %(start)s
  AND so.date_order <= %(end)s

-- GROUP BY: agrupa múltiples sol del mismo producto en la misma orden
-- pp.product_tmpl_id distingue variantes del mismo producto
GROUP BY
    so.name, rp.name, ru.name,
    COALESCE(pt.name->>'es_MX', pt.name->>'en_US'),
    pp.product_tmpl_id
```

**Clasificación Python post-query:**
```python
for r in rows_raw:
    entrega_neta   = entregado - devolucion
    facturado_neto = facturado - nc
    diferencia     = entrega_neta - facturado_neto

    if diferencia > 0.001:      # margen para evitar errores de punto flotante
        → rows_fact (pendiente de facturar)
    elif diferencia < -0.001:
        → rows_nc   (devolución sin nota de crédito)
    # si abs(diferencia) <= 0.001 → cuadrado, se ignora
```

---

#### Query NC no ligadas

Detecta notas de crédito que **no tienen ninguna línea vinculada** a una
`sale_order_line` mediante `sale_order_line_invoice_rel`. Esto ocurre cuando la NC
se crea manualmente desde contabilidad en lugar de generarse desde la orden de venta.

```sql
SELECT
    am.id, am.name, am.invoice_date, rp.name AS cliente,
    pt.name->>'es_MX' AS producto,
    aml.quantity, aml.price_unit, aml.price_subtotal
FROM account_move am
JOIN res_partner rp ON rp.id = am.partner_id
JOIN account_move_line aml ON aml.move_id = am.id
JOIN product_product  pp ON pp.id  = aml.product_id
JOIN product_template pt ON pt.id  = pp.product_tmpl_id
WHERE am.move_type    = 'out_refund'
  AND am.state        = 'posted'
  AND am.invoice_date >= %(start)s
  AND am.invoice_date <= %(end)s
  AND aml.display_type = 'product'
  AND pt.type          = 'product'
  -- Subconsulta de existencia: la NC no tiene ninguna línea
  -- registrada en la tabla puente venta↔factura
  AND NOT EXISTS (
    SELECT 1
    FROM account_move_line aml2
    JOIN sale_order_line_invoice_rel slir2 ON slir2.invoice_line_id = aml2.id
    WHERE aml2.move_id = am.id
  )
ORDER BY am.id, am.name, aml.id
```

**Agrupación Python:** Las filas se agrupan por `move_id` en un `OrderedDict`
para construir una lista de NCs con sus líneas de producto anidadas.

---

### `GET /pend_fact/orden` — Análisis de pedido

Permite analizar cualquier orden aunque no aparezca en la lista de pendientes.
Reutiliza los mismos subqueries de stock y facturas pero filtrado por `so.name`
en lugar de rango de fechas. Agrega además `STRING_AGG` para mostrar los nombres
de facturas y NC vinculadas a cada línea.

---

### `GET /pend_fact/auditoria` — Auditoría por (venta, producto)

Devuelve el detalle **movimiento a movimiento** de stock y **documento a documento**
de facturación para verificar que los totales cuadran. Útil para detectar registros
duplicados o mal vinculados.

Calcula `cantidad_neta` con `CASE`:
```sql
CASE spt.code
    WHEN 'outgoing' THEN  sm.product_uom_qty   -- salida: positivo
    WHEN 'incoming' THEN -sm.product_uom_qty   -- devolución: negativo
    ELSE 0
END AS cantidad_neta
```

Responde con `cuadra: true/false` comparando totales de stock vs facturas
con margen de `0.01` para errores de punto flotante.

---

### `GET /pend_fact/nc_lineas` — Líneas de NC on-demand

Carga las líneas de producto de una NC suelta solo cuando el usuario la expande
en el panel. Evita traer todas las líneas de todas las NCs en la carga inicial.

---

## Frontend — Componente OWL

### Stack tecnológico

- **OWL 2** (Odoo Web Library) — framework reactivo de Odoo 16
- **Template inline** con `xml\`` — evita dependencia de archivos XML externos
  que pueden fallar si el bundler no los procesa antes que el JS
- **`useState`** — reactividad: cualquier cambio en `state` re-renderiza el componente
- **`useService("rpc")`** — cliente JSON-RPC integrado de Odoo

### Estado reactivo (`state`)

```javascript
state = useState({
    // Filtros de fecha
    mode: 'range',          // 'year' | 'month' | 'range'
    year, month,            // para modos year y month
    dateFrom, dateTo,       // para modo range (default: hoy)

    // Datos
    rows: [],               // pendientes de facturar
    rowsNc: [],             // pendientes de NC
    filtered: [],           // rows filtrados por búsqueda/vendedor
    filteredNc: [],

    // KPIs
    totalPend, totalPendNc,
    totalOrdenes, totalOrdenesNc,
    totalLineas, totalLineasNc,

    // NC sueltas
    ncSueltas: [],          // lista de NCs no ligadas
    showNcPanel: false,
    ncExpandKey: null,      // move_id de la NC expandida actualmente

    // Auditoría
    auditKey: null,         // id de fila con panel abierto
    auditData: null,        // respuesta del endpoint auditoria
    auditLoading: false,

    // Análisis de pedido
    ordenBusqueda: '',
    ordenData: null,
    ordenError: '',

    // Timer
    countdown: 30,          // segundos para próxima actualización
    paused: false,          // si el usuario pausó manualmente
    autoRefresh: true,      // false cuando se aplica filtro manual
})
```

### Lógica del timer y modo auto/manual

El auto-refresco funciona solo cuando el filtro activo es exactamente "hoy":

```javascript
_isToday() {
    const today = new Date().toISOString().slice(0, 10);
    return this.state.mode === 'range'
        && this.state.dateFrom === today
        && this.state.dateTo   === today;
}
```

Cualquier cambio de filtro llama a `_setManual()`:
```javascript
_setManual() {
    this.state.autoRefresh = false;  // desactiva timer
    this._clearTimer();               // cancela el interval activo
}
```

`_startCountdown()` verifica `autoRefresh` antes de arrancar:
```javascript
_startCountdown() {
    if (!this.state.autoRefresh) return;  // no arrancar en modo manual
    this.state.countdown = 30;
    this._timer = setInterval(() => {
        if (this.state.paused) return;    // skip si está pausado
        this.state.countdown--;
        if (this.state.countdown <= 0) {
            this._clearTimer();
            this.loadData();              // recarga completa
        }
    }, 1000);
}
```

El botón "Volver a hoy" restablece el modo auto:
```javascript
resetToToday() {
    const today = new Date().toISOString().slice(0, 10);
    this.state.mode        = 'range';
    this.state.dateFrom    = today;
    this.state.dateTo      = today;
    this.state.autoRefresh = true;
    this.state.paused      = false;
    this.loadData();
}
```

### Manejo de eventos en OWL — `ev.currentTarget`

Los botones que reciben datos usan atributos `data-*` en lugar de arrow functions
en el template, porque en OWL los arrow functions en `t-on-click` pierden el
contexto de `this`:

```xml
<!-- INCORRECTO — this es undefined -->
<button t-on-click="() => auditar(row.venta, row.id)">Ver</button>

<!-- CORRECTO — datos via data attributes, leídos con ev.currentTarget -->
<button t-on-click="onAuditar"
    t-att-data-venta="row.venta"
    t-att-data-id="row.id">Ver</button>
```

```javascript
async onAuditar(ev) {
    // ev.currentTarget siempre apunta al elemento con t-on-click,
    // incluso si el click fue en un hijo (texto, icono)
    const btn     = ev.currentTarget;
    const venta   = btn.getAttribute('data-venta');
    const id      = Number(btn.getAttribute('data-id'));
    ...
}
```

### Filtrado client-side vs server-side

La búsqueda por texto y el filtro por vendedor se aplican **en el cliente** sobre
`state.rows` ya cargados, sin nueva llamada al servidor:

```javascript
_applyFilter() {
    const q = this.state.searchText.toLowerCase();
    const v = this.state.vendedorFil;
    const match = r => {
        const matchQ = !q || [r.venta, r.cliente, r.producto]
            .some(s => s.toLowerCase().includes(q));
        const matchV = !v || r.vendedor === v;
        return matchQ && matchV;
    };
    this.state.filtered   = this.state.rows.filter(match);
    this.state.filteredNc = this.state.rowsNc.filter(match);
}
```

Esto funciona porque el número de filas pendientes es normalmente pequeño
(decenas, no miles). Si en algún periodo hubiera cientos de pendientes,
el filtrado server-side sería más apropiado.

---

## Lógica de negocio

### ¿Por qué dos subqueries en lugar de un JOIN directo?

**Escenario:** Una orden tiene 3 movimientos de stock (salida, devolución, re-entrega)
y 2 facturas. Un JOIN directo produciría 3×2=6 filas y los SUM se multiplicarían:

```
stock_move × account_move_line = producto cartesiano
outgoing=100, incoming=50, outgoing=50 × factura=100, nc=50
→ 6 filas donde cada qty aparece 2 veces = totales duplicados
```

Con subqueries independientes:
```
mv: sale_line_id=X → entregado=150, devolucion=50  (una fila)
inv: order_line_id=X → facturado=100, nc=50        (una fila)
JOIN → una fila con datos correctos
```

### ¿Por qué `display_type = 'product' OR display_type IS NULL`?

En Odoo 16 las líneas de factura tienen varios tipos:
- `'product'` — línea de producto normal
- `'line_section'` — cabecera de sección
- `'line_note'` — nota
- `NULL` / `False` — en algunas versiones las líneas de producto tienen `NULL`

El filtro captura ambos casos para no perder líneas según la versión de Odoo.

### ¿Por qué filtrar `pt.type = 'product'`?

Los servicios (flete, paquetería, instalación) tienen `product_template.type = 'service'`.
Estos aparecen en las facturas pero **no generan movimientos de stock**. Si se
incluyen, el cálculo siempre mostraría pendiente porque `entregado=0` pero `facturado>0`.

### Margen de tolerancia `0.001`

```python
if diferencia > 0.001:    # y no > 0
```

Las cantidades de productos pueden tener decimales (ej: 1.5 kg). Las operaciones
de punto flotante acumulan errores del orden de `1e-10`. El margen de `0.001`
evita falsos positivos donde la diferencia real es cero pero Python calcula
`0.000000000001`.

---

## Seguridad

### Grupos

Definidos en `security/security.xml`:

| Grupo | XML ID | Descripción |
|---|---|---|
| Usuario | `pend_fact.group_pend_fact_user` | Acceso de lectura al dashboard |
| Manager | `pend_fact.group_pend_fact_manager` | Incluye Usuario; asignado a admin por defecto |

Los menús están restringidos a `group_pend_fact_user`. Para dar acceso a un
usuario: **Ajustes → Usuarios → editar → pestaña "Permisos de acceso" →
sección "Facturación Pendiente"**.

### Autenticación de endpoints

Todos los endpoints usan `auth='user'`, lo que significa que Odoo verifica
la sesión activa antes de ejecutar el controlador. No se puede llamar a
`/pend_fact/data` sin estar autenticado.
