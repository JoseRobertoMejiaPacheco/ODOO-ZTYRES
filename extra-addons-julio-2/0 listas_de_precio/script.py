import pandas as pd
import os
import re  # Importar la biblioteca re para trabajar con expresiones regulares
def calcular_descuento_logistico(row, suma_cantidad):
    if row['Outlet']==0:
        return 0
    if row['Lista de Precios'] in ['Mayoreo', 'Promocion']:
        if 80 <= suma_cantidad <= 250:
            return row['Costo Real'] * 0.01
        elif 251 <= suma_cantidad <= 600:
            return row['Costo Real'] * 0.02
        elif 601 <= suma_cantidad <= 999999:
            return row['Costo Real'] * 0.04
    return 0

    # Calcular la mejor condición y la lista de precios
def calcular_mejor_condicion(row,discount):
    valores = [(row['Mayoreo']*(1-(discount/100))), row['prom'], row['Outlet']]
    mejor_valor = min(valores)
    mejor_condicion = valores.index(mejor_valor)
    
    if mejor_condicion == 0:
        lista = "Mayoreo"
    elif mejor_condicion == 1:
        lista = "Promocion"
    else:
        lista = "Outlet"
    print(mejor_valor, lista)
    return mejor_valor, lista

def calcular_revision(row):
    if row['NC'] == 0:
        return "Correcto"
    else:
        return "Erróneo"

def calcular_subtotal(row):
    f_desc = ((row['price_unit']*(1-(row['discount']/100))))
    return (f_desc)*row['product_oum_qty']

def calcular_subtotal_correcto(row):
    f_desc = (row['MejorCondicion'])
    return (f_desc)*row['product_oum_qty']

def calcular_direfencia(row):
    if row['Revision'] == 'Erróneo':    
        return row['price_unit']-row['MejorCondicion']
    else:
        return 0

def extraer_numero_etiqueta(etiqueta):
    # Buscar el patrón numérico antes del %
    match = re.search(r'(\d+)\%', etiqueta)
    if match:
        return int(match.group(1))  # Convertir el resultado a entero
    else:
        return None

def calcular_monto_nc(row):
    return row['SubtotalErroneo']-row['SubtotalCorrecto']  

def convert_to_company_currency(currency_id, amount, date):
    currency_record = self.env['res.currency'].browse(currency_id.id)
    converted_amount = currency_record._convert(
        amount,
        currency_record.env.company.currency_id,
        currency_record.env.company,
        date
    )
    return converted_amount if converted_amount else 0

data = [
    ('03-10-2024','02-10-2024',0,70145)
]

