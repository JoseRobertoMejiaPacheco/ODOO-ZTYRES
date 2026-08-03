/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted, onWillUnmount, xml } from "@odoo/owl";

const TEMPLATE = xml`
<div class="o_pend_fact">

    <div class="pf-topbar">
        <h1>Pendiente de facturar</h1>
        <div class="pf-topbar-right">
            <t t-if="state.autoRefresh">
                <span class="pf-badge" t-att-class="state.paused ? 'pf-badge pf-badge-paused' : 'pf-badge'">
                    <t t-if="!state.paused"><span class="pf-pulse"/></t>
                    <t t-esc="formatCountdown(state.countdown)"/>s
                </span>
                <button class="pf-btn" t-on-click="togglePause">
                    <t t-if="state.paused">Reanudar</t><t t-else="">Pausar</t>
                </button>
            </t>
            <t t-else="">
                <span class="pf-badge pf-badge-manual">Modo manual</span>
                <button class="pf-btn" t-on-click="resetToToday">Volver a hoy</button>
            </t>
            <button class="pf-btn" t-on-click="loadData">Actualizar</button>
        </div>
    </div>

    <div class="pf-filters">
        <select t-on-change="onModeChange" t-att-value="state.mode">
            <option value="year">Por año</option>
            <option value="month">Por mes</option>
            <option value="range">Rango de fechas</option>
        </select>

        <t t-if="state.mode === 'year'">
            <select t-on-change="onYearChange">
                <t t-foreach="years" t-as="y" t-key="y">
                    <option t-att-value="y" t-att-selected="y === state.year"><t t-esc="y"/></option>
                </t>
            </select>
        </t>

        <t t-if="state.mode === 'month'">
            <select t-on-change="onYearChange">
                <t t-foreach="years" t-as="y" t-key="y">
                    <option t-att-value="y" t-att-selected="y === state.year"><t t-esc="y"/></option>
                </t>
            </select>
            <select t-on-change="onMonthChange">
                <option value="1"  t-att-selected="state.month === 1">Enero</option>
                <option value="2"  t-att-selected="state.month === 2">Febrero</option>
                <option value="3"  t-att-selected="state.month === 3">Marzo</option>
                <option value="4"  t-att-selected="state.month === 4">Abril</option>
                <option value="5"  t-att-selected="state.month === 5">Mayo</option>
                <option value="6"  t-att-selected="state.month === 6">Junio</option>
                <option value="7"  t-att-selected="state.month === 7">Julio</option>
                <option value="8"  t-att-selected="state.month === 8">Agosto</option>
                <option value="9"  t-att-selected="state.month === 9">Septiembre</option>
                <option value="10" t-att-selected="state.month === 10">Octubre</option>
                <option value="11" t-att-selected="state.month === 11">Noviembre</option>
                <option value="12" t-att-selected="state.month === 12">Diciembre</option>
            </select>
        </t>

        <t t-if="state.mode === 'range'">
            <input type="date" t-att-value="state.dateFrom" t-on-change="onDateFromChange"/>
            <input type="date" t-att-value="state.dateTo"   t-on-change="onDateToChange"/>
            <button class="pf-btn" t-on-click="loadData">Buscar</button>
        </t>

        <input type="text" placeholder="Buscar venta, cliente o producto..." t-on-input="onSearch"/>

        <select t-on-change="onVendedorChange">
            <option value="">Todos los vendedores</option>
            <t t-foreach="state.vendedores" t-as="v" t-key="v">
                <option t-att-value="v"><t t-esc="v"/></option>
            </t>
        </select>
    </div>

    <div class="pf-kpis">
        <div class="pf-kpi">
            <div class="pf-kpi-label">Pend. facturar · unidades</div>
            <div class="pf-kpi-val"><t t-esc="state.totalPend"/></div>
            <div class="pf-kpi-sub"><t t-esc="state.totalOrdenes"/> órdenes · <t t-esc="state.totalLineas"/> líneas</div>
        </div>
        <div class="pf-kpi pf-kpi-warn">
            <div class="pf-kpi-label">Pend. nota crédito · unidades</div>
            <div class="pf-kpi-val" style="color:#dc2626"><t t-esc="state.totalPendNc"/></div>
            <div class="pf-kpi-sub"><t t-esc="state.totalOrdenesNc"/> órdenes · <t t-esc="state.totalLineasNc"/> líneas</div>
        </div>
        <div class="pf-kpi">
            <div class="pf-kpi-label">NC sueltas detectadas</div>
            <div class="pf-kpi-val" style="color:#d97706"><t t-esc="state.ncSueltas.length"/></div>
            <div class="pf-kpi-sub">sin ligar a venta</div>
        </div>
    </div>

    <!-- Tabs -->
    <div class="pf-tabs">
        <button class="pf-tab" t-att-class="!state.showNcTab ? 'pf-tab pf-tab-active' : 'pf-tab'"
            t-on-click="showFactTab">
            Pendiente facturar (<t t-esc="state.totalLineas"/>)
        </button>
        <button t-att-class="state.showNcTab ? 'pf-tab pf-tab-active pf-tab-red' : 'pf-tab pf-tab-red'"
            t-on-click="showNcTab">
            Pendiente NC (<t t-esc="state.totalLineasNc"/>)
        </button>
    </div>

    <div class="pf-table-wrap">
        <t t-if="state.loading">
            <div class="pf-loading">Cargando datos...</div>
        </t>
        <t t-elif="!state.showNcTab">
            <div class="pf-tbody-scroll">
                <table>
                    <thead>
                        <tr>
                            <th>Venta</th>
                            <th>Fecha</th>
                            <th>Cliente</th>
                            <th>Vendedor</th>
                            <th>Producto</th>
                            <th class="r">Entrega neta</th>
                            <th class="r">Facturado neto</th>
                            <th class="r">NC</th>
                            <th class="r">Pendiente</th>
                            <th style="width:50px"></th>
                        </tr>
                    </thead>
                    <tbody>
                        <t t-if="state.filtered.length === 0">
                            <tr><td colspan="9" class="pf-empty">Sin pendientes · todo facturado ✓</td></tr>
                        </t>
                        <t t-foreach="state.filtered" t-as="row" t-key="row_index">
                            <tr>
                                <td class="muted"><t t-esc="row.venta"/></td>
                                <td class="muted"><t t-esc="row.fecha"/></td>
                                <td><t t-esc="row.cliente"/></td>
                                <td class="muted"><t t-esc="row.vendedor"/></td>
                                <td><t t-esc="row.producto"/></td>
                                <td class="r num"><t t-esc="row.entrega"/></td>
                                <td class="r num"><t t-esc="row.facturado"/></td>
                                <td class="r num red">
                                    <t t-if="row.nc > 0">-<t t-esc="row.nc"/></t>
                                    <t t-else="">—</t>
                                </td>
                                <td class="r num amber"><t t-esc="row.pendiente"/></td>
                                <td>
                                    <button class="pf-btn-sm" t-on-click="onAuditar"
                                        t-att-data-venta="row.venta"
                                        t-att-data-producto="row.producto"
                                        t-att-data-id="row.id">Ver</button>
                                </td>
                            </tr>
                            <t t-if="state.auditKey === row.id">
                                <tr>
                                    <td colspan="10" style="padding:0">
                                        <div class="pf-audit-panel">
                                            <t t-if="state.auditLoading">
                                                <div class="pf-loading">Cargando auditoría...</div>
                                            </t>
                                            <t t-elif="state.auditData">
                                                <!-- Resumen cuadre -->
                                                <div class="pf-audit-resumen">
                                                    <span>Salidas: <b><t t-esc="state.auditData.resumen.total_salidas"/></b></span>
                                                    <span>Devoluciones: <b><t t-esc="state.auditData.resumen.total_devoluc"/></b></span>
                                                    <span>= Entrega neta: <b><t t-esc="state.auditData.resumen.entrega_neta"/></b></span>
                                                    <span class="pf-audit-sep">|</span>
                                                    <span>Facturado: <b><t t-esc="state.auditData.resumen.total_facturado"/></b></span>
                                                    <span>NC: <b><t t-esc="state.auditData.resumen.total_nc"/></b></span>
                                                    <span>= Fact. neto: <b><t t-esc="state.auditData.resumen.facturado_neto"/></b></span>
                                                    <span class="pf-audit-sep">|</span>
                                                    <t t-if="state.auditData.resumen.cuadra">
                                                        <span class="pf-audit-ok">✓ Cuadra</span>
                                                    </t>
                                                    <t t-else="">
                                                        <span class="pf-audit-diff">⚠ Diferencia: <b><t t-esc="state.auditData.resumen.diferencia"/></b></span>
                                                    </t>
                                                </div>
                                                <div class="pf-audit-tables">
                                                    <!-- Movimientos stock -->
                                                    <div class="pf-audit-col">
                                                        <div class="pf-audit-col-title">Movimientos de stock</div>
                                                        <table>
                                                            <thead>
                                                                <tr>
                                                                    <th>Picking</th>
                                                                    <th>Tipo</th>
                                                                    <th>Fecha</th>
                                                                    <th class="r">Cantidad</th>
                                                                    <th class="r">Neto</th>
                                                                </tr>
                                                            </thead>
                                                            <tbody>
                                                                <t t-foreach="state.auditData.movimientos" t-as="mv" t-key="mv.move_id">
                                                                    <tr>
                                                                        <td class="muted" style="font-size:11px"><t t-esc="mv.picking"/></td>
                                                                        <td>
                                                                            <t t-if="mv.tipo === 'outgoing'">
                                                                                <span class="pf-tag-out">Salida</span>
                                                                            </t>
                                                                            <t t-else="">
                                                                                <span class="pf-tag-in">Devolucion</span>
                                                                            </t>
                                                                        </td>
                                                                        <td class="muted"><t t-esc="mv.fecha"/></td>
                                                                        <td class="r num"><t t-esc="mv.cantidad"/></td>
                                                                        <td class="r num" t-att-class="mv.cantidad_neta > 0 ? 'r num' : 'r num red'"><t t-esc="mv.cantidad_neta"/></td>
                                                                    </tr>
                                                                </t>
                                                                <tr class="pf-audit-total">
                                                                    <td colspan="4" style="text-align:right">Total neto</td>
                                                                    <td class="r num"><t t-esc="state.auditData.resumen.entrega_neta"/></td>
                                                                </tr>
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                    <!-- Facturas y NC -->
                                                    <div class="pf-audit-col">
                                                        <div class="pf-audit-col-title">Facturas y notas de crédito</div>
                                                        <table>
                                                            <thead>
                                                                <tr>
                                                                    <th>Documento</th>
                                                                    <th>Tipo</th>
                                                                    <th>Fecha</th>
                                                                    <th class="r">Cantidad</th>
                                                                    <th class="r">Neto</th>
                                                                </tr>
                                                            </thead>
                                                            <tbody>
                                                                <t t-foreach="state.auditData.facturas" t-as="fv" t-key="fv.move_id + fv.documento">
                                                                    <tr>
                                                                        <td class="muted" style="font-size:11px"><t t-esc="fv.documento"/></td>
                                                                        <td>
                                                                            <t t-if="fv.tipo === 'out_invoice'">
                                                                                <span class="pf-tag-inv">Factura</span>
                                                                            </t>
                                                                            <t t-else="">
                                                                                <span class="pf-tag-nc">NC</span>
                                                                            </t>
                                                                        </td>
                                                                        <td class="muted"><t t-esc="fv.fecha"/></td>
                                                                        <td class="r num"><t t-esc="fv.cantidad"/></td>
                                                                        <td class="r num" t-att-class="fv.cantidad_neta > 0 ? 'r num' : 'r num red'"><t t-esc="fv.cantidad_neta"/></td>
                                                                    </tr>
                                                                </t>
                                                                <tr class="pf-audit-total">
                                                                    <td colspan="4" style="text-align:right">Total neto</td>
                                                                    <td class="r num"><t t-esc="state.auditData.resumen.facturado_neto"/></td>
                                                                </tr>
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                </div>
                                            </t>
                                        </div>
                                    </td>
                                </tr>
                            </t>
                        </t>
                    </tbody>
                </table>
            </div>
        </t>
        <t t-elif="state.showNcTab">
            <div class="pf-tbody-scroll">
                <table>
                    <thead>
                        <tr>
                            <th>Venta</th>
                            <th>Fecha</th>
                            <th>Cliente</th>
                            <th>Vendedor</th>
                            <th>Producto</th>
                            <th class="r">Entrega neta</th>
                            <th class="r">Facturado neto</th>
                            <th class="r">Devolucion sin NC</th>
                            <th style="width:50px"></th>
                        </tr>
                    </thead>
                    <tbody>
                        <t t-if="state.filteredNc.length === 0">
                            <tr><td colspan="9" class="pf-empty">Sin devoluciones pendientes de NC ✓</td></tr>
                        </t>
                        <t t-foreach="state.filteredNc" t-as="row" t-key="row_index">
                            <tr>
                                <td class="muted"><t t-esc="row.venta"/></td>
                                <td class="muted"><t t-esc="row.fecha"/></td>
                                <td><t t-esc="row.cliente"/></td>
                                <td class="muted"><t t-esc="row.vendedor"/></td>
                                <td><t t-esc="row.producto"/></td>
                                <td class="r num"><t t-esc="row.entrega"/></td>
                                <td class="r num"><t t-esc="row.facturado"/></td>
                                <td class="r num red"><t t-esc="row.pendiente_nc"/></td>
                                <td>
                                    <button class="pf-btn-sm" t-on-click="onAuditar"
                                        t-att-data-venta="row.venta"
                                        t-att-data-producto="row.producto"
                                        t-att-data-id="row.id">Ver</button>
                                </td>
                            </tr>
                            <t t-if="state.auditKey === row.id">
                                <tr>
                                    <td colspan="9" style="padding:0">
                                        <div class="pf-audit-panel">
                                            <t t-if="state.auditLoading">
                                                <div class="pf-loading">Cargando auditoría...</div>
                                            </t>
                                            <t t-elif="state.auditData">
                                                <div class="pf-audit-resumen">
                                                    <span>Salidas: <b><t t-esc="state.auditData.resumen.total_salidas"/></b></span>
                                                    <span>Devoluciones: <b><t t-esc="state.auditData.resumen.total_devoluc"/></b></span>
                                                    <span>= Entrega neta: <b><t t-esc="state.auditData.resumen.entrega_neta"/></b></span>
                                                    <span class="pf-audit-sep">|</span>
                                                    <span>Facturado: <b><t t-esc="state.auditData.resumen.total_facturado"/></b></span>
                                                    <span>NC: <b><t t-esc="state.auditData.resumen.total_nc"/></b></span>
                                                    <span>= Fact. neto: <b><t t-esc="state.auditData.resumen.facturado_neto"/></b></span>
                                                    <span class="pf-audit-sep">|</span>
                                                    <span class="pf-audit-diff">Pend. NC: <b><t t-esc="state.auditData.resumen.diferencia"/></b></span>
                                                </div>
                                                <div class="pf-audit-tables">
                                                    <div class="pf-audit-col">
                                                        <div class="pf-audit-col-title">Movimientos de stock</div>
                                                        <table>
                                                            <thead><tr><th>Picking</th><th>Tipo</th><th>Fecha</th><th class="r">Cantidad</th><th class="r">Neto</th></tr></thead>
                                                            <tbody>
                                                                <t t-foreach="state.auditData.movimientos" t-as="mv" t-key="mv.move_id">
                                                                    <tr>
                                                                        <td class="muted" style="font-size:11px"><t t-esc="mv.picking"/></td>
                                                                        <td><t t-if="mv.tipo === 'outgoing'"><span class="pf-tag-out">Salida</span></t><t t-else=""><span class="pf-tag-in">Devolucion</span></t></td>
                                                                        <td class="muted"><t t-esc="mv.fecha"/></td>
                                                                        <td class="r num"><t t-esc="mv.cantidad"/></td>
                                                                        <td class="r num" t-att-class="mv.cantidad_neta > 0 ? 'r num' : 'r num red'"><t t-esc="mv.cantidad_neta"/></td>
                                                                    </tr>
                                                                </t>
                                                                <tr class="pf-audit-total"><td colspan="4" style="text-align:right">Total neto</td><td class="r num"><t t-esc="state.auditData.resumen.entrega_neta"/></td></tr>
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                    <div class="pf-audit-col">
                                                        <div class="pf-audit-col-title">Facturas y notas de crédito</div>
                                                        <table>
                                                            <thead><tr><th>Documento</th><th>Tipo</th><th>Fecha</th><th class="r">Cantidad</th><th class="r">Neto</th></tr></thead>
                                                            <tbody>
                                                                <t t-foreach="state.auditData.facturas" t-as="fv" t-key="fv.move_id + fv.documento">
                                                                    <tr>
                                                                        <td class="muted" style="font-size:11px"><t t-esc="fv.documento"/></td>
                                                                        <td><t t-if="fv.tipo === 'out_invoice'"><span class="pf-tag-inv">Factura</span></t><t t-else=""><span class="pf-tag-nc">NC</span></t></td>
                                                                        <td class="muted"><t t-esc="fv.fecha"/></td>
                                                                        <td class="r num"><t t-esc="fv.cantidad"/></td>
                                                                        <td class="r num" t-att-class="fv.cantidad_neta > 0 ? 'r num' : 'r num red'"><t t-esc="fv.cantidad_neta"/></td>
                                                                    </tr>
                                                                </t>
                                                                <tr class="pf-audit-total"><td colspan="4" style="text-align:right">Total neto</td><td class="r num"><t t-esc="state.auditData.resumen.facturado_neto"/></td></tr>
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                </div>
                                            </t>
                                        </div>
                                    </td>
                                </tr>
                            </t>
                        </t>
                    </tbody>
                </table>
            </div>
        </t>
    </div>

    <!-- Panel NC no ligadas -->
    <t t-if="state.ncSueltas.length > 0">
        <div class="pf-nc-alert" t-on-click="toggleNcPanel">
            <b><t t-esc="state.ncSueltas.length"/></b> nota(s) de crédito posiblemente no ligadas a una factura
            <span class="pf-nc-toggle"><t t-if="state.showNcPanel">▲ Ocultar</t><t t-else="">▼ Ver NC</t></span>
        </div>
        <t t-if="state.showNcPanel">
            <div class="pf-nc-panel">
                <table>
                    <thead>
                        <tr>
                            <th style="width:32px"></th>
                            <th>Nota de crédito</th>
                            <th>Fecha</th>
                            <th>Cliente</th>
                            <th class="r">Total</th>
                            <th style="width:80px"></th>
                        </tr>
                    </thead>
                    <tbody>
                        <t t-foreach="state.ncSueltas" t-as="nc" t-key="nc.move_id">
                            <tr class="pf-nc-row">
                                <td>
                                    <button class="pf-expand-btn" t-on-click="onToggleNcDetail"
                                        t-att-data-id="nc.move_id">
                                        <t t-if="state.ncExpandKey === nc.move_id">▼</t>
                                        <t t-else="">▶</t>
                                    </button>
                                </td>
                                <td class="red"><t t-esc="nc.nc_name"/></td>
                                <td class="muted"><t t-esc="nc.nc_fecha"/></td>
                                <td><t t-esc="nc.cliente"/></td>
                                <td class="r num red">$<t t-esc="nc.total.toLocaleString('es-MX', {minimumFractionDigits:2})"/></td>
                                <td>
                                    <button class="pf-btn-sm" t-on-click="onOpenNC"
                                        t-att-data-id="nc.move_id">Abrir</button>
                                </td>
                            </tr>
                            <t t-if="state.ncExpandKey === nc.move_id">
                                <tr>
                                    <td colspan="6" style="padding:0 0 0 32px;background:#fffbf0">
                                        <table class="pf-nc-detail">
                                            <thead>
                                                <tr>
                                                    <th>Producto</th>
                                                    <th class="r">Cantidad</th>
                                                    <th class="r">Precio</th>
                                                    <th class="r">Subtotal</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <t t-foreach="nc.lineas" t-as="ln" t-key="ln_index">
                                                    <tr>
                                                        <td><t t-esc="ln.producto"/></td>
                                                        <td class="r num"><t t-esc="ln.cantidad"/></td>
                                                        <td class="r num">$<t t-esc="ln.precio.toLocaleString('es-MX', {minimumFractionDigits:2})"/></td>
                                                        <td class="r num red">$<t t-esc="ln.subtotal.toLocaleString('es-MX', {minimumFractionDigits:2})"/></td>
                                                    </tr>
                                                </t>
                                            </tbody>
                                        </table>
                                    </td>
                                </tr>
                            </t>
                        </t>
                    </tbody>
                </table>
            </div>
        </t>
    </t>

    <!-- Análisis de pedido -->
    <div class="pf-orden-wrap">
        <div class="pf-orden-bar">
            <span style="font-weight:500;font-size:13px">Análisis de pedido</span>
            <div style="display:flex;gap:6px;align-items:center">
                <input class="pf-orden-input" type="text"
                    placeholder="Ej: S48786"
                    t-att-value="state.ordenBusqueda"
                    t-on-input="onOrdenInput"
                    t-on-keydown="onOrdenKeydown"
                />
                <button class="pf-btn" t-on-click="buscarOrden">Buscar</button>
            </div>
        </div>

        <t t-if="state.ordenLoading">
            <div class="pf-loading">Buscando pedido...</div>
        </t>
        <t t-elif="state.ordenError">
            <div class="pf-orden-notfound"><t t-esc="state.ordenError"/></div>
        </t>
        <t t-elif="state.ordenData">
            <div class="pf-orden-meta">
                <span><b><t t-esc="state.ordenData.venta"/></b></span>
                <span class="muted"><t t-esc="state.ordenData.fecha"/></span>
                <span><t t-esc="state.ordenData.cliente"/></span>
                <span class="muted"><t t-esc="state.ordenData.vendedor"/></span>
            </div>
            <div class="pf-nc-panel">
                <table>
                    <thead>
                        <tr>
                            <th>Producto</th>
                            <th class="r">Pedido</th>
                            <th class="r">Entregado</th>
                            <th class="r">Facturado</th>
                            <th class="r">Pendiente</th>
                            <th>Facturas</th>
                            <th>Notas crédito</th>
                        </tr>
                    </thead>
                    <tbody>
                        <t t-foreach="state.ordenData.lineas" t-as="lin" t-key="lin_index">
                            <tr>
                                <td><t t-esc="lin.producto"/></td>
                                <td class="r num"><t t-esc="lin.pedido"/></td>
                                <td class="r num"><t t-esc="lin.entregado"/></td>
                                <td class="r num"><t t-esc="lin.facturado"/></td>
                                <td class="r num amber">
                                    <t t-if="lin.pendiente > 0.001"><t t-esc="lin.pendiente"/></t>
                                    <t t-elif="lin.pendiente &lt; -0.001"><span class="red"><t t-esc="lin.pendiente"/></span></t>
                                    <t t-else="">✓</t>
                                </td>
                                <td class="muted" style="font-size:11px"><t t-esc="lin.facturas"/></td>
                                <td class="muted red" style="font-size:11px"><t t-esc="lin.notas_credito"/></td>
                            </tr>
                        </t>
                    </tbody>
                </table>
            </div>
        </t>
    </div>

    <div class="pf-footer">
        <t t-if="state.startDate">
            <t t-esc="state.startDate"/> → <t t-esc="state.endDate"/> ·
        </t>
        Última actualización: <t t-esc="state.lastUpdate"/> · <t t-if="state.paused">pausado</t><t t-else="">próxima en <t t-esc="formatCountdown(state.countdown)"/>s</t>
    </div>

</div>`;

