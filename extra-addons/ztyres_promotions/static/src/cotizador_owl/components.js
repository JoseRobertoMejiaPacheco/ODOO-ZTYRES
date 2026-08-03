/** @odoo-module **/
/* ============================================================
   Cotizador Owl · Ztyres — Componentes
   ============================================================ */
import { Component, useState, useRef, onMounted, onPatched, onWillUnmount, xml } from "@odoo/owl";

import { IconPlus, IconMinus, IconTrash } from './icons.js';
import {
  EXTRA_COLUMNS, SF_FIELDS, PROFILE_FIELDS, PROFILE_OPTIONS, money, formatDot, formatColumnValue, normalizeSearchText, setPromoSim, policyFactor, policyLabel, IVA_RATE, setShowIva, promoColorFor,
} from './constants.js';
import { productImageUrl } from './api.js';

/* Beneficio potencial por producto. En políticas por rin el porcentaje
   depende del product_id. Un monto fijo pertenece a la NC completa y no
   se convierte artificialmente en descuento unitario. */
function promoPercentForProduct(promo, tier, productId) {
  if (!tier || promo.reward_type === 'fixed_amount') return 0;
  if (tier.product_discounts) {
    return Number(tier.product_discounts[String(productId)] || 0);
  }
  /* Key Size: en este nivel cobra su propia columna. Misma regla que
     _cotizador_promo_discount en sale_order.py — si cambia una, cambia
     la otra o el XLSX deja de cuadrar con la pantalla. */
  if (Number(tier.key_size_discount || 0) > 0
      && (promo.key_size_product_ids || []).includes(Number(productId))) {
    return Number(tier.key_size_discount);
  }
  return Number(tier.discount || 0);
}

function promoUnitDiscount(promo, tier, product, listPrice) {
  if (!product || !(promo.product_ids || []).includes(Number(product.product_id))) return 0;
  if (promo.promo_type === 'coupons') {
    const coupon = (promo.coupons || []).find(
      (item) => item.tmpl_id === product.tmpl_id,
    );
    return coupon ? Number(coupon.amount || 0) : 0;
  }
  return Number(listPrice || 0)
    * promoPercentForProduct(promo, tier, product.product_id) / 100;
}

function selectedTierForPromo(state, promo, selected) {
  if (!selected || !selected.on) return null;
  if (selected.tier == null) return null;
  return (promo.tiers || [])[selected.tier] || null;
}


/* ---------- Imagen de producto (con zoom) ---------- */

/* ---------- Tabla plana del catálogo (estilo hoja de cálculo) ----------
   Ya no se agrupa por medida (antes era un <details> colapsable por
   cada medida) — todo el catálogo filtrado se ve de una sola vez, en
   una sola tabla. Clave y Medida son columnas propias (antes iban
   pegadas al nombre completo del producto). Las columnas de atributos
   (Segmento, Tipo, Modelo, etc.) siguen aquí igual que antes — solo se
   quitaron del catálogo las 10 que pidió el cliente (Fabricante, Uso,
   Peso, Seg. proveedor, S-Mark, E-Mark, CCC, HQ, Profundidad,
   Nacionalidad); el resto se sigue mostrando/ocultando con el selector
   de columnas (ver ColumnsPicker) igual que antes. */
/* ---------- Selector de IVA (solo visualización) ----------
   Todo el sistema trabaja SIN IVA: catálogo, quote, promociones y NC
   se calculan y guardan en base. Este control únicamente cambia CÓMO
   se pintan los montos en pantalla/PDF (×1.16 cuando está en "Con
   IVA") — jamás altera lo que se manda o se recibe del servidor. */
export class IvaToggle extends Component {
  static template = xml`
    <div class="iva-toggle" title="Solo cambia cómo se muestran los precios. Todo el sistema calcula y guarda sin IVA.">
      <button type="button" t-att-class="{ active: !props.state.showIva }"
              t-on-click="() => this.set(false)">Sin IVA</button>
      <button type="button" t-att-class="{ active: props.state.showIva }"
              t-on-click="() => this.set(true)">Con IVA</button>
    </div>`;

  set = (on) => {
    this.props.state.showIva = on;
    setShowIva(on);
  };
}

/* ---------- Fila del catálogo (componente propio) ----------
   Cada <tr> es un componente: recibe por props el producto, la
   cantidad en carrito y la entrada de promo YA resuelta (lookup O(1)
   hecho por el padre) — la fila no calcula nada, solo pinta. Junto
   con la ventana de filas del padre (renderLimit), esto elimina el
   "pantallazo fantasma": nunca se montan miles de nodos de golpe. */
export class CatalogRow extends Component {
  static template = xml`
    <tr t-att-class="{ 'in-cart': props.qty > 0, 'in-promo': !!props.color }"
        t-att-style="rowStyle()">
      <td class="flat-td-clave" data-label="Código" t-att-title="props.product.code || ''" t-esc="props.product.code || '—'"/>
      <td class="flat-td-tier" data-label="Tier">
        <span t-if="props.product.tier" class="tier-badge" t-att-title="props.product.tier"
              t-attf-style="background:{{tierColor()}};color:{{tierTextColor()}}" t-esc="tierShort()"/>
        <t t-else="">—</t>
      </td>
      <td class="flat-td-medida" data-label="Medida" t-esc="props.product.medida"/>
      <td class="flat-td-marca" data-label="Marca" t-att-title="props.product.brand || ''" t-esc="props.product.brand || '—'"/>
      <td class="flat-td-modelo" data-label="Modelo" t-att-title="props.product.model || ''" t-esc="props.product.model || '—'"/>
      <td class="flat-td-capcara" data-label="Cap/Cara" t-att-title="'Capas: ' + (props.product.layer || '—') + ' · Cara: ' + (props.product.face || '—')" t-esc="capCara()"/>
      <td class="flat-td-velind" data-label="Vel/Ind" t-att-title="'Velocidad: ' + (props.product.speed || '—') + ' · Índice de carga: ' + (props.product.index_of_load || '—')" t-esc="velInd()"/>
      <td class="flat-td-seg" data-label="Seg" t-esc="props.product.segment || '—'"/>
      <td class="flat-td-tipo" data-label="Tipo" t-esc="props.product.type || '—'"/>
      <td class="flat-td-dot" data-label="DOT" t-att-title="props.product.dot_range" t-esc="formatDot(props.product.dot_range)"/>
      <td class="flat-td-eqorig" data-label="Eq. Original" t-att-title="props.product.original_equipment || ''" t-esc="props.product.original_equipment || '—'"/>
      <td class="flat-td-attr" t-foreach="props.extraColumns" t-as="col" t-key="col.key" t-att-data-label="col.label"
          t-esc="formatColumnValue(col.key, props.product[col.key])"/>
      <td class="flat-td-disp" data-label="Inv" t-esc="props.product.free_qty != null ? props.product.free_qty : '—'"/>
      <td class="flat-td-price" data-label="Precio"
          t-att-class="{ 'has-promo': !!finalPrice() }" t-esc="money((props.product.price || 0) * props.iva)"/>
      <td class="flat-td-promo" data-label="Pr Promo" t-att-title="finalTitle()">
        <span t-if="finalPrice()" class="promo-price" t-esc="money(finalPrice() * props.iva)"/>
        <span t-else="" class="promo-empty" t-att-title="props.qty ? 'Sin promoción ni descuento aplicable' : 'Agrega al pedido o elige una promo/política para simular'">—</span>
      </td>
      <td class="flat-td-action">
        <button t-if="!props.qty" class="add-btn" t-on-click="() => props.onAdd(props.product.product_id)">
          <IconPlus/> Agregar
        </button>
        <div t-else="" class="qty-stepper">
          <button class="step-btn" t-on-click="() => props.onDec(props.product.product_id)"><IconMinus/></button>
          <input type="number" min="1" class="step-input" t-att-value="props.qty"
                 t-on-change="(ev) => props.onSetQty(props.product.product_id, ev.target.value)"
                 t-on-keydown="(ev) => ev.key === 'Enter' and ev.target.blur()"/>
          <button class="step-btn" t-on-click="() => props.onInc(props.product.product_id)"><IconPlus/></button>
        </div>
      </td>
    </tr>`;
  static components = { IconPlus, IconMinus };

