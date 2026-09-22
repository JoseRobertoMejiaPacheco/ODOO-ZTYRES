/** @odoo-module **/

import { Component, useState, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";

class GlobalPaymentWidget extends Component {
    setup() {
        this.state = useState({ expanded: {} });
    }

    toggleExpand(id) {
        this.state.expanded[id] = !this.state.expanded[id];
    }
}

GlobalPaymentWidget.template = xml/* xml */`
  <div class="o_global_payment_widget">
    <t t-foreach="props.record.data.global_payment_lines" t-as="line" t-index="line_index" t-key="line.id || line_index">
      <div class="line">
        <div>
          <strong t-on-click="toggleExpand.bind(this, line.id)">
            [Factura] 
            <t t-if="line.move_id">
              <t t-esc="line.move_id.display_name"/> - 
            </t>
            Total: <t t-esc="line.move_amount_total"/>
          </strong>
        </div>
        <t t-if="state.expanded[line.id]">
          <div class="ml-3">
            <t t-if="line.payment_form_id">
              <t t-foreach="line.payment_form_id" t-as="form" t-index="form_index" t-key="form.id || form_index">
                <div class="form">
                  <strong t-on-click="toggleExpand.bind(this, form.id)">
                    [Formulario] 
                    <t t-if="form.amount_residual != null">
                      Saldo: <t t-esc="form.amount_residual"/>
                    </t>
                  </strong>
                  <t t-if="state.expanded[form.id]">
                    <div class="ml-3">
                      <t t-if="form.payment_ids">
                        <t t-foreach="form.payment_ids" t-as="payment" t-index="payment_index" t-key="payment.id || payment_index">
                          <div class="payment">
                            <strong t-on-click="toggleExpand.bind(this, payment.id)">
                              [Pago] 
                              <t t-if="payment.payment_name">
                                <t t-esc="payment.payment_name"/> - 
                              </t>
                              <t t-if="payment.amount_to_apply != null">
                                <t t-esc="payment.amount_to_apply"/>
                              </t>
                            </strong>
                            <t t-if="state.expanded[payment.id]">
                              <ul class="ml-4">
                                <t t-if="payment.move_detailed_line_ids">
                                  <t t-foreach="payment.move_detailed_line_ids" t-as="line_detail" t-index="detail_index" t-key="line_detail.id || detail_index">
                                    <li>
                                      <t t-if="line_detail.name"><t t-esc="line_detail.name"/>: </t>
                                      <t t-if="line_detail.amount_taxed != null">
                                        <t t-esc="line_detail.amount_taxed"/>
                                      </t>
                                    </li>
                                  </t>
                                </t>
                              </ul>
                            </t>
                          </div>
                        </t>
                      </t>
                    </div>
                  </t>
                </div>
              </t>
            </t>
          </div>
        </t>
      </div>
    </t>
  </div>
`;

registry.category("fields").add("global_payment_widget", GlobalPaymentWidget);
