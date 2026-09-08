/** @odoo-module **/
/* ============================================================
   Cotizador Owl · Ztyres — Constantes y helpers
   ============================================================ */

/* Columnas OPCIONALES (selector "Columnas"). Cara y Equipo original
   ya NO viven aquí: según el layout del Excel (Libro12), "Cap/Cara"
   es una columna fija combinada (capas-cara, ej. "04-N") y
   "Eq. Original" es columna fija propia — ver CatalogTable. */
export const EXTRA_COLUMNS = [];

export const SF_FIELDS = [
  { key: 'brand', label: 'Marca' },
  { key: 'tier', label: 'Tier' },
  { key: 'segment', label: 'Segmento' },
  { key: 'type', label: 'Tipo' },
  { key: 'model', label: 'Modelo' },
];

/* Política comercial: cada categoría tiene únicamente sus porcentajes
   autorizados. El 0% permite indicar que esa categoría no aplica. */
export const PROFILE_FIELDS = [
  { key: 'volumen', label: 'Volumen', options: ['0', '1', '2', '3'] },
  { key: 'logistico', label: 'Logístico', options: ['0', '2', '4'] },
  { key: 'financiero', label: 'Financiero', options: ['0', '2', '3'] },
];

export const NATIONALITY_LABELS = {
  national: 'Nacional',
  imported: 'Importado',
  'national/imported': 'Nacional/Importado',
};

const IMG = '/ztyres_promotions/static/src/cotizador_owl/img/';


/* Marcas que se muestran en la marquesina del footer (scroll infinito
   de logos). Solo es decorativo/informativo — no tiene relación con
   PROMOS ni con el motor de promociones. */
export const FOOTER_BRANDS = [
  'bridgestone', 'continental', 'dunlop', 'firestone', 'goodyear',
  'kumho', 'maxxis', 'nexen', 'pirelli', 'aptany', 'jinyu_real',
].map((file) => ({ file, img: IMG + file + '.png' }));

export const money = (n) =>
  '$' + Number(n || 0).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/* DOT compacto: "2025-2026" / "24-26" / "2025" → "25/26", "24/26",
   "25". Se quedan solo los últimos 2 dígitos de cada año y se unen
   con "/" — el rango completo sigue disponible en el title (tooltip)
   de la celda para quien necesite confirmar el año exacto. */
export function formatDot(v) {
  if (!v || v === 'N/A') return 'N/A';
  const years = String(v).match(/\d{2,4}/g);
  if (!years) return String(v);
  return [...new Set(years.map((y) => y.slice(-2)))].join('/');
}

export function formatColumnValue(key, value) {
  if (key === 'weight') {
    // Antes caía en el check genérico de abajo (value === 0 ->
    // '—'), igual que cualquier atributo sin dato — por eso "no se
    // veía": casi ninguna llanta tiene peso capturado en Odoo, así
    // que TODAS mostraban el mismo guion ambiguo de siempre, se
    // confundía con "no existe esta columna". Ahora es explícito.
    return value ? `${value} kg` : 'Sin peso registrado';
  }
  if (value === undefined || value === null || value === '' || value === 0) return '—';
  if (key === 'floor_depth') return `${value} mm`;
  if (key === 'product_nationality') return NATIONALITY_LABELS[value] || value;
  return value;
}

/* No todo mundo escribe la medida igual (195/65 R15, 195-65-15,
   195 65 15, etc.) — esto las deja a todas en una misma "forma
   esqueleto" para poder compararlas sin importar qué separador usó
   quien escribió. Se usa tanto para lo que el usuario escribe en el
   buscador como para el texto del catálogo contra el que se compara
   (ver CatalogTree.filtered en components.js). */
export function normalizeSearchText(s) {
  return String(s || '')
    .toLowerCase()
    .replace(/[\s\-/.]+/g, '')
    .replace(/r(?=\d)/g, '');
}

