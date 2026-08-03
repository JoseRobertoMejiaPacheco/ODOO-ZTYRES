/** @odoo-module **/
/**
 * dashboard_reservas/static/src/js/dashboard.js
 *
 * Mejoras opcionales de cliente para el Dashboard Reservas.
 * Agrega un encabezado de resumen (estadísticas rápidas) encima de la lista.
 */

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onMounted } from "@odoo/owl";

patch(ListController.prototype, "dashboard_reservas.ListController", {
    setup() {
        this._super(...arguments);

        // Solo aplicar en el modelo dashboard.reservas
        if (this.props.resModel !== "dashboard.reservas") return;

        this.orm = useService("orm");

        onMounted(async () => {
            await this._renderReservasStats();
        });
    },

    async _renderReservasStats() {
        try {
            const result = await this.orm.call(
                "dashboard.reservas",
                "get_dashboard_data",
                [],
                {}
            );
            const stats = result.stats;
            const isManager = result.is_manager;

            const container = this.el?.querySelector(".o_list_renderer");
            if (!container) return;

            // Evitar duplicados
            const existing = this.el.querySelector(".reservas-stats-bar");
            if (existing) existing.remove();

            const bar = document.createElement("div");
            bar.className = "reservas-stats-bar d-flex gap-3 p-2 mb-2 bg-light rounded border";
            bar.innerHTML = `
                <span class="badge bg-secondary fs-6">
                    📦 Total: <strong>${stats.total}</strong>
                </span>
                <span class="badge bg-danger fs-6">
                    🔴 Críticos ≥30d: <strong>${stats.criticos}</strong>
                </span>
                <span class="badge bg-warning text-dark fs-6">
                    🟡 Alerta 15-29d: <strong>${stats.alerta}</strong>
                </span>
                <span class="badge bg-success fs-6">
                    🟢 Normales &lt;15d: <strong>${stats.normales}</strong>
                </span>
                ${isManager ? `<span class="badge bg-info text-dark fs-6 ms-auto">👁 Vista: Todos los vendedores</span>` : `<span class="badge bg-primary fs-6 ms-auto">👤 Vista: Mis pedidos</span>`}
            `;

            container.insertAdjacentElement("beforebegin", bar);
        } catch (e) {
            // Silencioso si falla — no rompe la vista
            console.warn("Dashboard Reservas stats:", e);
        }
    },
});