  money = money;
  formatDot = formatDot;
  formatColumnValue = formatColumnValue;

  /* Estilo de la fila teñida por promo(s):
     - Si aplica UNA sola: fondo tintado uniforme (más limpio visualmente).
     - Si aplican VARIAS: bandas verticales iguales de sus tintes con
       transiciones suaves (conic-gradient rectilíneo). El borde
       izquierdo suma UN pixel por promo, para que ni siquiera en
       pantallas pequeñas se pierda la señal.
     Marca / Modelo / Pr Promo toman el color de la promo ganadora
     (la que EFECTIVAMENTE está pintando el precio en Pr Promo). */
  rowStyle() {
    /* Construye las variables CSS de color de la fila. Con UNA sola
       promo, --promo-t plano basta y cada celda lo hereda tal cual.
       Con VARIAS promos, además setea --tint-1..--tint-N con el
       tinte que corresponde a cada COLUMNA visible: cada promo se
       lleva un tramo IGUAL de columnas (16 columnas fijas + extras),
       y el CSS con nth-child dice qué tinte usa cada <td>. Como el
       tinte va a nivel de celda, table-layout:fixed sigue mandando
       los anchos y todo queda alineado con el thead. */
    const c = this.props.color;
    if (!c) return '';
    const winner = c.winner || c.palette[0];
    let vars = `--promo-c: ${winner.text}; --promo-b: ${winner.border}; --promo-t: ${winner.tint};`;
    if (c.palette.length > 1) {
      const cols = 15 + (this.props.extraColumns ? this.props.extraColumns.length : 0);
      const n = c.palette.length;
      // Reparte columnas en bloques del MISMO tamaño posible;
      // sobrantes van a las primeras promos (bloques de tamaño ceil).
      const sizes = Array.from({length: n}, (_, i) =>
        Math.floor(cols / n) + (i < cols % n ? 1 : 0));
      let col = 1;
      for (let i = 0; i < n; i++) {
        const tint = c.palette[i].tint;
        for (let k = 0; k < sizes[i]; k++) {
          vars += ` --td-tint-${col}: ${tint};`;
          col++;
        }
      }
    }
    return vars;
  }

  capCara() {
    const p = this.props.product;
    return [p.layer, p.face].filter(Boolean).join('-') || '—';
  }
  velInd() {
    const p = this.props.product;
    return [p.speed, p.index_of_load].filter(Boolean).join('') || '—';
  }
  tierNum() {
    const m = String(this.props.product.tier || '').match(/\d+/);
    return m ? parseInt(m[0], 10) : 0;
  }
  tierShort() {
    return this.tierNum() || (this.props.product.tier || '—');
  }
  tierColor() {
    const n = this.tierNum();
    return n === 1 ? '#facc15' : n === 2 ? '#38bdf8' : n === 3 ? '#94a3b8' : n === 4 ? '#ef4444' : 'var(--card)';
  }
  tierTextColor() {
    const n = this.tierNum();
    return n === 1 || n === 3 ? '#000' : n === 2 || n === 4 ? '#fff' : 'var(--ink)';
  }

  /* Precio final de Pr Promo = política comercial (props.factor, en
     cascada sobre lista) + promo real/simulada (props.promo, ya
     resuelta por el padre; su price viene calculado SOBRE el precio
     con política — ver _promoMaps). Si solo hay política, se muestra
     lista×factor. */
  finalPrice() {
    if (this.props.promo) return this.props.promo.price;
    if (this.props.factor < 0.9999) return (this.props.product.price || 0) * this.props.factor;
    return 0;
  }
  finalTitle() {
    if (this.props.promo) return this.props.promo.label;
    if (this.props.factor < 0.9999) return 'Política comercial: ' + this.props.policyText;
    return '';
  }
}

export class CatalogTable extends Component {
  static template = xml`
    <div class="flat-empty-state" t-if="!rows.length">
      <span class="empty-state-icon">🔍</span>
      <p class="empty-state-title">Sin productos que coincidan</p>
      <p class="empty-state-hint">Prueba quitando algún filtro o ajustando la búsqueda.</p>
    </div>
    <table class="flat-table" t-else="">
      <thead>
        <tr>
          <th class="flat-th-clave">Código</th>
          <th class="flat-th-tier">Tier</th>
          <th class="flat-th-medida">Medida</th>
          <th class="flat-th-marca">Marca</th>
          <th class="flat-th-modelo">Modelo</th>
          <th class="flat-th-capcara" title="Capas / Cara">Cap/Cara</th>
          <th class="flat-th-velind" title="Velocidad / Índice de carga">Vel/Ind</th>
          <th class="flat-th-seg">Seg</th>
          <th class="flat-th-tipo">Tipo</th>
          <th class="flat-th-dot">DOT</th>
          <th class="flat-th-eqorig" title="Equipo original">Eq. Orig.</th>
          <th t-foreach="extraColumns" t-as="col" t-key="col.key" t-att-title="col.label" t-esc="col.short || col.label"/>
          <th class="flat-th-disp">Inv</th>
          <th class="flat-th-price">Precio</th>
          <th class="flat-th-promo" title="Precio efectivo por pieza considerando la promoción vigente (NC estimada del pedido actual)">Pr Promo</th>
          <th class="flat-th-action">Agregar</th>
        </tr>
      </thead>
      <tbody>
        <CatalogRow t-foreach="rows" t-as="product" t-key="product.product_id"
                    product="product"
                    qty="props.state.cart[product.product_id] or 0"
                    promo="promoEntry(product)"
                    color="colorFor(product)"
                    factor="factor"
                    iva="iva"
                    policyText="policyText"
                    extraColumns="extraColumns"
                    onAdd="props.onAdd" onInc="props.onInc" onDec="props.onDec" onSetQty="props.onSetQty"/>
      </tbody>
    </table>
    <div class="load-more" t-if="hiddenCount > 0" t-ref="loadMoreBar">
      <span class="load-more-info">
        Mostrando <t t-esc="rows.length"/> de <t t-esc="totalRows"/> llantas · se cargan más al hacer scroll
      </span>
      <button type="button" class="btn-sec" t-on-click.stop="() => this.loadMore(300)">Cargar 300 más</button>
      <button type="button" class="btn-sec" t-on-click.stop="() => this.loadMore(999999)">Mostrar todas</button>
    </div>`;
  static components = { CatalogRow };

  get extraColumns() {
    return EXTRA_COLUMNS.filter((c) => this.props.state.visibleColumns.includes(c.key));
  }