for fecha_factura,dia_lista,discount_global,id_factura in data:
    file_path = f'/mnt/extra-addons/0 listas_de_precio/{dia_lista}.xlsx'
    df_base = pd.read_excel(file_path, sheet_name='reporte_direccion',usecols=['Id','Codigo','Mayoreo','prom','Outlet'])
    # Agregar la columna MejorCondicion al dataframe
    #########################################3
    err_invoices = self.env['account.move'].browse(id_factura)#search(domain)
    data = []
    for invoice in err_invoices:
        r = invoice.invoice_line_ids.filtered(lambda line: line.discount > 0)
        if r:
            descuento_volumen =  discount_global
        else:
            descuento_volumen = discount_global
        order_line_data = []
        for line in invoice.invoice_line_ids:
            order_line_data.append({      
                        'Id': line.product_id.product_tmpl_id.id,  # Puedes ajustar según la necesidad, por ejemplo, line.product_id.name  
                        'Código': line.product_id.default_code,
                        'Medida': line.product_id.tire_measure_id.name,
                        'Capas': line.product_id.layer_id.name,
                        'Vel': line.product_id.speed_id.name,
                        'Carga': line.product_id.index_of_load_id.name,
                        'Modelo': line.product_id.model_id.name,
                        'Marca': line.product_id.brand_id.name,            
                        'price_unit': line.price_unit,
                        'product_oum_qty': line.quantity,
                        'discount': line.discount, 
                        'Observaciones' : ""         
                    })
        # Crear DataFrame desde la lista de diccionarios
        print(file_path)
        order_line_df = pd.DataFrame(order_line_data)
        df = df_base
        df['Mayoreo con Descuento'] = df['Mayoreo'] * (1 - (descuento_volumen/100))
        df.fillna(0)
        df[['MejorCondicion', 'lista de precios']] = df.apply(lambda row: calcular_mejor_condicion(row, descuento_volumen), axis=1).apply(pd.Series)
        merged_df = pd.merge(df, order_line_df, on='Id', how='inner')
        merged_df['SubtotalErroneo'] = merged_df.apply(lambda row: calcular_subtotal(row), axis=1)
        merged_df['SubtotalCorrecto'] = merged_df.apply(lambda row: calcular_subtotal_correcto(row), axis=1)
        merged_df['NC'] = merged_df.apply(lambda row: calcular_monto_nc(row), axis=1)
        merged_df['Revision'] = merged_df.apply(lambda row: calcular_revision(row), axis=1)    
        merged_df
        mv = ''
        pago_aplicado = 0
        tipo = []
        monto = []
        descripciones = []
        count = 0
        if invoice.invoice_payments_widget and invoice.invoice_payments_widget.get("content"):
            data = []
            for item in invoice.invoice_payments_widget["content"]:
                move = False
                if item.get("move_id"):
                    move = invoice.browse(item["move_id"])
                    if move.move_type == 'entry':
                        mv = 'Pago'
                        tipo.append(mv)
                    elif move.move_type == 'out_refund':
                        mv = 'Nota de Credito'
                        tipo.append(mv)
                    # print(mv)
                    pago_aplicado = pago_aplicado + convert_to_company_currency(move.currency_id, item.get("amount"), move.invoice_date or move.date) or 0
                    
                    for item_2 in move:
                        for item_2 in move.invoice_line_ids.filtered(lambda l: l.display_type == 'product' and l.debit > 0):
                            data.append({
                                    'Tipo': mv,
                                    'Folio': item_2.name,
                                    'Nombre de producto': item_2.product_id.name,
                                    'Etiqueta': item_2.name,  # Asumiendo que hay un campo de etiqueta en account.move.line
                                    'Subtotal': item_2.debit,
                                })
        print(data)
        df_pagos = pd.DataFrame(data)    
        print(df_pagos)
        merged_df = merged_df.rename(columns={
            'product_oum_qty': 'Cantidad',
            'prom': 'Promocion',
            'price_unit': 'Precio',
            'SubtotalErroneo': 'Costo factura',
            'SubtotalCorrecto': 'Costo Real',
            'lista de precios': 'Lista de Precios'
        })
        suma_cantidad = merged_df['Cantidad'].sum()
        merged_df['Descuento Logistico'] = merged_df.apply(lambda row: calcular_descuento_logistico(row, suma_cantidad), axis=1)    
        # Reordenar columnas según el nuevo orden que especificaste
        column_order = ['Id', 'Codigo', 'Medida', 'Capas', 'Vel', 'Carga', 'Modelo', 'Marca',
                        'Cantidad', 'Mayoreo','Mayoreo con Descuento','Promocion', 'Outlet', 'MejorCondicion','Lista de Precios',
                        'Precio', 'Costo factura', 'Costo Real','Observaciones','NC','Revision','Descuento Logistico']
        logistico = 0
        total_etiqueta_descuento = 0
        total_descuento = 0
        if not df_pagos.empty:
            filtro = df_pagos['Etiqueta'].str.contains('DESCUENTO: Logístico', case=True)
        else:
            filtro = pd.Series()
        
        merged_df = merged_df[column_order]
        if filtro.any():
            logistico = extraer_numero_etiqueta(df_pagos.loc[filtro, 'Etiqueta'].values[0])
            total_etiqueta_descuento = df_pagos.loc[filtro, 'Subtotal'].sum()
            total_descuento = total_etiqueta_descuento - merged_df['Descuento Logistico'].sum()
        else:
            logistico = 0
            total_etiqueta_descuento = 0
            total_descuento = 0
        
        total_nc = merged_df['NC'].sum() - total_descuento
        df_total_nc = pd.DataFrame({'Total de NC': [total_nc]})
        df_total_log = pd.DataFrame({'Diferencia Dto. Logístico': [total_descuento]})
        dataframes = [merged_df, df_total_nc, total_nc]
        nombre_archivo = f"{invoice.name.replace('/', '_')}{invoice.partner_id.name}1.0.10.xlsx"
        if True: #total_nc > 0:
            ruta_archivo = f'/mnt/extra-addons/0 listas_de_precio/excel/{nombre_archivo}'     
            ##################################
            with pd.ExcelWriter(ruta_archivo) as writer:
                merged_df.to_excel(writer, sheet_name='Precios', index=False)
                df_pagos.to_excel(writer, sheet_name='Pagos', index=False)        
                df_total_log.to_excel(writer, sheet_name='Diferencia de NC Logístico', index=False)
                df_total_nc.to_excel(writer, sheet_name='Total Nota de Cŕedito', index=False)