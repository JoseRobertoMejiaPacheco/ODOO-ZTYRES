import pandas as pd

po = env['purchase.order'].browse(2912)

data = []

for line in po.order_line:
    product = line.product_id
    for move in line.move_ids:
        picking_name = move.picking_id.name if move.picking_id else "Sin picking"
        procurement_group = move.group_id.name if move.group_id else "Sin procurement group"
        location_origin = move.location_id.display_name
        location_dest = move.location_dest_id.display_name
        
        # Determinar si es entrada, salida o devolución
        if move.picking_type_id.code == 'incoming':
            tipo = 'Entrada'
        elif move.picking_type_id.code == 'outgoing':
            tipo = 'Salida'
        elif move.picking_type_id.code == 'internal':
            tipo = 'Movimiento interno'
        else:
            tipo = 'Otro'
        if 'Proveedor' in location_dest:
            tipo = 'Devolución'
        
        # Datos de valoración
        svl = move.stock_valuation_layer_ids
        svl_qty = sum(svl.mapped('quantity'))
        svl_cost = sum(svl.mapped('unit_cost'))
        svl_value = sum(svl.mapped('value'))
        
        # Datos de factura
        invoice_lines = line.invoice_lines
        for inv_line in invoice_lines:
            row = {
                'po_id': po.name,
                'product_name': product.name,
                'product_code': product.default_code,
                'sm_name': move.name,
                'sm_state': move.state,
                'sm_picking': picking_name,
                'sm_procurement_group': procurement_group,
                'sm_qty': move.product_uom_qty,
                'sm_tipo_mov': tipo,
                'sm_ubicacion_origen': location_origin,
                'sm_ubicacion_destino': location_dest,
                'sm_precio_unitario': move.price_unit,
                'sm_procure_method': move.procure_method,
                'svl_qty': svl_qty,
                'svl_cost': svl_cost,
                'svl_value': svl_value,
                'factura': inv_line.move_id.name if inv_line.move_id else "Sin factura",
                'factura_fecha': inv_line.move_id.invoice_date if inv_line.move_id else "",
                'factura_subtotal': inv_line.price_subtotal,
            }
            data.append(row)

# Crear DataFrame y exportar
df = pd.DataFrame(data)
df = df[sorted(df.columns)]
output_path = '/mnt/extra-addons/ztyres_promo/reporte_licitacion.xlsx'
df.to_excel(output_path, index=False, freeze_panes=(1, 0))