  /* Pr Promo tiene DOS fuentes, en este orden: (1) REAL — NC ya
     calculada por el motor para lo que está en el carrito; (2)
     SIMULADO — el rango elegido en las facetas, aplicado a las
     llantas que cumplen esa promo.

     RENDIMIENTO: nada de esto se calcula por celda. Se precalculan
     DOS mapas producto→precio una sola vez por cambio real (de
     promos seleccionadas, del quote o del catálogo) y cada fila hace
     un lookup O(1). Antes se recorrían promos y líneas del quote en
     cada celda de cada fila — con miles de filas, ese era el lag al
     palomear una promo o teclear en el buscador. */
  get _promoMaps() {
    const st = this.props.state;
    // Huella DETERMINISTA de las promos activas: ids ordenados +
    // el tramo elegido. Si la promo no está activa no entra, así que
    // re-activarla siempre cambia la huella y fuerza recálculo.
    const simKeys = Object.keys(st.promoSim).filter((k) => st.promoSim[k] && st.promoSim[k].on).sort();
    const cartStamp = Object.entries(st.cart || {})
      .sort(([a], [b]) => Number(a) - Number(b))
      .map(([id, qty]) => `${id}:${qty}`).join(',');
    const stamp = simKeys.map((k) => k + ':' + (st.promoSim[k].tier || 0)).join(',')
      + '|' + policyFactor(st.profile) + '|' + cartStamp;
    const c = this._pmCache;
    if (c && c.promos === st.promos && c.catalog === st.catalog
        && c.quote === st.quote && c.stamp === stamp) {
      return c.maps;
    }

    // Índice del catálogo (id → producto), cacheado por identidad.
    if (!this._byId || this._byIdSrc !== st.catalog) {
      this._byIdSrc = st.catalog;
      this._byId = new Map(st.catalog.map((p) => [p.product_id, p]));
    }

    // (1) Mapa REAL: pocas entradas (solo líneas del carrito con NC).
    const real = new Map();
    const quote = st.quote;
    if (quote && quote.promo_ganada && quote.promo_ganada.per_product) {
      for (const [pidStr, nc] of Object.entries(quote.promo_ganada.per_product)) {
        const qty = st.cart[pidStr] || 0;
        if (!(nc > 0) || !qty) continue;
        const line = quote.lines.find((l) => String(l.product_id) === pidStr);
        const prod = this._byId.get(parseInt(pidStr, 10));
        const lista = line ? line.unit_price : (prod ? prod.price : 0);
        // SIN cascada: la política y la NC se calculan CADA UNA sobre
        // el precio de lista y se restan juntas.
        const policyDisc = lista * (1 - policyFactor(st.profile));
        const eff = Math.max(lista - policyDisc - nc / qty, 0);
        if (eff < lista - 0.005) {
          real.set(parseInt(pidStr, 10), {
            price: eff,
            label: 'Precio efectivo real: lista − política comercial − NC de este pedido (cada descuento sobre lista)',
          });
        }
      }
    }

    /* (2) Mapa SIMULADO — ACUMULATIVO
       ================================================================
       Reproduce EXACTAMENTE la matemática del motor real de
       ztyres_promo (ver ztyres_promo_notas_credito_eval.py línea 207
       y ztyres_promo_notas_credito_lines.py:_get_discount_percent):
       cada promoción se evalúa por separado y sus ganancias se SUMAN
       al final. Es lo que hace el motor cuando emite la NC: suma la
       "ganado" de la Promo A + la "ganado" de la Promo B, no elige
       "la mejor". Dentro de UNA SOLA promo con varios tramos, el
       motor toma el máximo `discount` de los que cumplen `qty`
       (línea 32 del mismo archivo) — en el simulador cada promo tiene
       UN tramo activo (el radio elegido por el vendedor), así que la
       elección del tramo es explícita.

       Por cada llanta se acumula:
         - policyDisc = lista × (política %)     — una sola vez
         - promoDiscTotal = Σ (lista × promo_i %)  para cada promo i
           activa que aplique a la llanta (o Σ cupón_i para promos
           de tipo 'coupons').
         - final = max(lista − policyDisc − promoDiscTotal, 0)
       TODO sobre lista (sin cascada), como el usuario pidió antes.

       Ejemplo con lista $1,000, política 6%, Promo A 5%, Promo B 13%:
         final = 1000 − 60 − 50 − 130 = $760   (18% total de promos)
       Antes se mostraba solo el mejor precio individual (Promo B):
         final = 1000 − 60 − 130 = $810   ← incorrecto, ignoraba A. */
    const sim = new Map();
    const policyPctOff = 1 - policyFactor(st.profile);
    const policyTxt = policyLabel(st.profile);
    const accum = new Map(); // pid → { discSum, parts:[{promo,tint,text,border,pct,coupon}] }
    for (const pr of st.promos) {
      const sel = st.promoSim[pr.id];
      if (!sel || !sel.on) continue;
      const tier = selectedTierForPromo(st, pr, sel);
      const color = promoColorFor(pr.id);
      for (const pid of pr.product_ids) {
        const prod = this._byId.get(pid);
        if (!prod) continue;
        const lista = prod.price || 0;
        const disc = promoUnitDiscount(pr, tier, prod, lista);
        let partLabel = '';
        if (pr.promo_type === 'coupons' && disc > 0) {
          partLabel = `${pr.name} apoyo $${disc}`;
        } else {
          const pct = promoPercentForProduct(pr, tier, pid);
          if (pct > 0) partLabel = `${pr.name} ${pct}%`;
        }
        if (disc <= 0) continue;
        const bucket = accum.get(pid) || { discSum: 0, parts: [] };
        bucket.discSum += disc;
        bucket.parts.push({ promoId: pr.id, color, disc, label: partLabel });
        accum.set(pid, bucket);
      }
    }

    // Consolidar accum → sim (con el descuento total de política + promos)
    for (const [pid, bucket] of accum) {
      const prod = this._byId.get(pid);
      const lista = prod.price || 0;
      const policyDisc = lista * policyPctOff;
      const final = Math.max(lista - policyDisc - bucket.discSum, 0);
      if (!(final < lista - 0.005)) continue;
      const partsTxt = bucket.parts.map((p) => p.label).join(' + ');
      const polTxt = policyTxt ? ` + Política ${policyTxt}` : '';
      sim.set(pid, {
        price: final,
        label: `Simulado · ${partsTxt}${polTxt} — cada descuento sobre lista`,
        parts: bucket.parts,
      });
    }

    /* Colores por producto: bandas por CADA promo que aportó al
       descuento total (no solo la "ganadora" — ya no la hay porque
       todas contribuyen). El winner del texto se elige por MAYOR
       aporte al descuento, no por mejor precio individual. */
    const colors = new Map();
    for (const [pid, entry] of sim) {
      const parts = entry.parts;
      const palette = parts.map((p) => p.color);
      const winner = parts.reduce((a, b) => (a.disc >= b.disc ? a : b)).color;
      colors.set(pid, { winner, palette });
    }
    // Al activar una promoción se identifican todos sus productos,
    // aunque el pedido aún no alcance un tramo. El precio solo cambia
    // cuando selectedTierForPromo encuentra un rango válido.
    for (const pr of st.promos) {
      const sel = st.promoSim[pr.id];
      if (!sel || !sel.on) continue;
      const color = promoColorFor(pr.id);
      for (const pid of pr.product_ids || []) {
        const current = colors.get(pid);
        if (!current) {
          colors.set(pid, { winner: color, palette: [color] });
        } else if (!current.palette.some((item) => item.text === color.text)) {
          current.palette.push(color);
        }
      }
    }
    const maps = { real, sim, colors };
    this._pmCache = { promos: st.promos, catalog: st.catalog, quote: st.quote, stamp, maps };
    return maps;
  }
  colorFor(product) {
    return this._promoMaps.colors.get(product.product_id) || null;
  }
  promoEntry(product) {
    const maps = this._promoMaps;
    return maps.real.get(product.product_id) || maps.sim.get(product.product_id) || null;
  }
  // Factor y etiqueta de la Política comercial (cambian solo cuando
  // el vendedor mueve los % del cliente) — se pasan a cada fila.
  get factor() {
    return policyFactor(this.props.state.profile);
  }
  get policyText() {
    return policyLabel(this.props.state.profile);
  }
  // Factor de IVA para PINTAR (1 o 1.16) — nunca entra a los mapas
  // de promo ni a nada que viaje al servidor.
  get iva() {
    return this.props.state.showIva ? 1 + IVA_RATE : 1;
  }

  /* Ventana de filas: nunca se montan miles de <tr> de golpe (eso
     era el "pantallazo fantasma"). Arrancan 150; "Cargar 300 más" o
     "Mostrar todas" amplían; al cambiar búsqueda/filtros la ventana
     se reinicia sola (el stamp del cache de rows cambia). */
  loadMore(n) {
    const total = this._allRows().length;
    const next = Math.min(this.state.renderLimit + n, total);
    if (next !== this.state.renderLimit) this.state.renderLimit = next;
  }
  get totalRows() {
    return this._allRows().length;
  }
  get hiddenCount() {
    return Math.max(this.totalRows - this.rows.length, 0);
  }


