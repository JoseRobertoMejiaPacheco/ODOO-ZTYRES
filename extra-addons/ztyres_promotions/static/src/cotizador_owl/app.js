/** @odoo-module **/
/* ============================================================
   Cotizador Owl · Ztyres — App raíz
   ============================================================

   Owl nativo de Odoo 16 — sin CDN, sin script IIFE, sin token.
   Este archivo solo define el COMPONENTE; quién lo arranca depende
   de dónde se use:
     - backend_action.js  → lo registra como client action (uso
       interno, dentro del webclient, con sesión).
     - public_main.js     → lo monta directo sobre un <div id="app-root">
       en la página pública (sin sesión), ver controllers.py.
   Ambos arranques usan el mismo Owl nativo del bundle de Odoo: la
   diferencia es solo en qué bundle se cargan (assets_backend vs el
   bundle público de este módulo).
   ============================================================ */
import { Component, useState, xml, onWillStart } from "@odoo/owl";

import {
  CatalogTable, TableFilters, PromoStrip, ClientPanel, OrderPanel, IvaToggle,
} from "./components.js";
import { fetchCatalog, fetchPromos, fetchQuote } from "./api.js";
// import { fetchPartners } from "./api.js";  // Cliente desactivado
import { getSFFilters, setSFFilters, getPromoSim, setPromoSim, policyFactor, policyLabel, getShowIva, IVA_RATE, lockScroll, unlockScroll, money, FOOTER_BRANDS } from "./constants.js";

/* Mostrar imágenes de producto — apagado por defecto, igual que en
   el cotizador externo. Cámbialo a 'true' aquí mismo para activarlo;
   no requiere nada más (la ruta /ztyres_promotions/cotizador/image/<id>
   ya existe en este módulo). */


