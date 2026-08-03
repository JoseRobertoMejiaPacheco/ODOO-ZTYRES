/** @odoo-module **/
/* ============================================================
   Cotizador Owl · Ztyres — Íconos
   Cada ícono es su propio componente Owl (en vez de strings SVG
   sueltos con t-out) — así el template queda declarativo y no hay
   que inyectar HTML crudo en ningún lado.

   Owl nativo: lo trae el propio Odoo 16 (no se carga desde CDN ni
   se referencia como global `owl`).
   ============================================================ */
import { Component, xml } from "@odoo/owl";

export class IconPlus extends Component {
  static template = xml`
    <svg class="btn-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round">
      <line x1="12" y1="4" x2="12" y2="20"/><line x1="4" y1="12" x2="20" y2="12"/>
    </svg>`;
}

export class IconMinus extends Component {
  static template = xml`
    <svg class="btn-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round">
      <line x1="4" y1="12" x2="20" y2="12"/>
    </svg>`;
}

export class IconCheck extends Component {
  static template = xml`
    <svg class="btn-icon" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="4 13 9 18 20 6"/>
    </svg>`;
}

export class IconX extends Component {
  static template = xml`
    <svg class="btn-icon" width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.6" stroke-linecap="round">
      <line x1="5" y1="5" x2="19" y2="19"/><line x1="19" y1="5" x2="5" y2="19"/>
    </svg>`;
}

export class IconZoom extends Component {
  static template = xml`
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.5" y2="16.5"/>
      <line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/>
    </svg>`;
}

export class IconTrash extends Component {
  static template = xml`
    <svg class="btn-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="3 6 5 6 21 6"/>
      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
      <line x1="10" y1="11" x2="10" y2="17"/>
      <line x1="14" y1="11" x2="14" y2="17"/>
    </svg>`;
}

export class IconNoImage extends Component {
  static template = xml`
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/>
    </svg>`;
}