  get filtered() {
    const state = this.props.state;
    const q = state.search.trim().toLowerCase();
    const qNorm = normalizeSearchText(q);
    return state.catalog.filter((p) => {
      const text = `${p.code} ${p.brand} ${p.name} ${p.medida} R${p.rim}`.toLowerCase();
      // Match normal (substring tal cual) O match "esqueleto" (sin
      // separadores, sin la R pegada al rin) — así "195/65 R15",
      // "195-65-15" y "195 65 15" encuentran la misma llanta sin
      // importar qué separador haya usado quien escribió.
      const matchesQ = !q || text.includes(q) || normalizeSearchText(text).includes(qNorm);
      const matchesSF = Object.entries(state.sfFilters).every(([field, vals]) => {
        if (!vals || !vals.length) return true;
        const v = p[field];
        return vals.includes(String(v || ''));
      });
      return matchesQ && matchesSF;
    });
  }

  // Lista plana ordenada por medida/rin y luego por clave — reemplaza
  // el agrupamiento por medida de antes: ya no hay <details> que
  // abrir, todo el catálogo filtrado se ve de una sola vez.
  setup() {
    /* renderLimit vive en state Y se LEE en cada render (en el
       getter rows), que es como Owl 2 sabe que debe re-renderizar
       al cambiarlo. Antes teníamos un renderTick que nadie leía —
       Owl trackea reads durante render; sin read, la mutación es
       invisible y los botones "no hacían nada". */
    this.state = useState({ renderLimit: 150 });
    this._lastFilterStamp = null;

    /* Scroll infinito con IntersectionObserver — el ROOT es el
       contenedor que sí scrollea (.table-scroll del SPA). Con root
       null (viewport por defecto), el observer NUNCA disparaba
       porque el viewport no se mueve cuando el scroll es interno de
       la tabla. rootMargin de 400px = precarga con anticipación:
       el usuario no percibe el corte, la tabla se siente continua. */
    this.loadMoreRef = useRef('loadMoreBar');
    this._observer = null;
    const reconnect = () => {
      if (this._observedEl && this._observer) {
        this._observer.unobserve(this._observedEl);
        this._observedEl = null;
      }
      const el = this.loadMoreRef.el;
      if (!el) return;
      // Recrear el observer si cambió el ancestro scrolleable.
      const scrollRoot = el.closest('.table-scroll') || null;
      if (!this._observer || this._observerRoot !== scrollRoot) {
        if (this._observer) this._observer.disconnect();
        this._observerRoot = scrollRoot;
        this._observer = new IntersectionObserver(
          (entries) => {
            if (entries.some((e) => e.isIntersecting)) {
              this.loadMore(300);
            }
          },
          { root: scrollRoot, rootMargin: '400px 0px' },
        );
      }
      this._observer.observe(el);
      this._observedEl = el;
    };
    onMounted(reconnect);
    onPatched(reconnect);
    onWillUnmount(() => {
      if (this._observer) this._observer.disconnect();
    });
  }

  _allRows() {
    const st = this.props.state;
    const filterStamp = st.search + '|' + JSON.stringify(st.sfFilters);
    const rc = this._rowsCache;
    if (rc && rc.catalog === st.catalog && rc.stamp === filterStamp) return rc.rows;
    const rows = this._computeRows();
    this._rowsCache = { catalog: st.catalog, stamp: filterStamp, rows };
    return rows;
  }
  get rows() {
    const st = this.props.state;
    // Reset de la ventana cuando cambia búsqueda/filtros — se hace
    // en el getter porque es el único que corre en render con el
    // estado nuevo ya en state. La mutación aquí es idempotente y
    // solo dispara re-render si el valor de verdad cambió.
    const filterStamp = st.search + '|' + JSON.stringify(st.sfFilters);
    if (filterStamp !== this._lastFilterStamp) {
      this._lastFilterStamp = filterStamp;
      if (this.state.renderLimit !== 150) this.state.renderLimit = 150;
    }
    const all = this._allRows();
    const limit = this.state.renderLimit;
    return all.length > limit ? all.slice(0, limit) : all;
  }
  _computeRows() {
    return [...this.filtered].sort((a, b) => {
      const rimA = parseInt(a.rim, 10) || 0;
      const rimB = parseInt(b.rim, 10) || 0;
      if (rimA !== rimB) return rimA - rimB;
      const medA = String(a.medida || '');
      const medB = String(b.medida || '');
      const medCmp = medA.localeCompare(medB, 'es', { numeric: true });
      if (medCmp !== 0) return medCmp;
      return String(a.code || '').localeCompare(String(b.code || ''), 'es', { numeric: true });
    });
  }
}

/* ---------- Selector de columnas extra ---------- */
export class ColumnsPicker extends Component {
  static template = xml`
    <div class="cols-wrap">
      <button class="btn-cols" t-att-class="{ active: props.state.colPickerOpen }"
              t-on-click="() => props.state.colPickerOpen = !props.state.colPickerOpen">
        Columnas ▾
      </button>
      <div class="col-picker" t-att-class="{ open: props.state.colPickerOpen }">
        <div class="col-picker-grid">
          <label class="col-check" t-foreach="columns" t-as="col" t-key="col.key">
            <input type="checkbox" t-att-checked="props.state.visibleColumns.includes(col.key)"
                   t-on-change="() => toggle(col.key)"/>
            <t t-esc="col.label"/>
          </label>
        </div>
        <div class="col-picker-actions">
          <button class="btn-sec" t-on-click="() => setAll(false)">Ninguna</button>
          <button class="btn-sec" t-on-click="() => setAll(true)">Todas</button>
        </div>
      </div>
    </div>`;

  columns = EXTRA_COLUMNS;

  toggle = (key) => {
    const cols = this.props.state.visibleColumns;
    const i = cols.indexOf(key);
    if (i === -1) cols.push(key); else cols.splice(i, 1);
    this.props.onChange();
  };
  setAll = (all) => {
    this.props.state.visibleColumns.splice(0, this.props.state.visibleColumns.length,
      ...(all ? EXTRA_COLUMNS.map((c) => c.key) : []));
    this.props.onChange();
  };
}

/* ---------- Filtros estilo Excel (autofiltro), arriba de la tabla ----------
   Antes eran un panel lateral (acordeón vertical a la izquierda).
   Ahora es una barra horizontal encima de la tabla: un botón por
   campo filtrable, cada uno con su flechita ▾ — igual que el
   autofiltro de Excel — que al hacer clic abre un desplegable con
   checkboxes de los valores distintos de esa columna. */
export class TableFilters extends Component {
  static template = xml`
    <div class="xls-filter-bar">
      <span class="xls-filter-label">Filtros:</span>
      <div class="xls-filter-field" t-foreach="groups" t-as="g" t-key="g.key">
        <button type="button" class="xls-filter-btn" t-att-class="{ active: g.active.length }"
                t-on-click="() => toggleOpen(g.key)">
          <t t-esc="g.label"/><span t-if="g.active.length" class="xls-filter-count" t-esc="g.active.length"/> ▾
        </button>
        <div class="xls-filter-pop" t-if="state.openKey === g.key">
          <div class="xls-filter-pop-actions">
            <button type="button" t-on-click="() => setAll(g.key, true)">Todo</button>
            <button type="button" t-on-click="() => setAll(g.key, false)">Nada</button>
          </div>
          <div class="xls-filter-pop-list">
            <label class="xls-filter-opt" t-foreach="g.options" t-as="opt" t-key="opt.val">
              <input type="checkbox" t-att-checked="g.active.includes(opt.val)"
                     t-on-change="() => toggleValue(g.key, opt.val)"/>
              <span t-esc="opt.val"/>
              <span class="xls-filter-opt-count" t-esc="opt.count"/>
            </label>
          </div>
        </div>
      </div>
      <button type="button" class="xls-filter-clear" t-if="activeCount" t-on-click="reset">
        Limpiar filtros (<t t-esc="activeCount"/>)
      </button>
    </div>`;