export class CotizadorOwlApp extends Component {
  static template = xml`
    <div class="o_ztyres_cotizador">
      <div class="wrap">
        <div class="error-box" t-if="state.connError" t-esc="state.connError"/>

        <div class="stack" t-if="state.loaded">
          <!-- Barra superior de una sola fila (envuelve en pantallas
               angostas): título + Política comercial + buscador.
               Antes eran tres bloques apilados — en laptops de 13-15"
               se comían un tercio de la pantalla antes de ver una
               sola llanta. -->
          <header class="app-topbar">
            <div class="page-title">
              <span class="page-title-icon" aria-hidden="true">🏷️</span>
              <div>
                <h1>Lista de Precios</h1>
              </div>
            </div>

            <div class="global-search">
              <span class="global-search-icon" aria-hidden="true">🔍</span>
              <input type="text" placeholder="Buscar marca, modelo o medida (195/65 R15, 195-65-15, 195 65 15)..." t-model="state.search"/>
            </div>

            <ClientPanel state="state" onCalculate="calculate"/>

          </header>

          <!-- Con todo en una sola columna, el Pedido ya no queda
               siempre a la vista como antes (columna lateral fija) —
               esta barra lo compensa: aparece en cuanto hay algo en
               el carrito y sigue pegada arriba mientras se recorre
               la tabla, sin tapar contenido. Solo existe en pantallas
               angostas: en escritorio el Pedido vive fijo a la
               derecha (ver .main-grid). -->
          <div class="cart-bar" t-if="cartCount">
            <span class="cart-bar-info">
              🧾 <b t-esc="cartCount"/> producto<t t-if="cartCount != 1">s</t>
              · <b t-esc="cartPieces"/> pieza<t t-if="cartPieces != 1">s</t>
              <t t-if="state.quote"> · <b t-esc="money(state.quote.order_total * policyFactorValue * ivaFactor)"/></t>
            </span>
            <button type="button" class="cart-bar-btn" t-on-click="scrollToOrder">Ver pedido ↓</button>
          </div>

          <!-- SPA de tres zonas (escritorio): Promociones a la
               izquierda (tarjetas chicas de 2 en 2), el catálogo al
               centro con todo el ancho disponible, el Pedido SIEMPRE
               a la vista a la derecha (sticky, con su propio scroll).
               Abajo de 1100px colapsa a una sola columna en el orden
               catálogo → promos → pedido, y ahí la barra flotante
               "Ver pedido ↓" vuelve a hacer su trabajo. -->
          <div class="main-grid">
            <aside class="side-col side-left">
              <PromoStrip state="state"/>
            </aside>

            <section class="center-col">
              <div class="panel catalog-panel">
                <div class="filters-row">
                  <TableFilters state="state" onChange="onFiltersChanged"/>
                  <IvaToggle state="state"/>
                  <button type="button" class="btn-download btn-download-filters"
                          t-att-class="{ 'is-loading': state.xlsxLoading === 'list' }"
                          t-att-disabled="state.xlsxLoading === 'list'"
                          t-on-click="() => this.downloadXlsx('list')"
                          title="Descarga únicamente los productos filtrados con la promoción y política seleccionadas">
                    <t t-if="state.xlsxLoading === 'list'">⏳ Generando...</t>
                    <t t-else="">📥 Descargar lista de precios</t>
                  </button>
                </div>
                <div class="table-scroll">
                  <CatalogTable state="state" showImages="showImages"
                                onAdd="addToCart" onInc="increment" onDec="decrement" onSetQty="setQty"/>
                </div>
              </div>
            </section>

            <aside class="side-col side-right" id="orderPanelAnchor">
              <OrderPanel state="state" onRemove="removeFromCart" onSetQty="setQty" onCalculate="calculate" onDownloadXlsx="() => this.downloadXlsx('order')"/>
            </aside>
          </div>
        </div>
      </div>

      <footer class="op6">
        <div class="marquee-track">
          <div class="marquee-inner">
            <span class="chip" t-foreach="footerBrands" t-as="b" t-key="b.file + '_1'">
              <img t-att-src="b.img" alt=""/>
            </span>
            <!-- se repite para el loop continuo -->
            <span class="chip" t-foreach="footerBrands" t-as="b" t-key="b.file + '_2'">
              <img t-att-src="b.img" alt=""/>
            </span>
          </div>
        </div>
      </footer>

      <!-- Toast de "producto agregado" — confirma que el click sí
           funcionó aunque el Pedido esté lejos en la pantalla. -->
      <div class="add-toast" t-if="state.toast">
        <span class="add-toast-icon" aria-hidden="true">✓</span>
        <span>Agregado: <b t-esc="state.toast"/></span>
      </div>
    </div>`;
  static components = { PromoStrip, ClientPanel, TableFilters, CatalogTable, OrderPanel, IvaToggle };
  footerBrands = FOOTER_BRANDS;
  money = money;

  get ivaFactor() {
    return this.state.showIva ? 1 + IVA_RATE : 1;
  }
  get policyFactorValue() {
    return policyFactor(this.state.profile);
  }
  get policyTextValue() {
    return policyLabel(this.state.profile);
  }