export function getVisibleColumns() {
  const valid = EXTRA_COLUMNS.map((c) => c.key);
  try {
    const raw = localStorage.getItem('ztyres_catalog_columns');
    // null = primera vez en este navegador: las opcionales arrancan
    // apagadas (Cara y Eq. Original ya son columnas fijas de la
    // tabla, no opcionales). El filter limpia claves guardadas de
    // versiones anteriores ('face', 'original_equipment') que ya no
    // existen como opcionales — sin él, quedarían "prendidas" en
    // localStorage sin ninguna casilla en el selector para apagarlas.
    if (raw === null) return [];
    return JSON.parse(raw).filter((k) => valid.includes(k));
  }
  catch (e) { return []; }
}
export function setVisibleColumns(cols) {
  localStorage.setItem('ztyres_catalog_columns', JSON.stringify(cols));
}

/* Selección del simulador de promos ({promoId: {on, tier}}) — se
   recuerda por navegador, igual que filtros y columnas. */
/* IVA (16% MX) — SOLO PARA MOSTRAR. Todo el sistema (catálogo,
   quote, promos, NC) trabaja y persiste SIN IVA; este factor se
   aplica únicamente al pintar montos cuando el vendedor activa
   "Con IVA". Nunca viaja al servidor. */
export const IVA_RATE = 0.16;

/* Paleta de colores para las promociones — 10 tonos escogidos a
   mano por su distancia PERCEPTUAL (no solo angular en HSL): entre
   dos promos consecutivas del catálogo nunca hay "otro tono del
   mismo color". El orden ROMPE el ciclo natural del hue para que
   ids vecinos (1, 2, 3…) caigan en colores completamente distintos:
   rojo → verde → azul → naranja → violeta → teal → magenta → oliva
   → índigo → coral. */
const PROMO_COLORS = [
  { text: 'hsl(355, 72%, 40%)', tint: 'hsl(355, 82%, 93%)', border: 'hsl(355, 70%, 55%)' }, // rojo
  { text: 'hsl(140, 62%, 30%)', tint: 'hsl(140, 60%, 90%)', border: 'hsl(140, 55%, 45%)' }, // verde
  { text: 'hsl(215, 75%, 42%)', tint: 'hsl(215, 82%, 93%)', border: 'hsl(215, 70%, 58%)' }, // azul
  { text: 'hsl( 28, 80%, 40%)', tint: 'hsl( 28, 85%, 91%)', border: 'hsl( 28, 78%, 55%)' }, // naranja
  { text: 'hsl(275, 55%, 42%)', tint: 'hsl(275, 65%, 93%)', border: 'hsl(275, 55%, 60%)' }, // violeta
  { text: 'hsl(180, 60%, 30%)', tint: 'hsl(180, 55%, 90%)', border: 'hsl(180, 55%, 45%)' }, // teal
  { text: 'hsl(325, 65%, 42%)', tint: 'hsl(325, 75%, 93%)', border: 'hsl(325, 62%, 60%)' }, // magenta
  { text: 'hsl( 65, 55%, 30%)', tint: 'hsl( 65, 60%, 88%)', border: 'hsl( 65, 55%, 45%)' }, // oliva
  { text: 'hsl(245, 55%, 45%)', tint: 'hsl(245, 65%, 93%)', border: 'hsl(245, 55%, 60%)' }, // índigo
  { text: 'hsl(  8, 65%, 42%)', tint: 'hsl(  8, 75%, 92%)', border: 'hsl(  8, 65%, 58%)' }, // coral
];
export function promoColorFor(id) {
  const n = parseInt(id, 10) || 0;
  return PROMO_COLORS[((n % PROMO_COLORS.length) + PROMO_COLORS.length) % PROMO_COLORS.length];
}
export function getShowIva() {
  return localStorage.getItem('ztyres_show_iva') === '1';
}
export function setShowIva(on) {
  localStorage.setItem('ztyres_show_iva', on ? '1' : '0');
}

