/** @odoo-module **/
/* ============================================================
   Cotizador Owl · Ztyres — Componentes
   ============================================================ */
import { Component, useState, useRef, useExternalListener, onMounted, onPatched, onWillUnmount, xml } from "@odoo/owl";

import { IconPlus, IconMinus, IconTrash } from './icons.js';
import {
  EXTRA_COLUMNS, SF_FIELDS, PROFILE_FIELDS, money, formatDot, formatColumnValue, normalizeSearchText, setPromoSim, policyFactor, policyLabel, IVA_RATE, setShowIva, promoColorFor,
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
    // Cupón / apoyo fijo por pieza: SÍ es un descuento sobre la llanta
    // (tiene tope de piezas y se refleja en la NC del pedido).
    const coupon = (promo.coupons || []).find(
      (item) => item.tmpl_id === product.tmpl_id,
    );
    return coupon ? Number(coupon.amount || 0) : 0;
  }
  /* Tarjeta de regalo: NO baja el precio de la llanta. El cliente se
     lleva una tarjeta por ese valor (ver docs/TARJETA_REGALO.md — con
     gift_card_delivery='none', que es el default, ni siquiera emite
     NC). Descontarla del precio unitario hacía ver la llanta más barata
     de lo que se cobra. Vive en su propia columna, vía
     giftCardAmountFor. */
  if (promo.reward_type === 'gift_card') return 0;
  const percent = promoPercentForProduct(promo, tier, product.product_id);
  const rawPms = (promo.pms_price_by_product || {})[String(product.product_id)];
  if (rawPms != null) {
    // Base PMS: el porcentaje se calcula sobre el precio PMS pactado,
    // que es independiente de la lista y de Mayoreo. No se toca.
    const roundMoney = (value) => Math.round((Number(value) + Number.EPSILON) * 100) / 100;
    const unitReward = roundMoney(Number(rawPms || 0) * percent / 100);
    return roundMoney(unitReward / Number(promo.pms_tax_factor || 1));
  }
  // Sobre LISTA, no sobre el precio base (ya con Mayoreo aplicado) —
  // igual que _cotizador_promo_discount en sale_order.py (usa
  // `lista`, no `base`). Si se calculara sobre base, Mayoreo y la
  // promo se encadenarían (cascada) en vez de restarse cada una por
  // su lado desde lista (directo), y el Excel del cotizador dejaría
  // de cuadrar con lo que realmente cobra el motor de promociones.
  return (Number(listPrice) || 0) * percent / 100;
}

function mayoreoUnitDiscount(product, listPrice) {
  return Number(listPrice || 0)
    * (Number(product && product.mayoreo_discount || 0) / 100);
}

/* Precio BASE de una llanta: el de lista menos la política Mayoreo
   (−10% en Bridgestone/Firestone que pertenecen a esa lista de precios).
   Es el precio desde el que se calcula todo lo demás — política
   comercial y promociones aplican SOBRE este número, no sobre el de
   lista. Antes el −10% se restaba al final junto con los otros
   descuentos, lo que hacía que la promo se calculara sobre un precio
   que el cliente nunca iba a pagar.
   `listPrice` permite pasar el precio de una línea del pedido, que
   puede diferir del de catálogo. Mismo criterio en el servidor:
   _cotizador_base_price en sale_order.py. */
function basePriceOf(product, listPrice) {
  const list = listPrice != null ? Number(listPrice) : Number(product && product.price || 0);
  return Math.max(list - mayoreoUnitDiscount(product, list), 0);
}

/* Monto de tarjeta de regalo por pieza para un producto. Es un
   beneficio aparte: el cliente recibe una tarjeta, la llanta no baja de
   precio. Por eso vive en su propia columna y NO entra al precio. */
