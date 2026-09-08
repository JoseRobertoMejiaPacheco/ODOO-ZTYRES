/** @odoo-module **/
/* ============================================================
   Cotizador Owl · Ztyres — Arranque para la PÁGINA PÚBLICA
   ============================================================
   Esta página (controllers.py: cotizador_public_page) no corre
   dentro del webclient de Odoo, así que aquí no hay "actions" que
   la monten solas: se monta a mano con mount(), igual que antes,
   pero el Owl que se usa sigue siendo el nativo de Odoo (viene en
   el bundle web.assets_common + el bundle público de este módulo,
   cargados por la plantilla QWeb) — sin CDN externo, sin token: la
   página es pública (auth='public') y las rutas de datos
   (/ztyres_promotions/cotizador/*) son del mismo origen.
   ============================================================ */
import { mount, whenReady } from "@odoo/owl";
import { CotizadorOwlApp } from "./app.js";

whenReady(() => {
  const rootEl = document.getElementById("app-root");
  if (!rootEl) return;
  mount(CotizadorOwlApp, rootEl, { dev: false }).catch((e) => {
    console.error("Error al montar el cotizador público:", e);
    rootEl.innerHTML = '<div class="empty-state" style="padding:60px 20px;color:red;">'
      + 'Error al iniciar el cotizador: ' + e.message + '</div>';
  });
});
