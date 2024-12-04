import pandas as pd
from datetime import datetime
from odoo import api, SUPERUSER_ID
from openpyxl import load_workbook
from openpyxl.styles import numbers
df_list = []
dates = [
    # ('DICIEMBRE 2023', '2023-12-31 23:59:59'),
    # ('ENERO', '2024-01-31 23:59:59'),
    # ('FEBRERO', '2024-02-29 23:59:59'),  # Febrero de 2024 tiene 28 días
    # ('MARZO', '2024-03-31 23:59:59'),
    # ('ABRIL', '2024-04-30 23:59:59'),
    # ('MAYO', '2024-05-31 23:59:59'),
    # ('JUNIO', '2024-06-30 23:59:59'),
    # ('JULIO', '2024-07-31 23:59:59'),
    # ('AGOSTO', '2024-08-31 23:59:59'),
    # ('SEPTIEMBRE', '2024-09-30 23:59:59'),
    ('OCTUBRE', '2024-10-31 23:59:59'),
    # ('NOVIEMBRE', '2024-11-30 23:59:59'),
    # ('DICIEMBRE', '2024-12-31 23:59:59')
]

for month,date in dates:
    report_data = []  # Definimos report_data como una lista vacía
    ids_nacionales = [2,3,4,6,7,9,12,13,14,15,17]
    ids_importacion = [1,5,8,10,11,16,18,19,20,21,22,23]
    domain = [('type', '=', 'product')]
    products_at_date = self.env['product.product'].with_context(dict({
        'active_model': 'stock.quant',
        'lang': 'es_MX',
        'tz': 'America/Mexico_City',
        'uid': 2,
        'to_date': date
    })).search(domain)
    
    if True:
        for product in products_at_date:
            in_moves = 0
            out_moves = 0
            transit_ids = [53, 24686, 24687]
            # Asegúrate de convertir la cadena de fecha a un objeto datetime
            cutoff_date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
            
            # Filtra los movimientos de stock
            in_moves = sum(product.stock_move_ids.mapped('move_line_ids').filtered(
                lambda line: line.state == 'done' and 
                            line.date <= cutoff_date and
                            line.location_dest_id.id in transit_ids
            ).mapped('qty_done'))
            
            out_moves = sum(product.stock_move_ids.mapped('move_line_ids').filtered(
                lambda line: line.state == 'done' and 
                            line.date <= cutoff_date and
                            line.location_id.id in transit_ids
            ).mapped('qty_done'))
            total_at_date = 0
            total_at_date = in_moves - out_moves
            # Evitamos divisiones por cero verificando product.value_svl
            valor_transito =  product.value_svl/total_at_date  if total_at_date != 0 else 0            
            report_data.append({
                'Producto': product.name,
                'FABRICANTE': product.manufacturer_id.name,
                'Tipo de Producto': "NACIONAL" if product.manufacturer_id.id in ids_nacionales else "IMPORTACION" if product.manufacturer_id.id in ids_importacion else "SIN ESPECIFICAR",
                'Código': product.default_code,
                # 'Cantidad En Tránsito': total_at_date,
                # 'Valor Tránsito': valor_transito,
                'Cantidad Stock': product.product_tmpl_id.qty_available,
                'Valor Stock': product.value_svl                
            })
    df = pd.DataFrame(report_data)
    df_list.append((date,df))
    report_data = []  # Definimos report_data como una lista vacía
    df = None
    #file_path = f'/mnt/extra-addons/Valor de Inventario C {date}.xlsx'
    #df.to_excel(file_path,index=False)

with pd.ExcelWriter('/mnt/extra-addons/Valo.xlsx') as writer:
    for _date,_df in df_list:
        _df.to_excel(writer, sheet_name=_date.replace(':',' '), index=False)
