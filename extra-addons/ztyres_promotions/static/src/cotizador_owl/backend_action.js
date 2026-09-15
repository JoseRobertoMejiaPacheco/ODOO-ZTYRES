/** @odoo-module **/
/* ============================================================
   Cotizador Owl · Ztyres — Arranque para BACKEND (uso interno)
   ============================================================
   Se registra como client action: el webclient de Odoo crea,
   monta y destruye el componente con su propio Owl nativo (mismo
   bundle que usa todo el backend), dentro de una sesión normal.
   No se incluye en el bundle público — ver public_main.js.
   ============================================================ */
import { registry } from "@web/core/registry";
import { Component, xml, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CotizadorOwlApp } from "./app.js";

/* Ocultar el menú (ver views/cotizador_owl_menus.xml, groups=
   "group_cotizador_access") solo evita que aparezca el ícono — no
   impide que alguien abra la acción directo por URL/hash si conoce
   el tag. Este wrapper hace la verificación real: consulta el grupo
   del usuario ANTES de montar el cotizador (que sí carga catálogo,
   precios y clientes) y, si no pertenece, muestra un aviso en vez de
   los datos. Se resuelve una sola vez por apertura, no en cada
   render. */
class CotizadorAccessGuard extends Component {
  static template = xml`
    <div class="o_ztyres_cotizador" t-if="state.checked">
      <t t-if="state.allowed">
        <CotizadorOwlApp/>
      </t>
      <div class="empty-state" t-else="" style="padding:60px 20px;">
        <div class="empty-state-title">No tienes permiso para ver el Cotizador</div>
        <p class="empty-state-hint">
          Esta app es de acceso restringido. Si necesitas usarla, pide a un
          administrador que te agregue al grupo "Cotizador: acceso a la app
          de precios" desde Ajustes &gt; Usuarios y Compañías.
        </p>
      </div>
    </div>`;
  static components = { CotizadorOwlApp };

  setup() {
    this.user = useService("user");
    this.state = useState({ checked: false, allowed: false });
    onWillStart(async () => {
      this.state.allowed = await this.user.hasGroup("ztyres_promotions.group_cotizador_access");
      this.state.checked = true;
    });
  }
}

registry.category("actions").add("ztyres_promotions.cotizador", CotizadorAccessGuard);