class PendingInvoiceDashboard extends Component {
    static template = TEMPLATE;

    setup() {
        this.rpc = useService("rpc");
        const now = new Date();
        const currentYear  = now.getFullYear();
        const currentMonth = now.getMonth() + 1;

        this.years = [];
        for (let y = currentYear; y >= currentYear - 4; y--) {
            this.years.push(y);
        }

        const today = now.toISOString().slice(0, 10);

        this.state = useState({
            mode:        'range',
            year:        currentYear,
            month:       currentMonth,
            dateFrom:    today,
            dateTo:      today,
            rows:           [],
            filtered:       [],
            rowsNc:         [],
            filteredNc:     [],
            totalPend:      0,
            totalPendNc:    0,
            totalOrdenes:   0,
            totalOrdenesNc: 0,
            totalLineas:    0,
            totalLineasNc:  0,
            showNcTab:      false,
            lastUpdate:  '—',
            startDate:   '',
            endDate:     '',
            countdown:    30,
            paused:       false,
            autoRefresh:  true,
            vendedores:  [],
            searchText:   '',
            vendedorFil:  '',
            loading:      false,
            ncSueltas:     [],
            showNcPanel:   false,
            ncExpandKey:   null,
            auditKey:      null,
            auditData:     null,
            auditLoading:  false,
            ordenBusqueda: '',
            ordenLoading:  false,
            ordenData:     null,
            ordenError:    '',
        });

        this._timer = null;
        onMounted(() => this.loadData());
        onWillUnmount(() => this._clearTimer());
    }