export function getPromoSim() {
  try { return JSON.parse(localStorage.getItem('ztyres_promo_sim') || '{}'); }
  catch (e) { return {}; }
}
export function setPromoSim(sim) {
  localStorage.setItem('ztyres_promo_sim', JSON.stringify(sim));
}

/* Factor de la Política comercial: los tres descuentos del cliente
   (Volumen/Logístico/Financiero) se SUMAN y el total se aplica una
   sola vez sobre el precio de lista — 2% + 4% + 5% = 11% de
   descuento directo (NO en cascada). 1.0 = sin descuento; se acota
   en 0 por si algún día los porcentajes sumaran más de 100. */
export function policyFactor(profile) {
  const pct = (k) => parseFloat(profile && profile[k]) || 0;
  const total = pct('volumen') + pct('logistico') + pct('financiero');
  return Math.max(0, 1 - total / 100);
}
export function policyLabel(profile) {
  const parts = [];
  ['volumen', 'logistico', 'financiero'].forEach((k) => {
    const v = parseFloat(profile && profile[k]) || 0;
    if (v > 0) parts.push(k.charAt(0).toUpperCase() + k.slice(1) + ' −' + v + '%');
  });
  return parts.join(' · ');
}

export function getSFFilters() {
  try {
    const saved = JSON.parse(localStorage.getItem('ztyres_sf_filters') || '{}');
    const allowed = new Set(SF_FIELDS.map((field) => field.key));
    return Object.fromEntries(
      Object.entries(saved).filter(([key, values]) => allowed.has(key) && Array.isArray(values) && values.length),
    );
  }
  catch (e) { return {}; }
}
export function setSFFilters(f) {
  localStorage.setItem('ztyres_sf_filters', JSON.stringify(f));
}

/* ---------- Bloqueo de scroll de fondo mientras hay un modal abierto ----------
   En la página pública, el que hace scroll es <body>. En el backend
   de Odoo, .o_ztyres_cotizador hace su propio scroll interno (ver el
   overflow-y:auto del contenedor raíz). Sin esto, en celular se podía
   ver/mover el contenido de atrás detrás del modal (la "imagen de
   fondo" se quedaba visible) porque ese contenido seguía pudiendo
   desplazarse aunque el modal estuviera encima. Un contador en vez de
   un simple true/false: si llegan a abrirse dos modales a la vez
   (ej. uno desde el otro), el scroll no se desbloquea de más hasta
   que se cierre el último.

   También se agrega/quita la clase "modal-open" en el contenedor
   raíz: hay celdas con position:sticky en la tabla del catálogo
   (Producto/Precio/Agregar, para que no se pierdan al hacer scroll
   horizontal) y en ciertos anchos "móviles" (tablets, celulares en
   horizontal, ancho >760px pero con el menú ya colapsado) esas
   celdas siguen siendo sticky. Es un bug conocido de WebKit/Chrome
   móvil: un elemento sticky puede quedar en su propia capa de
   composición que "se filtra" por encima de un modal con position:
   fixed, sin importar el z-index — justo la imagen seleccionada se
   quedaba visible encima del modal. La solución confiable es apagar
   el sticky (ver CSS .modal-open) mientras el modal está abierto. */
let _scrollLockCount = 0;
export function lockScroll() {
  _scrollLockCount++;
  if (_scrollLockCount > 1) return;
  document.body.style.overflow = 'hidden';
  const root = document.querySelector('.o_ztyres_cotizador');
  if (root) {
    root.style.overflow = 'hidden';
    root.classList.add('modal-open');
  }
}
export function unlockScroll() {
  _scrollLockCount = Math.max(0, _scrollLockCount - 1);
  if (_scrollLockCount > 0) return;
  document.body.style.overflow = '';
  const root = document.querySelector('.o_ztyres_cotizador');
  if (root) {
    root.style.overflow = '';
    root.classList.remove('modal-open');
  }
}