  setup() {
    this.state = useState({ openKey: null });
  }

  get activeCount() {
    return Object.values(this.props.state.sfFilters).reduce((s, a) => s + (a ? a.length : 0), 0);
  }

  get groups() {
    const catalog = this.props.state.catalog;
    // Las OPCIONES (valores distintos + conteos) solo dependen del
    // catálogo, que se carga una vez — se calculan una sola vez y se
    // cachean por identidad. Antes se recorrían 9 campos × todo el
    // catálogo (vía el proxy reactivo, que encarece cada acceso) en
    // CADA render: cada clic en un rango de promo, cada tecla del
    // buscador, cada +/- del carrito pagaba ese costo. Ese era el
    // lag restante.
    if (!this._optionsCache || this._optionsCacheSrc !== catalog) {
      this._optionsCacheSrc = catalog;
      this._optionsCache = SF_FIELDS.map((f) => {
        const counts = new Map();
        catalog.forEach((p) => {
          const v = p[f.key];
          if (v === null || v === undefined || v === '' || v === 0) return;
          const label = String(v);
          counts.set(label, (counts.get(label) || 0) + 1);
        });
        const options = [...counts.entries()].sort((a, b) => a[0].localeCompare(b[0], 'es'))
          .map(([val, count]) => ({ val, count }));
        return { key: f.key, label: f.label, options };
      }).filter((g) => g.options.length >= 2);
    }
    // Solo 'active' es dinámico (los filtros palomados) — armarlo por
    // render es barato.
    return this._optionsCache.map((g) => ({
      ...g, active: this.props.state.sfFilters[g.key] || [],
    }));
  }

  toggleOpen = (key) => {
    this.state.openKey = this.state.openKey === key ? null : key;
  };

  toggleValue = (field, val) => {
    const filters = this.props.state.sfFilters;
    if (!filters[field]) filters[field] = [];
    const i = filters[field].indexOf(val);
    if (i === -1) filters[field].push(val); else filters[field].splice(i, 1);
    if (!filters[field].length) delete filters[field];
    this.props.onChange();
    // Autoocultar el desplegable apenas se elige un valor — el
    // usuario ve de inmediato la tabla filtrada, sin tener que cerrar
    // el popover a mano.
    this.state.openKey = null;
  };

  setAll = (field, all) => {
    const filters = this.props.state.sfFilters;
    const g = this.groups.find((x) => x.key === field);
    if (all) filters[field] = g.options.map((o) => o.val);
    else delete filters[field];
    this.props.onChange();
  };

  reset = () => {
    const filters = this.props.state.sfFilters;
    Object.keys(filters).forEach((k) => delete filters[k]);
    this.props.onChange();
  };
}

/* ---------- Área de promociones (facetas + simulador) ----------
   Minimalista de verdad: nombre + conteo, y debajo TODOS sus rangos
   siempre visibles (radios). Sin casilla: elegir un rango YA activa
   esa promo en el simulador (se sobreentiende); volver a hacer clic
   en el rango elegido la desactiva. */
export class PromoStrip extends Component {
  static template = xml`
    <div class="panel promos-panel">
      <h2 title="Elige un rango para simular el precio potencial de los productos que participan.">Promociones</h2>
      <p class="facet-empty" t-if="!props.state.promos.length">Sin promociones vigentes</p>
      <div class="facet" t-foreach="props.state.promos" t-as="pr" t-key="pr.id"
           t-attf-style="--promo-c: {{colorFor(pr).text}}; --promo-b: {{colorFor(pr).border}}; --promo-t: {{colorFor(pr).tint}}">
        <!-- Cabecera COLAPSABLE: clic en cualquier parte alterna el
             despliegue de rangos. El caret ▸/▾ indica el estado;
             el conteo muestra el número de CONDICIONES (tramos),
             no el número de llantas — es lo que el vendedor necesita
             saber al elegir. -->
        <div class="facet-head" t-att-class="{ active: isOn(pr), open: isOpen(pr) }"
             t-att-title="pr.name + ' — ' + conditionCount(pr) + ' condiciones · clic para desplegar'"
             t-attf-style="--promo-c: {{colorFor(pr).text}}; --promo-b: {{colorFor(pr).border}}; --promo-t: {{colorFor(pr).tint}}"
             t-on-click="() => this.toggleOpen(pr)">
          <span class="facet-caret" aria-hidden="true" t-esc="isOpen(pr) ? '▾' : '▸'"/>
          <span class="facet-name">
            <t t-esc="pr.name"/><span class="facet-count" t-esc="'(' + conditionCount(pr) + ')'"/>
          </span>
        </div>
        <div class="facet-body" t-if="isOpen(pr)">
          <div class="promo-compact-meta">
            <span t-esc="pr.policy_label || typeLabel(pr)"/>
            <span>·</span>
            <span t-esc="participantLabel(pr)"/>
          </div>
          <t t-if="pr.tiers.length">
            <label class="facet-tier" t-att-class="{ 'facet-tier-complex': isComplexPolicy(pr) }"
                   t-foreach="pr.tiers" t-as="tier" t-key="tier_index"
                   t-att-title="tierTitle(pr, tier)">
              <input type="radio" t-att-name="'promo_tier_' + pr.id"
                     t-att-checked="isOn(pr) and tierIndex(pr) === tier_index"
                     t-on-click.stop="() => this.pickTier(pr, tier_index)"/>
              <span t-esc="tierLabel(pr, tier)"/>
            </label>
          </t>
          <label class="facet-tier" t-if="pr.promo_type === 'coupons'"
                 title="Simula el apoyo fijo configurado para cada producto participante. Clic de nuevo para quitar.">
            <input type="radio" t-att-name="'promo_tier_' + pr.id"
                   t-att-checked="isOn(pr)"
                   t-on-click.stop="() => this.pickTier(pr, 0)"/>
            <span t-esc="couponLabel(pr)"/>
          </label>
          <p class="facet-note" t-if="!pr.tiers.length and pr.promo_type !== 'coupons'">
            Sin rangos para simular
          </p>
        </div>
      </div>
    </div>`;

  setup() {
    // Estado local del colapso: qué promos están abiertas. Se
    // inicia con TODAS colapsadas para ahorrar espacio en la
    // sidebar angosta del laptop; el usuario abre solo las que le
    // interesan. Cuando el usuario activa un rango (clic en radio),
    // la promo se marca "abierta" automáticamente vía pickTier.
    this._openState = useState({ open: {} });
  }
  isOpen(pr) {
    // Una promo se considera abierta si el usuario la desplegó
    // manualmente O si ya tiene un rango activo (para que el radio
    // seleccionado sea visible sin más clics).
    return !!this._openState.open[pr.id] || this.isOn(pr);
  }
  toggleOpen = (pr) => {
    this._openState.open[pr.id] = !this._openState.open[pr.id];
  };