    async loadData() {
        this._clearTimer();
        this.state.loading = true;

        const params = {};
        if (this.state.mode === 'year') {
            params.year = this.state.year;
        } else if (this.state.mode === 'month') {
            params.year  = this.state.year;
            params.month = this.state.month;
        } else {
            params.date_from = this.state.dateFrom;
            params.date_to   = this.state.dateTo;
        }

        try {
            console.log('[pend_fact] params enviados:', params);
            const res = await this.rpc('/pend_fact/data', params);
            console.log('[pend_fact] respuesta:', res);
            this.state.rows           = res.rows;
            this.state.rowsNc         = res.rows_nc || [];
            this.state.totalPend      = res.total_pend;
            this.state.totalPendNc    = res.total_pend_nc || 0;
            this.state.totalOrdenes   = res.total_ordenes;
            this.state.totalOrdenesNc = res.total_ordenes_nc || 0;
            this.state.totalLineas    = res.total_lineas;
            this.state.totalLineasNc  = res.total_lineas_nc || 0;
            this.state.startDate    = res.start_date;
            this.state.endDate      = res.end_date;
            this.state.lastUpdate   = new Date().toLocaleTimeString('es-MX');
            this.state.vendedores   = [...new Set(res.rows.map(r => r.vendedor))].sort();
            this.state.ncSueltas    = res.nc_sueltas || [];
            this._applyFilter();
        } catch (e) {
            console.error('[pend_fact] error RPC:', e);
        }

        this.state.loading = false;
        this._startCountdown();
    }