function giftCardAmountFor(promo, product) {
  if (promo.reward_type !== 'gift_card') return 0;
  if (!product || !(promo.product_ids || []).includes(Number(product.product_id))) return 0;
  const card = (promo.coupons || []).find((item) => item.tmpl_id === product.tmpl_id);
  return card ? Number(card.amount || 0) : 0;
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
      <td class="flat-td-clave" data-label="Código" t-att-title="props.product.code || ''">
        <span t-esc="props.product.code || '—'"/>
      </td>
      <!-- La columna K/B se retiró: el % de Key Size ya viaja dentro del
           beneficio de la promo y el −10% de Mayoreo ya viene aplicado en
           el precio de la columna Precio. Marcarlos además con una letra
           obligaba al vendedor a recalcular mentalmente algo que la
           aritmética ya resolvió. -->
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
      <!-- Precio base. En Bridgestone/Firestone de la lista Mayoreo ya
           trae aplicado el −10%: es el precio desde el que se calcula
           todo lo demás, no el de lista publicada. -->
      <td class="flat-td-price" data-label="Precio" t-att-title="priceTitle()"
          t-att-class="{ 'has-promo': !!finalPrice(), 'is-mayoreo-price': props.product.is_mayoreo }"
          t-esc="money(basePrice() * props.iva)"/>
      <td class="flat-td-promo" data-label="Pr Promo" t-att-title="finalTitle()">
        <span t-if="finalPrice()" class="promo-price" t-esc="money(finalPrice() * props.iva)"/>
        <span t-else="" class="promo-empty" t-att-title="props.qty ? 'Sin promoción ni descuento aplicable' : 'Agrega al pedido o elige una promo/política para simular'">—</span>
      </td>
      <!-- Tarjeta de regalo: monto por pieza que el cliente recibe en
           tarjeta. Va en su propia columna porque NO es un descuento
           sobre el precio de la llanta. Se pinta en gris cuando la promo
           que la otorga aún no está seleccionada en el simulador. -->
      <td class="flat-td-giftcard" data-label="Tarjeta" t-att-title="giftCardTitle()">
        <span t-if="props.giftCard" class="giftcard-amount"
              t-att-class="{ pending: !props.giftCard.active }"
              t-esc="money(props.giftCard.amount * props.iva)"/>
        <span t-else="" class="promo-empty">—</span>
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
      /* Columnas que reciben tinte = todas menos la de acción. Se
         quitó K/B y se agregó Tarjeta, así que el fijo queda igual en
         15; si se añade o quita una columna hay que actualizar este
         número o las bandas de color dejan de cubrir la fila. */
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
  /* Precio base de la fila. Para Bridgestone/Firestone dentro de la
     lista Mayoreo, el −10% ya está aplicado aquí: ese es el precio que
     el vendedor cotiza y desde el que se calculan política y promos.
     Antes el −10% se restaba solo al final, en Pr Promo, y la columna
     Precio mostraba un precio de lista que nunca se cobraba. */
  basePrice() {
    return basePriceOf(this.props.product);
  }
  priceTitle() {
    if (!this.props.product.is_mayoreo) return '';
    const list = this.props.product.price || 0;
    return `Ya incluye Mayoreo −10% · Precio de lista ${money(list * this.props.iva)}`;
  }
  finalPrice() {
    if (this.props.promo) return this.props.promo.price;
    const base = this.basePrice();
    // Política se calcula SOBRE LISTA (no sobre `base`, que ya trae
    // Mayoreo restado) y se resta junto con Mayoreo — no en cascada.
    // lista×0.9×0.98 (cascada) ≠ lista×(1−0.10−0.02) (directo); la
    // cascada le cobra de más al cliente cuando hay Mayoreo + política.
    if (this.props.factor < 0.9999) {
      const list = this.props.product.price || 0;
      const policyDisc = list * (1 - this.props.factor);
      return Math.max(base - policyDisc, 0);
    }
    return 0;
  }
  finalTitle() {
    if (this.props.promo) return this.props.promo.label;
    if (this.props.factor < 0.9999) return 'Política comercial: ' + this.props.policyText;
    return '';
  }
  giftCardTitle() {
    const card = this.props.giftCard;
    if (!card) return '';
    const state = card.active
      ? 'Condición seleccionada en el simulador'
      : 'Requiere seleccionar la condición de esta promoción';
    return `${card.promoName} · tarjeta de regalo por pieza. ${state}. `
      + 'No descuenta el precio de la llanta.';
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
          <th class="flat-th-price" title="Precio por pieza desde el que se calcula todo. En Bridgestone/Firestone de la lista Mayoreo ya incluye el −10%.">Precio</th>
          <th class="flat-th-promo" title="Precio efectivo por pieza considerando la promoción vigente (NC estimada del pedido actual)">Pr Promo</th>
          <th class="flat-th-giftcard" title="Monto de tarjeta de regalo por pieza. Es un beneficio aparte: no baja el precio de la llanta.">Tarjeta</th>
          <th class="flat-th-action">Agregar</th>
        </tr>
      </thead>
      <tbody t-if="ui.isMobile" class="grouped-body">
        <t t-foreach="mobileGroups" t-as="rg" t-key="rg.key">
          <tr class="grp-row grp-rim" t-att-class="{ open: open.rims[rg.key] }"
              t-on-click="() => this.toggleRim(rg)">
            <td colspan="99">
              <span class="grp-caret">▸</span>
              <span class="grp-title" t-esc="rg.label"/>
              <span class="grp-sub"><t t-esc="rg.medidas.length"/> medidas</span>
              <span class="grp-count" t-esc="rg.count"/>
            </td>
          </tr>
          <t t-if="open.rims[rg.key]">
            <t t-foreach="rg.medidas" t-as="mg" t-key="mg.key">
              <tr class="grp-row grp-medida" t-att-class="{ open: open.meds[mg.key] }"
                  t-on-click="() => this.toggleMed(mg)">
                <td colspan="99">
                  <span class="grp-caret">▸</span>
                  <span class="grp-title" t-esc="mg.label"/>
                  <span class="grp-count" t-esc="mg.count"/>
                </td>
              </tr>
              <t t-if="open.meds[mg.key]">
                <CatalogRow t-foreach="mg.products" t-as="product" t-key="product.product_id"
                            product="product"
                            qty="props.state.cart[product.product_id] or 0"
                            promo="promoEntry(product)"
                            giftCard="giftCardFor(product)"
                            color="colorFor(product)"
                            factor="factor"
                            iva="iva"
                            policyText="policyText"
                            extraColumns="extraColumns"
                            onAdd="props.onAdd" onInc="props.onInc" onDec="props.onDec" onSetQty="props.onSetQty"/>
              </t>
            </t>
          </t>
        </t>
      </tbody>
      <tbody t-else="">
        <CatalogRow t-foreach="rows" t-as="product" t-key="product.product_id"
                    product="product"
                    qty="props.state.cart[product.product_id] or 0"
                    promo="promoEntry(product)"
                    giftCard="giftCardFor(product)"
                    color="colorFor(product)"
                    factor="factor"
                    iva="iva"
                    policyText="policyText"
                    extraColumns="extraColumns"
                    onAdd="props.onAdd" onInc="props.onInc" onDec="props.onDec" onSetQty="props.onSetQty"/>
      </tbody>
    </table>
    <div class="grp-foot" t-if="ui.isMobile and anyGroupOpen">
      <button type="button" class="btn-sec" t-on-click="() => this.collapseAll()">Contraer todo</button>
    </div>
    <div class="load-more" t-if="!ui.isMobile and hiddenCount > 0" t-ref="loadMoreBar">
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
        // Mayoreo define el precio BASE que se muestra/cotiza, pero
        // política y NC se calculan sobre LISTA (no sobre esa base) y
        // se restan junto con Mayoreo — los tres de forma independiente,
        // sin que uno cascadee sobre el resultado de otro.
        const base = basePriceOf(prod, lista);
        const policyDisc = lista * (1 - policyFactor(st.profile));
        const eff = Math.max(base - policyDisc - nc / qty, 0);
        if (eff < base - 0.005) {
          real.set(parseInt(pidStr, 10), {
            price: eff,
            label: 'Precio efectivo real: precio base (ya con Mayoreo) − política comercial − NC de este pedido',
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
        if ((pr.promo_type === 'coupons' || pr.reward_type === 'gift_card') && disc > 0) {
          partLabel = `${pr.display_label || pr.name} Cupón $${disc.toFixed(2)}`;
        } else {
          const pct = promoPercentForProduct(pr, tier, pid);
          if (pct > 0) partLabel = `${pr.display_label || pr.name} ${pct}%`;
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
      const base = basePriceOf(prod);
      // Política sobre lista, no sobre `base` (ya con Mayoreo) — ver
      // nota de policyFactor en constants.js: es aditivo, no cascada.
      const policyDisc = (prod.price || 0) * policyPctOff;
      const final = Math.max(base - policyDisc - bucket.discSum, 0);
      if (!(final < base - 0.005)) continue;
      const partsTxt = bucket.parts.map((p) => p.label).join(' + ');
      const polTxt = policyTxt ? ` + Política ${policyTxt}` : '';
      const mayoreoTxt = prod.is_mayoreo ? ' (base ya con Mayoreo −10%)' : '';
      sim.set(pid, {
        price: final,
        label: `Simulado · ${partsTxt}${polTxt} — cada descuento sobre el precio base${mayoreoTxt}`,
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
    // Al elegir una condición, el vendedor está pidiendo ver ESA
    // simulación (incluida su base PMS y % Key Size). La NC real del
    // carrito queda como respaldo cuando no hay simulación seleccionada.
    return maps.sim.get(product.product_id) || maps.real.get(product.product_id) || null;
  }
  /* Tarjeta de regalo por pieza. Se muestra siempre que el producto
     tenga una configurada en alguna promo vigente — no solo cuando la
     promo está simulada — porque el vendedor necesita saber que la
     tarjeta existe antes de decidir. `active` distingue si ya eligió la
     condición que la otorga; la fila la pinta en gris mientras no.
     Si dos promos vigentes dan tarjeta al mismo producto, se suman los
     montos de las activas; si ninguna está activa, se muestra la mayor
     configurada como referencia. */
  giftCardFor(product) {
    const promos = this.props.state.promos || [];
    let activeSum = 0;
    let activeNames = [];
    let best = null;
    for (const promo of promos) {
      const amount = giftCardAmountFor(promo, product);
      if (!(amount > 0)) continue;
      const sel = this.props.state.promoSim[promo.id];
      if (sel && sel.on) {
        activeSum += amount;
        activeNames.push(promo.display_label || promo.name);
      } else if (!best || amount > best.amount) {
        best = { amount, promoName: promo.display_label || promo.name };
      }
    }
    if (activeSum > 0) {
      return { amount: activeSum, promoName: activeNames.join(' + '), active: true };
    }
    return best ? { ...best, active: false } : null;
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

    /* MÓVIL: el catálogo plano de miles de tarjetas es imposible de
       recorrer con el pulgar. Ahí se vuelve a agrupar como en la
       versión vieja — acordeón Rin → Medida → llantas — y por eso
       tampoco hace falta la ventana de renderLimit: lo que acota el
       DOM es que los grupos nacen cerrados. */
    this.ui = useState({ isMobile: window.matchMedia('(max-width: 700px)').matches });
    this.open = useState({ rims: {}, meds: {} });
    const mq = window.matchMedia('(max-width: 700px)');
    this._onMq = (ev) => { this.ui.isMobile = ev.matches; };
    mq.addEventListener('change', this._onMq);
    onWillUnmount(() => mq.removeEventListener('change', this._onMq));

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
  /* ---------- Agrupado de móvil: Rin → Medida → llantas ----------
     Se arma sobre _allRows(), que YA viene ordenado rin → medida →
     clave, así que basta recorrer una vez y respetar el orden de
     inserción de los Map. Se cachea por la misma huella que las
     filas: sólo se recalcula si cambian catálogo, búsqueda o
     filtros. */
  get mobileGroups() {
    const st = this.props.state;
    const stamp = st.search + '|' + JSON.stringify(st.sfFilters);
    const c = this._mgCache;
    if (c && c.catalog === st.catalog && c.stamp === stamp) return c.groups;

    const byRim = new Map();
    this._allRows().forEach((p) => {
      const rim = (p.rim === null || p.rim === undefined || p.rim === '') ? '' : String(p.rim);
      let rg = byRim.get(rim);
      if (!rg) {
        rg = { key: 'r:' + rim, label: rim ? 'Rin ' + rim : 'Sin rin', count: 0, medMap: new Map(), medidas: [] };
        byRim.set(rim, rg);
      }
      rg.count++;
      const med = String(p.medida || '—');
      let mg = rg.medMap.get(med);
      if (!mg) {
        mg = { key: rg.key + '|' + med, label: med, count: 0, products: [] };
        rg.medMap.set(med, mg);
        rg.medidas.push(mg);
      }
      mg.count++;
      mg.products.push(p);
    });
    const groups = [...byRim.values()];
    groups.forEach((g) => { delete g.medMap; });
    this._mgCache = { catalog: st.catalog, stamp, groups };
    this._autoOpen(groups, stamp);
    return groups;
  }

  /* Al cambiar búsqueda/filtros se recalcula qué nace abierto:
     - resultado chico (≤40 llantas): todo abierto, no tiene caso
       hacer tocar acordeones para ver 6 productos;
     - un solo rin: se abre ese rin (y su medida, si es una sola);
     - lo demás: todo cerrado, la lista arranca como índice. */
  _autoOpen(groups, stamp) {
    if (this._autoOpenStamp === stamp) return;
    this._autoOpenStamp = stamp;
    const total = groups.reduce((s, g) => s + g.count, 0);
    const openAll = total > 0 && total <= 40;
    const rims = {};
    const meds = {};
    if (openAll || groups.length === 1) {
      groups.forEach((g) => {
        rims[g.key] = true;
        if (openAll || g.medidas.length === 1) g.medidas.forEach((m) => { meds[m.key] = true; });
      });
    }
    this.open.rims = rims;
    this.open.meds = meds;
  }

  get anyGroupOpen() {
    return Object.values(this.open.rims).some(Boolean);
  }

  toggleRim = (rg) => {
    const on = !this.open.rims[rg.key];
    this.open.rims[rg.key] = on;
    // Un rin con una sola medida no merece un segundo toque.
    if (on && rg.medidas.length === 1) this.open.meds[rg.medidas[0].key] = true;
  };

  toggleMed = (mg) => {
    this.open.meds[mg.key] = !this.open.meds[mg.key];
  };

  collapseAll = () => {
    this.open.rims = {};
    this.open.meds = {};
  };

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
    <div class="xls-filter-bar" t-ref="bar">
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
            <button type="button" class="xls-filter-pop-done" t-on-click="close">Listo</button>
          </div>
          <div class="xls-filter-pop-list">
            <label class="xls-filter-opt" t-foreach="g.options" t-as="opt" t-key="opt.val">
              <span class="xls-filter-opt-val" t-att-title="opt.val" t-esc="opt.val"/>
              <span class="xls-filter-opt-count" t-esc="opt.count"/>
              <input type="checkbox" class="xls-filter-opt-box"
                     t-att-checked="g.active.includes(opt.val)"
                     t-on-change="() => toggleValue(g.key, opt.val)"/>
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
    this.barRef = useRef('bar');
    // El desplegable ya NO se cierra al palomear un valor (antes sí, y
    // obligaba a reabrirlo por cada marca). Se queda abierto para poder
    // elegir varias; se cierra con "Listo", con Esc, volviendo a hacer
    // clic en el botón del filtro, o haciendo clic fuera de la barra.
    useExternalListener(window, 'mousedown', this.onOutsideDown);
    useExternalListener(window, 'keydown', this.onKeyDown);
  }

  onOutsideDown = (ev) => {
    if (this.state.openKey === null) return;
    const bar = this.barRef.el;
    if (bar && !bar.contains(ev.target)) this.state.openKey = null;
  };

  onKeyDown = (ev) => {
    if (ev.key === 'Escape' && this.state.openKey !== null) this.state.openKey = null;
  };

  close = () => { this.state.openKey = null; };

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
    // El popover se queda abierto a propósito: la tabla de atrás se
    // filtra en vivo mientras se palomean varios valores seguidos.
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
        <!-- Cabecera COLAPSABLE. El nombre se parte en tres piezas
             (periodo · tipo · nombre corto) porque el nombre completo
             repite el mismo prefijo en todas las promos y en la columna
             angosta no llega a mostrar lo único que las distingue. El
             nombre corto sale del campo cotizador_name de la promoción
             (display_label) y cae al nombre completo si está vacío. -->
        <div class="facet-head" t-att-class="{ active: isOn(pr), open: isOpen(pr) }"
             t-att-title="pr.name + ' — ' + conditionCount(pr) + ' condiciones · clic para desplegar'"
             t-on-click="() => this.toggleOpen(pr)">
          <span class="promo-headline">
            <span class="promo-eyebrow">
              <span class="promo-period" t-if="periodChip(pr)" t-esc="periodChip(pr)"/>
              <span class="promo-kind" t-esc="pr.policy_label || typeLabel(pr)"/>
            </span>
            <span class="facet-name" t-esc="shortName(pr)"/>
          </span>
          <span class="facet-caret" aria-hidden="true" t-esc="isOpen(pr) ? '▾' : '▸'"/>
        </div>
        <div class="facet-body" t-if="isOpen(pr)">
          <div class="promo-compact-meta">
            <span t-esc="participantLabel(pr)"/>
          </div>
          <!-- ESCALERA: los tramos se leen como progresión, no como
               frases sueltas. Cada peldaño muestra el rango a la
               izquierda y el beneficio a la derecha; los peldaños hasta
               el elegido quedan marcados para que se vea de un vistazo
               cuánto falta para el siguiente porcentaje. La frase
               completa sigue viva en el title (misma redacción que el
               Excel, ver _cotizador_promo_detail). -->
          <div class="promo-ladder" t-if="steps(pr).length">
            <label class="promo-step"
                   t-foreach="steps(pr)" t-as="step" t-key="step_index"
                   t-att-class="{ sel: isStepSelected(pr, step_index), reached: isStepReached(pr, step_index) }"
                   t-att-title="step.title">
              <input type="radio" t-att-name="'promo_tier_' + pr.id"
                     t-att-checked="isStepSelected(pr, step_index)"
                     t-on-click.stop="() => this.pickTier(pr, step_index)"/>
              <span class="step-body">
                <span class="step-range" t-esc="step.range"/>
                <span class="step-rule" t-if="step.rule" t-esc="step.rule"/>
                <span class="step-rims" t-if="step.rims.length">
                  <span class="step-rim" t-foreach="step.rims" t-as="rim" t-key="rim_index">
                    <t t-esc="rim.label"/> <b t-esc="rim.value"/>
                  </span>
                </span>
              </span>
              <span class="step-value" t-esc="step.value"/>
            </label>
          </div>
          <p class="facet-note" t-if="!steps(pr).length">
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

  /* ---------- Escalera: nombre, periodo y peldaños ----------
     El servidor manda `display_label` (campo cotizador_name de la
     promoción). Mientras alguna promo no lo tenga capturado se sigue
     viendo su nombre completo — nada se rompe por no llenar el campo. */
  shortName(pr) {
    return pr.display_label || pr.name || '';
  }
  // Folio/periodo que abre el nombre administrativo ("08-26 …",
  // "B/F-0801PBS …"). Se muestra aparte para que no compita con el
  // nombre; si el nombre corto ya no lo trae, no se pinta nada.
  periodChip(pr) {
    const raw = String(pr.name || '').trim();
    const match = raw.match(/^(\d{2}-\d{2}|[A-Z]\/[A-Z]-\w+)\b/);
    if (!match) return '';
    // Si el nombre corto conserva el folio, no se duplica.
    if (String(this.shortName(pr)).startsWith(match[1])) return '';
    return match[1];
  }

  /* Peldaños de la escalera. Convierte cada tramo en las piezas que
     la escalera pinta por separado (rango, regla, beneficio) en vez de
     una sola frase. `title` conserva la frase completa de tierLabel —
     misma redacción que el Excel, para que pantalla y archivo digan lo
     mismo. Memorizado por identidad de tiers: el template lo llama una
     vez por peldaño en cada render. */
  steps(pr) {
    if (!this._stepCache) this._stepCache = new Map();
    const cached = this._stepCache.get(pr.id);
    if (cached && cached.src === pr.tiers && cached.promo === pr) return cached.out;

    const whole = (value) => Math.round(Number(value || 0));
    const number = (value) => whole(value).toLocaleString('es-MX', { maximumFractionDigits: 0 });
    const percent = (value) => `${Number(value || 0).toLocaleString(
      'es-MX', { minimumFractionDigits: 0, maximumFractionDigits: 1 },
    )}%`;
    const money = (value) => `$${number(value)}`;

    let out = [];
    if (pr.promo_type === 'coupons') {
      const limit = whole(pr.coupon_limit_qty);
      out = [{
        range: 'Por producto participante',
        rule: limit > 1 ? `Tope ${number(limit)} pzas` : '',
        value: 'Cupón',
        rims: [],
        title: this.couponLabel(pr),
      }];
    } else {
      out = (pr.tiers || []).map((tier) => {
        const max = whole(tier.max || 999999999);
        const min = whole(tier.min);
        const unlimited = max >= 999999999;
        const isAmount = ['amount', 'amount_rim'].includes(pr.promo_type);
        const range = isAmount
          ? (unlimited ? `${money(min)} o más` : `${money(min)} – ${money(max)}`)
          : (unlimited ? `${number(min)}+ pzas` : `${number(min)} – ${number(max)} pzas`);

        // Regla secundaria: lo que hay que cumplir DENTRO del rango.
        let rule = '';
        if (pr.promo_type === 'monthly_volume') {
          rule = `${number(tier.minimum_products)} medidas × `
            + `${number(tier.minimum_qty_per_measure)} pzas c/u`;
        } else {
          const minQty = whole(tier.min_qty);
          if (minQty > (isAmount ? 1 : min)) rule = `Mínimo ${number(minQty)} pzas`;
        }

        // Política por rin: cada rin cobra su propio porcentaje, así que
        // no hay UN beneficio sino varios. Se listan como fichas y el
        // valor grande del peldaño es el más alto.
        const rims = (['rim_quantity', 'amount_rim'].includes(pr.promo_type))
          ? (tier.rim_discounts || []).map((row) => {
            if (pr.promo_type === 'amount_rim') {
              return {
                min: whole(row.rim_from),
                max: whole(row.rim_to),
                discount: Number(row.discount || 0),
              };
            }
            const nums = [...String(row.rims || '').matchAll(/\d+(?:\.\d+)?/g)]
              .map((m) => whole(m[0])).filter((v) => Number.isFinite(v));
            return {
              min: nums.length ? Math.min(...nums) : 0,
              max: nums.length ? Math.max(...nums) : 0,
              discount: Number(row.discount || 0),
            };
          }).filter((row) => row.min > 0).sort((a, b) => a.min - b.min)
          : [];
        const rimChips = rims.map((row, index) => ({
          label: (index === rims.length - 1 && row.min >= 16)
            ? `R${number(row.min)}+`
            : (row.min === row.max
              ? `R${number(row.min)}`
              : `R${number(row.min)}–R${number(row.max)}`),
          value: percent(row.discount),
        }));
        if (pr.promo_type === 'amount_rim' && Number(tier.key_size_discount || 0) > 0) {
          rimChips.push({ label: 'Key Sizes', value: percent(tier.key_size_discount) });
        }

        let value;
        if (pr.reward_type === 'gift_card') value = 'Tarjeta';
        else if (pr.reward_type === 'fixed_amount') value = `${money(tier.fixed_amount)} NC`;
        else if (rims.length) value = percent(Math.max(...rims.map((row) => row.discount)));
        else value = percent(tier.discount);

        return { range, rule, value, rims: rimChips, title: this.tierLabel(pr, tier) };
      });
    }
    this._stepCache.set(pr.id, { src: pr.tiers, promo: pr, out });
    return out;
  }
  isStepSelected(pr, index) {
    return this.isOn(pr) && this.tierIndex(pr) === index;
  }
  // Peldaños por debajo del elegido: se marcan para leer la escalera
  // como progresión ("ya vas en el segundo, te falta uno").
  isStepReached(pr, index) {
    return this.isOn(pr) && index < this.tierIndex(pr);
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
      amount_rim: 'Monto por Rin / Key Sizes',
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
    const whole = (value) => Math.round(Number(value || 0));
    const number = (value) => whole(value).toLocaleString(
      'es-MX', { maximumFractionDigits: 0 },
    );
    // Conservar una décima cuando exista (7.5%), sin agregar ".0"
    // a los porcentajes enteros (8%).
    const percent = (value) => `${Number(value || 0).toLocaleString(
      'es-MX', { minimumFractionDigits: 0, maximumFractionDigits: 1 },
    )}%`;
    const max = whole(tier.max || 999999999);
    const min = whole(tier.min);
    const unlimited = max >= 999999999;
    const qtyRange = unlimited
      ? `${number(min)} pzas o más`
      : `de ${number(min)} a ${number(max)} pzas`;
    const amountRange = unlimited
      ? `$${number(min)} o más`
      : `de $${number(min)} a $${number(max)}`;
    const reward = pr.reward_type === 'gift_card'
      ? 'un cupón'
      : (pr.reward_type === 'fixed_amount'
        ? `$${number(tier.fixed_amount)} en nota de crédito`
        : percent(tier.discount));

    if (pr.promo_type === 'amount') {
      const minQty = whole(tier.min_qty);
      const qtyRule = minQty > 1 ? ` (mínimo ${number(minQty)} pzas)` : '';
      return `Obtén ${reward} en compras ${amountRange}${qtyRule}.`;
    }

    if (pr.promo_type === 'amount_rim') {
      const rows = (tier.rim_discounts || []).map((row) => {
        const from = whole(row.rim_from);
        const to = whole(row.rim_to);
        if (!from) return '';
        const label = to >= 99
          ? `R${number(from)}+`
          : (from === to ? `R${number(from)}` : `R${number(from)} a R${number(to)}`);
        return `${percent(row.discount)} en ${label}`;
      }).filter(Boolean);
      if (Number(tier.key_size_discount || 0) > 0) {
        rows.push(`${percent(tier.key_size_discount)} en Key Sizes`);
      }
      return rows.length
        ? `Compras ${amountRange}: ${rows.join(' · ')}.`
        : `Compras ${amountRange}: porcentaje según el rin.`;
    }

    if (pr.promo_type === 'monthly_volume') {
      const measures = whole(tier.minimum_products);
      const perMeasure = whole(tier.minimum_qty_per_measure);
      return `Obtén ${reward} comprando ${qtyRange} `
        + `(${number(measures)} medidas × ${number(perMeasure)} pzas c/u).`;
    }

    if (pr.promo_type === 'rim_quantity') {
      const rows = (tier.rim_discounts || []).map((row) => {
        const rims = [...String(row.rims || '').matchAll(/\d+(?:\.\d+)?/g)]
          .map((match) => whole(match[0]))
          .filter((value) => Number.isFinite(value));
        return {
          min: rims.length ? Math.min(...rims) : 0,
          max: rims.length ? Math.max(...rims) : 0,
          discount: Number(row.discount || 0),
        };
      }).filter((row) => row.min > 0).sort((a, b) => a.min - b.min);
      const breakdown = rows.map((row, index) => {
        const isLastHighRange = index === rows.length - 1 && row.min >= 16;
        const rimLabel = isLastHighRange
          ? `R${number(row.min)}+`
          : (row.min === row.max
            ? `R${number(row.min)}`
            : `R${number(row.min)} a R${number(row.max)}`);
        return `${percent(row.discount)} en ${rimLabel}`;
      }).join(' y ');
      return breakdown
        ? `Obtén ${breakdown} comprando ${qtyRange}.`
        : `Obtén un porcentaje según el rin comprando ${qtyRange}.`;
    }

    const minQty = whole(tier.min_qty);
    // En políticas por cantidad, el inicio del rango ya comunica el
    // mínimo. Solo se muestra min_qty si agrega una restricción mayor.
    const qtyRule = minQty > min ? ` (mínimo ${number(minQty)} pzas)` : '';
    const quantityPurchase = unlimited ? `de ${qtyRange}` : qtyRange;
    return `Obtén ${reward} en la compra ${quantityPurchase}${qtyRule}.`;
  }
  couponLabel(pr) {
    const limit = Math.round(Number(pr.coupon_limit_qty || 0));
    return 'Obtén un cupón por cada producto participante'
      + (limit > 1 ? ` (tope ${limit} pzas).` : '.');
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
            <option t-foreach="pf.options" t-as="opt" t-key="opt" t-att-value="opt" t-esc="opt + '%'"/>
          </select>
        </div>
      </div>
    </div>`;

  profileFields = PROFILE_FIELDS;

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
              <div class="sv-row sv-detail sv-mayoreo" t-if="mayoreoSavingAmt > 0.01">
                <span class="sv-lbl">Política Mayoreo (−10%)</span>
                <span class="sv-val" t-esc="'-' + money(mayoreoSavingAmt * iva)"/>
              </div>
              <div class="sv-row sv-detail sv-promo" t-foreach="promoSavingsList" t-as="ps" t-key="ps.id">
                <span class="sv-lbl" t-attf-style="color: {{ps.color}}" t-esc="ps.name"/>
                <span class="sv-val" t-attf-style="color: {{ps.color}}" t-esc="'-' + money(ps.amount * iva)"/>
              </div>
              <div class="total-row total-row-secondary" t-if="hasPromotionDiscount">
                <span class="label">Total si cumple las condiciones <small class="iva-mode" t-esc="props.state.showIva ? '(con IVA)' : '(sin IVA)'"/></span>
                <span class="value" t-esc="money(conditionsTotal * iva)"/>
              </div>
              <div class="total-row">
                <span class="label">
                  <t t-if="hasPromotionDiscount">Total con todos los descuentos</t>
                  <t t-elif="policySavingAmt > 0.01 or mayoreoSavingAmt > 0.01">Total con política comercial</t>
                  <t t-else="">Total del pedido</t>
                  <small class="iva-mode" t-esc="props.state.showIva ? '(con IVA)' : '(sin IVA)'"/>
                </span>
                <span class="value" t-esc="money(grandTotal * iva)"/>
              </div>
              <!-- Tarjeta de regalo: va DESPUÉS del total y como línea
                   aparte, no dentro del desglose de ahorros. El cliente
                   se lleva una tarjeta por ese valor; el precio de las
                   llantas no cambia. Sumarla al ahorro haría ver un
                   total más bajo del que se va a cobrar. -->
              <div class="bonus-line giftcard-line" t-if="giftCardTotal > 0.005">
                🎁 Tarjeta de regalo<t t-if="giftCardList.length > 1"> — <t t-esc="giftCardList.length"/> promos</t>: <t t-esc="money(giftCardTotal * iva)"/>
                <small t-if="!giftCardAllActive"> · falta elegir la condición</small>
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
  // La política comercial se calcula SOBRE LISTA (totalList), no sobre
  // el precio ya rebajado por Mayoreo — igual que en el catálogo y el
  // Excel. Calcularla sobre `totalList - mayoreoSavingAmt` encadenaría
  // los dos descuentos (cascada: base×0.98) en vez de restarlos cada
  // uno por su lado desde lista (directo: lista×0.02); eso mostraba
  // -$71.70 de Política en vez de -$79.67 con Mayoreo activo. Si no
  // hay llantas de Mayoreo el resultado es idéntico al anterior.
  get policySavingAmt() {
    const pct = parseFloat(this.policyPctTotal) || 0;
    return this.totalList * (pct / 100);
  }
  get mayoreoSavingAmt() {
    if (!this.props.state.quote) return 0;
    return this.props.state.quote.lines.reduce((sum, line) => {
      const product = this.productFor(String(line.product_id));
      return sum + mayoreoUnitDiscount(product, line.unit_price || 0) * (line.qty || 0);
    }, 0);
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
        result.push({
          id: pr.id,
          name: pr.display_label || pr.name,
          amount,
          color: promoColorFor(pr.id).text,
        });
      }
    }
    return result;
  }

  /* Tarjeta de regalo del pedido: Σ (piezas × monto del código), como
     lo define docs/TARJETA_REGALO.md. Es un valor que el cliente
     RECIBE, no un descuento — por eso vive fuera de totalSavings y de
     grandTotal, en su propia línea del ticket. */
  get giftCardList() {
    const { promos, promoSim, cart } = this.props.state;
    if (!promos.length) return [];
    const result = [];
    for (const pr of promos) {
      if (pr.reward_type !== 'gift_card') continue;
      let amount = 0;
      for (const [pidStr, qty] of Object.entries(cart || {})) {
        const product = this.productFor(pidStr);
        amount += giftCardAmountFor(pr, product) * (qty || 0);
      }
      if (amount > 0.005) {
        const sel = promoSim[pr.id];
        result.push({
          id: pr.id,
          name: pr.display_label || pr.name,
          amount,
          active: !!(sel && sel.on),
        });
      }
    }
    return result;
  }
  get giftCardTotal() {
    return this.giftCardList.reduce((sum, item) => sum + item.amount, 0);
  }
  get giftCardAllActive() {
    return this.giftCardList.every((item) => item.active);
  }

  get totalList() {
    if (!this.props.state.quote) return 0;
    return this.props.state.quote.lines.reduce((s, l) => s + l.unit_price * l.qty, 0);
  }
  get totalSavings() {
    return Math.max(this.policySavingAmt + this.mayoreoSavingAmt + this.promoSavingsTotal, 0);
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
  // Mayoreo, política y promos se restan CADA UNO por su lado desde
  // lista — no en cascada. `baseTotal` (lista − Mayoreo) es el precio
  // que se cotiza; `policySavingAmt` ya sale de lista arriba, así que
  // aquí solo se resta, nunca se multiplica por `factor` (eso era la
  // cascada: base×factor = lista×(1−Mayoreo%)×(1−política%)).
  get baseTotal() {
    if (!this.props.state.quote) return 0;
    return Math.max(this.props.state.quote.order_total - this.mayoreoSavingAmt, 0);
  }
  get grandTotal() {
    if (!this.props.state.quote) return 0;
    return Math.max(this.baseTotal - this.policySavingAmt - this.promoSavingsTotal, 0);
  }
  get conditionsTotal() {
    if (!this.props.state.quote) return 0;
    return Math.max(this.baseTotal - this.policySavingAmt, 0);
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
    // La Política comercial se calcula SOBRE LISTA (no en cascada
    // sobre `base`, que ya trae Mayoreo restado); si el factor es 1.0
    // no hay descuento de política. La NC de ztyres_promo NO se resta
    // aquí — es un beneficio aparte que ya se muestra como "NC +$" por
    // línea. Mayoreo, política y promos se calculan cada uno de forma
    // independiente sobre lista y se restan juntos del precio base.
    const f = this.factor;
    if (quoteLine) {
      const list = quoteLine.unit_price || 0;
      const base = basePriceOf(product, quoteLine.final_unit_price || 0);
      const policyDisc = list * (1 - f);
      const unit = Math.max(
        base - policyDisc - this.promoDiscountPerUnit(id, list),
        0,
      );
      return {
        unitPrice: unit,
        listPrice: basePriceOf(product, list),
        hasPromo: unit < basePriceOf(product, list) - 0.005,
        subtotal: unit * qty,
        dotRange: quoteLine.dot_range,
        freeQty: quoteLine.free_qty,
      };
    }
    const list = product.price || 0;
    const base = basePriceOf(product, list);
    const policyDisc = list * (1 - f);
    const unit = Math.max(
      base - policyDisc - this.promoDiscountPerUnit(id, list),
      0,
    );
    return {
      unitPrice: unit,
      listPrice: base,
      hasPromo: unit < base - 0.005,
      subtotal: unit * qty,
      dotRange: product.dot_range,
      freeQty: product.free_qty,
    };
  };
}

/* ---------- Modal de zoom de imagen ---------- */