  sim(pr) {
    return this.props.state.promoSim[pr.id] || null;
  }
  isOn(pr) {
    const s = this.sim(pr);
    return !!(s && s.on);
  }
  tierIndex(pr) {
    const s = this.sim(pr);
    return s && s.tier != null ? s.tier : -1;
  }
  isComplexPolicy(pr) {
    return pr.promo_type === 'rim_quantity' || pr.promo_type === 'monthly_volume';
  }
  compactRims(value) {
    const raw = String(value || '');
    const numbers = [...raw.matchAll(/\d+(?:\.\d+)?/g)]
      .map((match) => Number(match[0]))
      .filter((number) => Number.isFinite(number));
    const unique = [...new Set(numbers)].sort((a, b) => a - b);
    if (!unique.length) return raw;
    if (unique.length > 1) return `R${unique[0]}–R${unique[unique.length - 1]}`;
    return `R${unique[0]}`;
  }
  // Nº de CONDICIONES de la promo: cantidad de tramos configurados,
  // o 1 si son cupones (aporte fijo por pieza). Esto es lo que el
  // vendedor necesita saber al elegir — "cuántas opciones tengo".
  conditionCount(pr) {
    if (pr.promo_type === 'coupons') return 1;
    return (pr.tiers || []).length;
  }
  typeLabel(pr) {
    if (pr.type_label) return pr.type_label;
    return {
      quantity: 'Por cantidad',
      amount: 'Por monto',
      monthly_volume: 'Volumen mensual',
      rim_quantity: 'Cantidad acumulada por rin',
      coupons: 'Cupones',
    }[pr.promo_type] || 'Promoción especial';
  }
  explanation(pr) {
    if (pr.explanation) return pr.explanation;
    return 'Solo se muestran los productos participantes y su beneficio potencial; el pedido completo determina si se gana.';
  }
  participantLabel(pr) {
    const count = pr.product_count != null ? pr.product_count : this.matchCount(pr);
    return `${count} producto${count === 1 ? '' : 's'}`;
  }
  periodLabel(pr) {
    if (!pr.start_date && !pr.end_date) return '';
    if (pr.start_date && pr.end_date) return `Vigencia: ${pr.start_date} al ${pr.end_date}`;
    if (pr.start_date) return `Vigente desde: ${pr.start_date}`;
    return `Vigente hasta: ${pr.end_date}`;
  }
  matchCount(pr) {
    if (!this._catalogIds || this._catalogIdsSrc !== this.props.state.catalog) {
      this._catalogIdsSrc = this.props.state.catalog;
      this._catalogIds = new Set(this.props.state.catalog.map((p) => p.product_id));
    }
    return pr.product_ids.reduce((n, id) => n + (this._catalogIds.has(id) ? 1 : 0), 0);
  }
  tierLabel(pr, tier) {
    const compactNumber = (value) => {
      const n = Number(value || 0);
      if (n >= 1000000) return `${(n / 1000000).toFixed(n % 1000000 ? 1 : 0)}M`;
      if (n >= 1000) return `${(n / 1000).toFixed(n % 1000 ? 1 : 0)}k`;
      return n.toLocaleString('es-MX');
    };
    const reward = pr.reward_type === 'fixed_amount'
      ? '$' + compactNumber(tier.fixed_amount || 0) + ' NC'
      : (tier.discount || 0) + '%';
    const max = Number(tier.max || 999999999);
    const range = max >= 999999999
      ? `${compactNumber(tier.min)}+`
      : `${compactNumber(tier.min)}–${compactNumber(max)}`;
    if (pr.promo_type === 'amount') {
      const qtyRule = tier.min_qty ? ` · mín ${tier.min_qty} pzas` : '';
      return `$${range} → ${reward}${qtyRule}`;
    }
    if (pr.promo_type === 'monthly_volume') {
      return `${range} pzas → ${tier.minimum_products || 0} med · ${tier.minimum_qty_per_measure || 0} c/u · ${reward}`;
    }
    if (pr.promo_type === 'rim_quantity') {
      const breakdown = (tier.rim_discounts || [])
        .map((row) => `${this.compactRims(row.rims)} ${row.discount}%`).join(' · ');
      return `${range} pzas → ${breakdown || '% según rin'}`;
    }
    const qtyRule = tier.min_qty ? ` · mín ${tier.min_qty} pzas` : '';
    return `${range} pzas → ${reward}${qtyRule}`;
  }
  tierTitle(pr, tier) {
    return this.tierLabel(pr, tier)
      + '. Escenario potencial sujeto al pedido completo; clic de nuevo para quitar.';
  }
  couponLabel(pr) {
    const limit = Number(pr.coupon_limit_qty || 0);
    return 'Monto por producto' + (limit ? ` · tope ${limit} pzas` : '');
  }

  // Elegir un rango ACTIVA la promo con ese tramo; clic sobre el
  // rango ya elegido la APAGA (los radios nativos no se pueden
  // desmarcar solos — por eso el handler va en click, no en change).
  colorFor(pr) { return promoColorFor(pr.id); }

  pickTier = (pr, index) => {
    const simAll = this.props.state.promoSim;
    const current = simAll[pr.id];
    if (current && current.on && (current.tier != null ? current.tier : 0) === index) {
      // APAGAR: eliminar la entrada por completo — con {on:false}
      // guardado, el JSON.stringify del cache producía la MISMA
      // huella tras re-activar (mismo shape antes y después) y el
      // mapa memoizado devolvía datos viejos. Sin la entrada, la
      // huella cambia limpio y siempre recalcula.
      delete simAll[pr.id];
    } else {
      simAll[pr.id] = { on: true, tier: index };
    }
    setPromoSim(simAll);
  };
}

/* ---------- Datos del cliente ----------
   Selecciona el cliente (mismo dato que antes vivía en Pedido — se
   movió aquí porque "quién es el cliente" es de las primeras cosas
   que hay que definir, no algo que se confirma hasta abajo) y su
   perfil: 3 categorías con un % cada una. Los porcentajes son un
   ejemplo (0/2/4/5%) — todavía no están conectados al motor de
   reglas, solo quedan registrados junto con el resto del pedido. */
export class ClientPanel extends Component {
  static template = xml`
    <div class="panel client-panel client-panel-compact">
      <h2 title="Descuentos aplicables a esta cotización">Política comercial</h2>
      <div class="client-row">
        <!-- Cliente y RFC se ocultan por ahora — no se usan en esta
             etapa. La selección de cliente sigue disponible en el
             estado (props.state.partnerId) para cuando se reactive:
             es solo el UI el que no la muestra. Sacar los selects
             del DOM también evita que se dispare onPartnerChange
             sin querer. -->
        <div class="client-field client-field-profile" t-foreach="profileFields" t-as="pf" t-key="pf.key">
          <label t-esc="pf.label"/>
          <select t-model="props.state.profile[pf.key]">
            <option t-foreach="profileOptions" t-as="opt" t-key="opt" t-att-value="opt" t-esc="opt + '%'"/>
          </select>
        </div>
      </div>
    </div>`;

  profileFields = PROFILE_FIELDS;
  profileOptions = PROFILE_OPTIONS;

  get selectedPartner() {
    return this.props.state.partners.find((p) => p.id === this.props.state.partnerId) || {};
  }

  // Mismo cast que antes en OrderPanel: t-model en <select> deja el
  // id como string, y el backend espera un entero.
  onPartnerChange = () => {
    const id = parseInt(this.props.state.partnerId, 10);
    if (!Number.isNaN(id)) this.props.state.partnerId = id;
    this.props.onCalculate();
  };
}

