/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const { Component } = owl;

export class PriorityTenField extends Component {
    static template = "z_helpdesk.PriorityTenField";
    static props = { ...standardFieldProps };

    get stars() {
        return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
    }

    get value() {
        return parseInt(this.props.record.data[this.props.name] || "5", 10);
    }

    get label() {
        const labels = {
            1: "Informativa",
            2: "Muy baja",
            3: "Baja",
            4: "Limitada",
            5: "Media",
            6: "Relevante",
            7: "Alta",
            8: "Muy alta",
            9: "Crítica",
            10: "Emergencia",
        };
        return `${this.value} - ${labels[this.value] || "Media"}`;
    }

    async setPriority(level) {
        if (this.props.readonly) {
            return;
        }
        await this.props.record.update({ [this.props.name]: String(level) });
    }
}

registry.category("fields").add("priority_ten", PriorityTenField);