  /* Descarga XLSX: arma el estado completo y hace POST al backend,
     que responde con el archivo. Uso fetch + blob para poder pedir el
     archivo con las cookies de sesión y luego forzar la descarga
     nombrándolo desde el header Content-Disposition. */
  downloadXlsx = async (kind) => {
    // Ni la lista ni el pedido exigen cliente por ahora — cuando no
    // haya, se descargan con Cliente/RFC en blanco. El pedido solo
    // exige que haya llantas en el carrito.
    if (kind === 'order' && !Object.keys(this.state.cart).length) {
      alert('El pedido está vacío.');
      return;
    }
    const payload = {
      partner_id: this.state.selectedPartnerId || 0,
      profile: this.state.profile,
      promo_sim: this.state.promoSim,
      show_iva: this.state.showIva,
      cart: this.state.cart,
      search: this.state.search,
      sf_filters: this.state.sfFilters,
    };
    this.state.xlsxLoading = kind;
    try {
      const resp = await fetch(`/ztyres_promotions/cotizador/download/${kind}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error(await resp.text());
      const blob = await resp.blob();
      const cd = resp.headers.get('Content-Disposition') || '';
      const match = cd.match(/filename=\"([^\"]+)\"/);
      const filename = match ? match[1] : `cotizador_${kind}.xlsx`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert('No se pudo generar la descarga: ' + (err.message || err));
    } finally {
      this.state.xlsxLoading = null;
    }
  };

  // --- CLIENTE (comentado, se reactiva cuando se use) ---
  // get selectedPartnerName() {
  //   const p = this.state.partners.find((x) => String(x.id) === String(this.state.selectedPartnerId));
  //   return p ? p.name : '';
  // }


  get cartCount() {
    return Object.keys(this.state.cart).length;
  }
  // Piezas totales (suma de cantidades) — se usa en la barra
  // flotante junto al conteo de productos distintos.
  get cartPieces() {
    return Object.values(this.state.cart).reduce((s, q) => s + (q || 0), 0);
  }

  // Scroll suave hasta el Pedido — así la barra flotante sirve para
  // algo más que solo avisar "tienes cosas en el carrito": también
  // es el atajo para llegar ahí sin desplazarse a mano por toda la
  // tabla del catálogo (que ahora, a lo ancho completo, puede ser
  // bastante larga).
  scrollToOrder = () => {
    const el = document.getElementById('orderPanelAnchor');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  setup() {
    this.state = useState({
      loaded: false,
      connError: '',
      catalog: [],
      partners: [],
      promos: [],
      promoSim: getPromoSim(),
      showIva: getShowIva(),
      partnerId: null,
      profile: { volumen: '0', logistico: '0', financiero: '0' },
      cart: {},
      sfFilters: getSFFilters(),
      visibleColumns: [],
      search: '',
      quote: null,
      quoteLoading: false,
      quoteError: '',
      toast: null,
      // 'list' | 'order' | null — qué descarga de Excel está en curso
      // ahorita, para poder deshabilitar el botón correspondiente y
      // mostrar "Generando..." mientras se arma el archivo en el
      // servidor (puede tardar unos segundos y antes no había ninguna
      // señal de que el clic sí se había registrado).
      xlsxLoading: null,
    });

    onWillStart(async () => {
      try {
        const [catalog, promos] = await Promise.all([
          fetchCatalog(),
          // Las promos son opcionales: si ztyres_promo no está o la
          // ruta falla, el cotizador arranca igual, sin facetas.
          fetchPromos().catch(() => []),
        ]);
        this.state.catalog = catalog;
        this.state.promos = promos || [];
        // Limpia selecciones guardadas de promos que ya no están
        // vigentes (venció la promo, se canceló, etc.).
        const validIds = new Set((promos || []).map((p) => String(p.id)));
        let promoSelectionChanged = false;
        Object.keys(this.state.promoSim).forEach((k) => {
          const promo = (promos || []).find((item) => String(item.id) === String(k));
          const selection = this.state.promoSim[k];
          const staleAuto = promo
            && ['rim_quantity', 'monthly_volume', 'amount_rim'].includes(promo.promo_type)
            && selection && selection.auto && selection.tier == null;
          if (!validIds.has(String(k)) || staleAuto) {
            delete this.state.promoSim[k];
            promoSelectionChanged = true;
          }
        });
        if (promoSelectionChanged) setPromoSim(this.state.promoSim);
        this.state.loaded = true;
      } catch (e) {
        this.state.connError = `No se pudo cargar el catálogo: ${e.message}`;
      }
    });

    // Temporizador del cálculo automático (no es parte de state: no
    // necesita re-render, y si viviera en state cada cambio suyo
    // dispararía un ciclo extra de Owl sin ningún beneficio).
    this._calcTimer = null;
    this._loadingTimer = null;
    this._toastTimer = null;
  }

  // Arrow functions (no métodos de clase normales): estas se pasan
  // como props a componentes hijos (onAdd, onInc, onChange, etc.) y
  // se invocan ahí como funciones sueltas, no como this.metodo() —
  // con un método normal eso pierde el 'this' y truena al tocar
  // this.state. Como arrow function de clase, el 'this' queda fijo
  // al instanciarse, sin importar cómo se llamen después.
  onFiltersChanged = () => {
    setSFFilters(this.state.sfFilters);
  };

  // Confirmación visual al agregar — el catálogo puede estar muy
  // lejos del Pedido en la pantalla (150 líneas de por medio), así
  // que sin esto no había ninguna señal de que el click sí funcionó.
  // Se reinicia el timer en cada nuevo agregado en vez de apilar
  // timers sueltos, para que agregar varias cosas seguido no deje
  // timers viejos cerrando el toast antes de tiempo.
  showAddedToast = (id) => {
    const p = this.state.catalog.find((x) => String(x.product_id) === String(id));
    this.state.toast = p ? `${p.brand} ${p.name}` : 'Producto agregado';
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => { this.state.toast = null; }, 2200);
  };

  addToCart = (id) => {
    this.state.cart[id] = 1;
    this.showAddedToast(id);
    this.scheduleCalculate();
  };
  increment = (id) => {
    this.state.cart[id] = (this.state.cart[id] || 0) + 1;
    this.scheduleCalculate();
  };
  decrement = (id) => {
    const q = (this.state.cart[id] || 0) - 1;
    if (q > 0) this.state.cart[id] = q; else delete this.state.cart[id];
    this.scheduleCalculate();
  };
  // Capturar la cantidad directo (en vez de solo +/-). 0 o vacío/inválido
  // quita la llanta del carrito, igual que llegar a 0 con el botón "-".
  setQty = (id, qty) => {
    const n = parseInt(qty, 10);
    if (!n || n < 1) {
      delete this.state.cart[id];
    } else {
      this.state.cart[id] = n;
    }
    this.scheduleCalculate();
  };

  removeFromCart = (id) => {
    delete this.state.cart[id];
    this.scheduleCalculate();
  };


  // El botón "Calcular" llama a esto directo, sin espera, para
  // feedback inmediato. Los cambios de carrito (agregar/+/-/quitar)
  // pasan por scheduleCalculate en vez de llamar esto directo: así,
  // si el usuario le da varias veces rápido al + o al -, no se manda
  // una petición al servidor por cada clic — solo se calcula una vez,
  // 300ms después del último cambio.
  scheduleCalculate = () => {
    clearTimeout(this._calcTimer);
    this._calcTimer = setTimeout(() => this.calculate(), 300);
  };

  calculate = async () => {
    const lines = Object.entries(this.state.cart).map(([id, qty]) => ({ product_id: parseInt(id), qty }));
    if (!lines.length) {
      // Carrito vacío (se quitó la última llanta): limpiar cualquier
      // resultado/error previo en vez de dejarlo mostrando un cálculo
      // que ya no corresponde a lo que hay en el carrito.
      clearTimeout(this._loadingTimer);
      this.state.quote = null;
      this.state.quoteError = '';
      this.state.quoteLoading = false;
      return;
    }
    this.state.quoteError = '';
    // El "efecto fantasma" / parpadeo del total era esto: como el
    // cálculo casi siempre responde en pocos milisegundos,
    // quoteLoading se prendía y apagaba tan rápido que solo se veía
    // un destello de "Calculando...". Con este pequeño retraso, el
    // indicador solo aparece si de verdad se está tardando más de lo
    // normal; si la respuesta es rápida (el caso normal), nunca
    // llega a mostrarse y el total se siente instantáneo.
    clearTimeout(this._loadingTimer);
    this._loadingTimer = setTimeout(() => { this.state.quoteLoading = true; }, 220);
    try {
      this.state.quote = await fetchQuote(this.state.partnerId, lines);
    } catch (e) {
      this.state.quoteError = `Error al calcular: ${e.message}`;
      this.state.quote = null;
    } finally {
      clearTimeout(this._loadingTimer);
      this.state.quoteLoading = false;
    }
  };
}

/* ── Arranque ──────────────────────────────────────────────────────
   Ver backend_action.js (uso interno) y public_main.js (página
   pública) — cada uno importa esta clase y decide cómo arrancarla.
──────────────────────────────────────────────────────────────────── */