/* ---------- Panel de pedido / carrito + resultado de cotización ---------- */
export class OrderPanel extends Component {
  static template = xml`
    <div class="panel order-panel">
      <h2>Pedido</h2>
      <div t-if="!cartIds.length" class="empty-state">
        <span class="empty-state-icon">🧾</span>
        <p class="empty-state-title">Sin productos en el pedido</p>
        <p class="empty-state-hint">Agrega llantas del catálogo para empezar a cotizar.</p>
      </div>
      <t t-else="">
        <!-- Una sola lista: antes había dos (el carrito editable arriba,
             sin precio, y el desglose del ticket abajo, con precio pero
             no editable) — la misma llanta aparecía dos veces y para
             revisar el precio había que bajar a otra sección. Ahora
             cada línea trae cantidad editable + precio + subtotal +
             DOT/disponibles juntos. -->
        <div class="cart-header-row">
          <span>
            <t t-esc="cartIds.length"/> producto<t t-if="cartIds.length != 1">s</t> distintos
            <span class="cart-header-pieces">· <t t-esc="totalPieces"/> pieza<t t-if="totalPieces != 1">s</t></span>
          </span>
        </div>
        <!-- Buscador propio del carrito: con pedidos grandes (50, 100,
             150+ líneas) es la forma más rápida de encontrar/editar
             una llanta puntual sin desplazarse por toda la lista.
             Solo aparece si hay suficientes líneas para justificarlo. -->
        <div class="cart-search" t-if="cartIds.length > 8">
          <span class="cart-search-icon" aria-hidden="true">🔍</span>
          <input type="text" placeholder="Buscar en el pedido…" t-model="state.cartSearch"/>
        </div>
        <div class="empty-state cart-no-match" t-if="cartIds.length and !filteredCartIds.length">
          <p class="empty-state-hint">Sin resultados para "<t t-esc="state.cartSearch"/>" dentro del pedido.</p>
        </div>
        <!-- Antes era una lista de tarjetas apiladas — ahora es una
             tabla, mismo lenguaje visual que el catálogo (.flat-table),
             para que Pedido no se sienta como un componente aparte con
             sus propias reglas. Con .stack a ancho completo ya no hace
             falta apretar todo en una columna angosta. -->
        <!-- Sin agrupar ni limitar altura: la lista simplemente crece
             hacia abajo con la página, por larga que sea — el buscador
             de arriba ya cubre "encontrar algo puntual" en pedidos
             grandes, así que no hace falta la complejidad extra de
             bloques colapsables (eso sigue disponible en el modal
             "Ver pedido completo" para quien sí lo quiera). -->
        <!-- Lista compacta (ya no tabla): el Pedido vive ahora en una
             columna angosta a la derecha, siempre visible — una tabla
             de 7 columnas no cabe ahí. Cada línea apila: nombre +
             quitar, código·medida + DOT/Inv discretos, y el renglón
             de acción con stepper, precio (lista tachada si hay
             promo) y subtotal. Funciona igual en móvil, donde el
             panel ocupa todo el ancho. -->
        <div class="cart-lines" t-if="filteredCartIds.length">
          <div class="cart-line-compact" t-foreach="filteredCartIds" t-as="id" t-key="id">
            <div class="clc-row">
              <span class="clc-info">
                <span class="clc-brand" t-esc="productFor(id).brand || ''"/>
                <span class="clc-model" t-esc="productFor(id).model || ''"/>
                <span class="clc-meta" t-esc="(productFor(id).code || '') + ' · ' + (productFor(id).medida || '')"/>
              </span>
              <input type="number" min="1" class="clc-qty" t-att-value="props.state.cart[id]"
                     t-on-change="(ev) => props.onSetQty(id, ev.target.value)"
                     t-on-keydown="(ev) => ev.key === 'Enter' and ev.target.blur()"
                     title="Editar cantidad"/>
              <span class="clc-prices">
                <span class="clc-list" t-if="lineInfo(id).hasPromo" t-esc="money(lineInfo(id).listPrice * iva)"/>
                <span class="clc-price" t-att-class="{ 'clc-promo': lineInfo(id).hasPromo }" t-esc="money(lineInfo(id).unitPrice * iva)"/>
                <span class="clc-saving" t-if="lineInfo(id).hasPromo"
                      title="Ahorro por pieza si se cumplen las condiciones">
                  Ahorras <t t-esc="money((lineInfo(id).listPrice - lineInfo(id).unitPrice) * iva)"/>/pza
                </span>
              </span>
              <button class="clc-remove" title="Quitar" t-on-click="() => props.onRemove(id)">✕</button>
            </div>
          </div>
        </div>
        <div id="resultBox">
          <span class="calc-loading" t-if="props.state.quoteLoading">Calculando…</span>
          <div class="error-box" t-if="props.state.quoteError" t-esc="props.state.quoteError"/>
          <t t-if="props.state.quote">
            <div class="price-tag">
              <div class="hole"/>
              <div class="sv-row" t-if="totalSavings > 0">
                <span class="sv-lbl">Lista (sin promos)</span>
                <span class="sv-val sv-strike" t-esc="money(totalList * iva)"/>
              </div>
              <div class="sv-row sv-green" t-if="totalSavings > 0">
                <span class="sv-lbl">Ahorro potencial (<t t-esc="savingsPct"/>%)</span>
                <span class="sv-val" t-esc="'-' + money(totalSavings * iva)"/>
              </div>
              <div class="sv-row sv-detail" t-if="policySavingAmt > 0.01">
                <span class="sv-lbl">Política (−<t t-esc="policyPctTotal"/>%)</span>
                <span class="sv-val" t-esc="'-' + money(policySavingAmt * iva)"/>
              </div>
              <div class="sv-row sv-detail sv-promo" t-foreach="promoSavingsList" t-as="ps" t-key="ps.id">
                <span class="sv-lbl" t-attf-style="color: {{ps.color}}" t-esc="ps.name"/>
                <span class="sv-val" t-attf-style="color: {{ps.color}}" t-esc="'-' + money(ps.amount * iva)"/>
              </div>
              <div class="total-row total-row-secondary" t-if="hasPromotionDiscount">
                <span class="label">Total si cumple las condiciones <small class="iva-mode" t-esc="props.state.showIva ? '(con IVA)' : '(sin IVA)'"/></span>
                <span class="value" t-esc="money(props.state.quote.order_total * factor * iva)"/>
              </div>
              <div class="total-row">
                <span class="label">
                  <t t-if="hasPromotionDiscount">Total con todos los descuentos</t>
                  <t t-elif="policySavingAmt > 0.01">Total con política comercial</t>
                  <t t-else="">Total del pedido</t>
                  <small class="iva-mode" t-esc="props.state.showIva ? '(con IVA)' : '(sin IVA)'"/>
                </span>
                <span class="value" t-esc="money(grandTotal * iva)"/>
              </div>
              <!-- Promoción ganada en NC (motor ztyres_promo): monto
                   INFORMATIVO que el cliente ganaría en Nota de
                   Crédito con las promos vigentes — no descuenta el
                   total del pedido (la NC se emite al facturar, desde
                   el flujo normal de ztyres_promo). -->
              <div class="bonus-line nc-line" t-if="ncPreview">
                🏷️ Promoción ganada (NC)<t t-if="ncPreview.items.length > 1"> — <t t-esc="ncPreview.items.length"/> promos</t>: <t t-esc="money(ncPreview.total * iva)"/>
              </div>
            </div>
            <ul class="nc-detail" t-if="ncPreview">
              <!-- t-key por índice: usar it.name podía colapsar dos
                   promos si compartieran nombre (edge case), y los
                   promo_id vienen del motor sin garantía de ser únicos
                   contra otros items futuros. it_index es siempre
                   único y estable dentro del render. -->
              <li t-foreach="ncPreview.items" t-as="it" t-key="it_index" t-esc="it.message"/>
            </ul>
            <button class="btn-main btn-xlsx" style="width:100%;margin-top:8px;"
                    t-att-class="{ 'is-loading': props.state.xlsxLoading === 'order' }"
                    t-att-disabled="props.state.xlsxLoading === 'order'"
                    t-on-click="() => props.onDownloadXlsx()"
                    title="Descarga la cotización en Excel con las promociones y política seleccionadas">
              <t t-if="props.state.xlsxLoading === 'order'">⏳ Generando...</t>
              <t t-else="">📥 Descargar Cotización</t>
            </button>
          </t>
        </div>
      </t>
    </div>`;
  static components = { IconPlus, IconMinus, IconTrash };

  setup() {
    this.state = useState({
      cartSearch: '',
    });
  }

  money = money;
  formatDot = formatDot;

  // Factor de la Política comercial — mismo cálculo que el catálogo,
  // aplicado a precios unitarios, subtotales y total del pedido.
  get factor() {
    return policyFactor(this.props.state.profile);
  }
  get policyText() {
    return policyLabel(this.props.state.profile);
  }
  get iva() {
    return this.props.state.showIva ? 1 + IVA_RATE : 1;
  }