    _applyFilter() {
        const q = this.state.searchText.toLowerCase();
        const v = this.state.vendedorFil;
        const match = r => {
            const matchQ = !q || [r.venta, r.cliente, r.producto].some(s => s.toLowerCase().includes(q));
            const matchV = !v || r.vendedor === v;
            return matchQ && matchV;
        };
        this.state.filtered   = this.state.rows.filter(match);
        this.state.filteredNc = this.state.rowsNc.filter(match);
    }

    formatCountdown(secs) {
        const h = Math.floor(secs / 3600);
        const m = Math.floor((secs % 3600) / 60);
        const s = secs % 60;
        return `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
    }

    _startCountdown() {
        if (!this.state.autoRefresh) return;   // modo manual, no arrancar timer
        this.state.countdown = 30;
        this._timer = setInterval(() => {
            if (this.state.paused) return;
            this.state.countdown--;
            if (this.state.countdown <= 0) {
                this._clearTimer();
                this.loadData();
            }
        }, 1000);
    }

    togglePause() {
        this.state.paused = !this.state.paused;
        // Al reanudar, reiniciar el countdown
        if (!this.state.paused) {
            this.state.countdown = 30;
        }
    }

    _clearTimer() {
        if (this._timer) { clearInterval(this._timer); this._timer = null; }
    }

    toggleNcPanel()        { this.state.showNcPanel = !this.state.showNcPanel; }

    onToggleNcDetail(ev) {
        const id = Number(ev.currentTarget.getAttribute('data-id'));
        this.state.ncExpandKey = this.state.ncExpandKey === id ? null : id;
    }

    showFactTab()  { this.state.showNcTab = false; }
    showNcTab()    { this.state.showNcTab = true; }

    onOpenNC(ev) {
        const id = ev.target.closest('button').dataset.id;
        window.open('/web#id=' + id + '&model=account.move&view_type=form&action=197', '_blank');
    }

    async onAuditar(ev) {
        const btn      = ev.currentTarget;
        const venta    = btn.getAttribute('data-venta');
        const producto = btn.getAttribute('data-producto');
        const id       = Number(btn.getAttribute('data-id'));

        console.log('[pend_fact] auditar:', venta, producto, id);

        // toggle: cerrar si ya está abierto
        if (this.state.auditKey === id) {
            this.state.auditKey  = null;
            this.state.auditData = null;
            return;
        }
        this.state.auditKey     = id;
        this.state.auditData    = null;
        this.state.auditLoading = true;
        try {
            const res = await this.rpc('/pend_fact/auditoria', { venta, producto });
            console.log('[pend_fact] auditoria res:', res);
            this.state.auditData = res;
        } catch(e) {
            console.error('[pend_fact] auditoria error:', e);
            this.state.auditLoading = false;
        }
        this.state.auditLoading = false;
    }

    openNC(moveId) {
        window.open(
            '/web#id=' + moveId + '&model=account.move&view_type=form&action=197',
            '_blank'
        );
    }

    onOrdenInput(ev)      { this.state.ordenBusqueda = ev.target.value; }
    onOrdenKeydown(ev)    { if (ev.key === 'Enter') this.buscarOrden(); }

    async buscarOrden() {
        const venta = this.state.ordenBusqueda.trim();
        if (!venta) return;
        this.state.ordenLoading = true;
        this.state.ordenData    = null;
        this.state.ordenError   = '';
        try {
            const res = await this.rpc('/pend_fact/orden', { venta });
            if (res.found) {
                this.state.ordenData  = res;
            } else {
                this.state.ordenError = `No se encontró el pedido "${venta}"`;
            }
        } catch(e) {
            this.state.ordenError = 'Error al buscar el pedido';
            console.error('[pend_fact] buscarOrden error:', e);
        }
        this.state.ordenLoading = false;
    }

    // Detectar si el filtro activo es exactamente "hoy"
    _isToday() {
        const today = new Date().toISOString().slice(0, 10);
        return this.state.mode === 'range'
            && this.state.dateFrom === today
            && this.state.dateTo   === today;
    }

    _setManual() {
        this.state.autoRefresh = false;
        this._clearTimer();
    }

    resetToToday() {
        const today = new Date().toISOString().slice(0, 10);
        this.state.mode      = 'range';
        this.state.dateFrom  = today;
        this.state.dateTo    = today;
        this.state.autoRefresh = true;
        this.state.paused    = false;
        this.loadData();
    }

    onModeChange(ev) {
        this.state.mode = ev.target.value;
        this._setManual();
        if (this.state.mode !== 'range') this.loadData();
    }
    onYearChange(ev) {
        this.state.year = parseInt(ev.target.value);
        this._setManual();
        this.loadData();
    }
    onMonthChange(ev) {
        this.state.month = parseInt(ev.target.value);
        this._setManual();
        this.loadData();
    }
    onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value;
        // Detectar si volvió a ser hoy
        if (this._isToday()) {
            this.state.autoRefresh = true;
        } else {
            this._setManual();
        }
    }
    onDateToChange(ev) {
        this.state.dateTo = ev.target.value;
        if (this._isToday()) {
            this.state.autoRefresh = true;
        } else {
            this._setManual();
        }
    }
    onSearch(ev)         { this.state.searchText = ev.target.value; this._applyFilter(); }
    onVendedorChange(ev) { this.state.vendedorFil = ev.target.value; this._applyFilter(); }
}

registry.category("actions").add("pend_fact", PendingInvoiceDashboard);
