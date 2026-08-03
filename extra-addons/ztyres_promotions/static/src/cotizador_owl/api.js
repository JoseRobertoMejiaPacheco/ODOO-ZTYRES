/** @odoo-module **/
/* ============================================================
   Cotizador Owl · Ztyres — Capa de datos
   Sin API key: esta app la sirve Odoo mismo (mismo origen), no es
   un cliente externo. Usa /ztyres_promotions/cotizador/* — rutas
   públicas aparte, sin autenticación, distintas de /external/* (que
   sigue siendo para el cotizador HTML/JS que vive fuera de Odoo y sí
   necesita la API key).
   ============================================================ */

async function apiGet(path) {
  const res = await fetch(path);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || ('HTTP ' + res.status));
  return data;
}

async function apiPost(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || ('HTTP ' + res.status));
  return data;
}

export function fetchCatalog() {
  return apiGet('/ztyres_promotions/cotizador/catalog');
}

// --- CLIENTE (comentado, se reactiva cuando se use) ---
// export function fetchPartners() {
//   return apiGet('/ztyres_promotions/cotizador/partners');
// }


// Promociones vigentes (ztyres_promo): nombre, tipo, rangos de
// descuento y productos que aplican — alimenta las facetas del
// panel de Promociones y el simulador de precio.
export function fetchPromos() {
  return apiGet('/ztyres_promotions/cotizador/promos');
}

export function fetchQuote(partnerId, lines) {
  return apiPost('/ztyres_promotions/cotizador/quote', { partner_id: partnerId, lines });
}

// Disponibilidad/DOT/precio al momento para una lista puntual de
// product_id — NO el catálogo completo (ver get_stock_refresh en
// product_template.py para el por qué). Se llama justo cuando el
// vendedor abre un grupo de medida, no de entrada.
export function refreshStock(productIds) {
  return apiPost('/ztyres_promotions/cotizador/stock', { product_ids: productIds });
}

export function productImageUrl(productId, big) {
  const size = big ? '?size=big' : '';
  return `/ztyres_promotions/cotizador/image/${productId}${size}`;
}