  // --- Desglose de ahorros para el panel de Pedido ---
  get policyPctTotal() {
    const p = this.props.state.profile || {};
    return ((parseFloat(p.volumen) || 0) + (parseFloat(p.logistico) || 0) + (parseFloat(p.financiero) || 0)).toFixed(1).replace(/\.0$/, '');
  }
  get policySavingAmt() {
    const pct = parseFloat(this.policyPctTotal) || 0;
    return this.totalList * (pct / 100);
  }
  get savingsPct() {
    if (!this.totalList) return '0';
    return (this.totalSavings / this.totalList * 100).toFixed(1).replace(/\.0$/, '');
  }
  // Desglose por promo: cuánto ahorra cada una sobre el pedido actual
  get promoSavingsList() {
    const { promos, promoSim, cart } = this.props.state;
    if (!promos.length || !this.props.state.quote) return [];
    const cartPids = new Set(Object.keys(cart).map(Number));
    const result = [];
    for (const pr of promos) {
      const sel = promoSim[pr.id];
      if (!sel || !sel.on) continue;
      const tier = selectedTierForPromo(this.props.state, pr, sel);
      let amount = 0;
      for (const line of this.props.state.quote.lines) {
        const pid = line.product_id;
        if (!cartPids.has(pid)) continue;
        if (!(pr.product_ids || []).includes(pid)) continue;
        const lista = line.unit_price || 0;
        const prod = this.productFor(String(pid));
        const disc = promoUnitDiscount(pr, tier, prod, lista);
        amount += disc * (cart[pid] || 0);
      }
      if (amount > 0.005) {
        result.push({ id: pr.id, name: pr.name, amount, color: promoColorFor(pr.id).text });
      }
    }
    return result;
  }

  get totalList() {
    if (!this.props.state.quote) return 0;
    return this.props.state.quote.lines.reduce((s, l) => s + l.unit_price * l.qty, 0);
  }
  get totalSavings() {
    return Math.max(this.policySavingAmt + this.promoSavingsTotal, 0);
  }
  // v3.2.2 — El "Total si cumple las condiciones" solo restaba el
  // descuento de Política (order_total ya viene a precio de lista,
  // sin promos: ver get_promotions_preview en sale_order.py). Las
  // promos simuladas se mostraban arriba como si se descontaran,
  // pero nunca bajaban de ese total — quedaba engañoso. Este getter
  // suma TODOS los descuentos visibles (Política + promos simuladas)
  // para dar el total real "todo incluido".
  get promoSavingsTotal() {
    return this.promoSavingsList.reduce((s, ps) => s + ps.amount, 0);
  }
  get hasPromotionDiscount() {
    return this.promoSavingsTotal > 0.005;
  }
  get grandTotal() {
    if (!this.props.state.quote) return 0;
    const base = this.props.state.quote.order_total * this.factor;
    return Math.max(base - this.promoSavingsTotal, 0);
  }

  /* Bloque "Promoción ganada (NC)" del quote — viene del puente con
     ztyres_promo en el servidor (get_promotions_preview). Es null si
     ese módulo no está instalado o ninguna promo vigente aplica. */
  get ncPreview() {
    const q = this.props.state.quote;
    return (q && q.promo_ganada && q.promo_ganada.total > 0) ? q.promo_ganada : null;
  }
  // Monto NC atribuible a una línea puntual del carrito (0 si nada).
  // Las claves del JSON llegan como string — los ids del carrito
  // también lo son, así que el acceso directo coincide.
  ncFor = (id) => {
    const nc = this.ncPreview;
    return nc && nc.per_product ? (nc.per_product[String(id)] || 0) : 0;
  };
  // Desglose por línea: qué promos aportaron y cuánto. Cuando hay
  // dos o más, se pintan en el chip "NC +$X" con su color y monto.
  ncPartsFor = (id) => {
    const nc = this.ncPreview;
    if (!nc || !nc.per_product_parts) return [];
    return nc.per_product_parts[String(id)] || [];
  };
  ncTitleFor = (id) => {
    const parts = this.ncPartsFor(id);
    if (parts.length <= 1) return 'Ganancia estimada en Nota de Crédito por promoción vigente';
    return 'Contribuciones a la NC:\n' + parts
      .map((p) => `  · ${p.promo}: $${p.amount.toFixed(2)}`).join('\n');
  };
  // Color de una promo por id — usa la misma paleta que las facetas.
  colorFor = (promoId) => promoColorFor(promoId);

  get cartIds() {
    return Object.keys(this.props.state.cart);
  }
  // Total de PIEZAS (suma de cantidades), no de líneas distintas —
  // con pedidos grandes es fácil perder de vista cuántas llantas son
  // en total cuando solo se ve "12 productos" (podrían ser 12 o 400
  // piezas según la cantidad de cada uno).
  get totalPieces() {
    return Object.values(this.props.state.cart).reduce((s, q) => s + (q || 0), 0);
  }
  get filteredCartIds() {
    const q = this.state.cartSearch.trim().toLowerCase();
    if (!q) return this.cartIds;
    return this.cartIds.filter((id) => {
      const p = this.productFor(id);
      const text = `${p.brand || ''} ${p.name || ''} ${p.medida || ''}`.toLowerCase();
      return text.includes(q);
    });
  }
  productFor = (id) => {
    return this.props.state.catalog.find((p) => String(p.product_id) === String(id)) || {};
  };
  // Descuento unitario simulado de las promociones seleccionadas para
  // un producto puntual. Es el mismo criterio que usa el catálogo:
  // suma cupones o porcentajes de todas las promociones activas.
  promoDiscountPerUnit = (id, listPrice) => {
    const st = this.props.state;
    const product = this.productFor(id);
    let discount = 0;
    for (const promo of st.promos || []) {
      const selected = st.promoSim[promo.id];
      if (!selected || !selected.on) continue;
      if (!(promo.product_ids || []).includes(Number(id))) continue;

      const tier = selectedTierForPromo(st, promo, selected);
      discount += promoUnitDiscount(promo, tier, product, listPrice);
    }
    return discount;
  };
  // Precio/subtotal/DOT por línea: prioriza lo que ya calculó el
  // motor de promociones (state.quote.lines, con descuentos
  // aplicados) — antes de que llegue esa respuesta (o si falló),
  // se cae al precio de catálogo sin descuento como estimado, para
  // no dejar la columna vacía mientras se calcula.
  lineInfo = (id) => {
    const qty = this.props.state.cart[id] || 0;
    const product = this.productFor(id);
    const quoteLine = this.props.state.quote
      && this.props.state.quote.lines.find((l) => String(l.product_id) === String(id));
    // La Política comercial descuenta directo el precio de la línea
    // (en cascada, ver policyFactor); si el factor es 1.0 se muestra
    // lista tal cual. La NC de ztyres_promo NO se resta aquí — es un
    // beneficio aparte que ya se muestra como "NC +$" por línea.
    const f = this.factor;
    if (quoteLine) {
      const list = quoteLine.unit_price || 0;
      const unit = Math.max(
        quoteLine.final_unit_price * f - this.promoDiscountPerUnit(id, list),
        0,
      );
      return {
        unitPrice: unit,
        listPrice: list,
        hasPromo: unit < list - 0.005,
        subtotal: unit * qty,
        dotRange: quoteLine.dot_range,
        freeQty: quoteLine.free_qty,
      };
    }
    const list = product.price || 0;
    const unit = Math.max(
      list * f - this.promoDiscountPerUnit(id, list),
      0,
    );
    return {
      unitPrice: unit,
      listPrice: list,
      hasPromo: unit < list - 0.005,
      subtotal: unit * qty,
      dotRange: product.dot_range,
      freeQty: product.free_qty,
    };
  };
}

/* ---------- Modal de zoom de imagen ---------- */
