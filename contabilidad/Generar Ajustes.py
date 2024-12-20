#odoo shell -d ZTYRES --config /etc/odoo/odoo.conf --xmlrpc-port=8009 --workers=20

import pandas as pd
from odoo import models, fields, api
from datetime import datetime

# Cargar el archivo Excel en un DataFrame
# Reemplaza 'ruta_del_archivo.xlsx' con la ruta real del archivo Excel que contiene los datos
df = pd.read_excel('/mnt/contabilidad/ajustes.xlsx')

# Asegurarse de que las columnas del archivo Excel son correctas
# Suponemos que el archivo tiene las columnas: 'Cuenta Debe', 'Cuenta Haber', 'Cliente ID', 'Monto', 'Fecha'
# También agregaremos una nueva columna para el nombre del cliente

# Lista para almacenar el nombre del cliente
cliente_nombres = []

# Procesar cada fila en el DataFrame
for index, row in df.iterrows():
    # Lee los datos de cada fila
    monto = row['Monto']  # Monto del asiento contable
    cuenta_debe = row['Cuenta Debe']  # Cuenta del débito
    cuenta_haber = row['Cuenta Haber']  # Cuenta del crédito
    cliente_id = row['Cliente ID']  # ID del cliente
    fecha = datetime.strptime(row['Fecha'], '%d/%m/%Y')  # Convierte la fecha al formato de fecha de Odoo
    
    # Busca las cuentas contables por ID
    cuenta_debe_obj = self.env['account.account'].browse(cuenta_debe)
    cuenta_haber_obj = self.env['account.account'].browse(cuenta_haber)
    
    # Busca el cliente
    cliente_obj = self.env['res.partner'].browse(cliente_id)
    
    # Crea un nuevo asiento contable en el diario con ID 141
    move = self.env['account.move'].create({
        'journal_id': 141,  # ID del diario
        'date': fecha,  # Fecha del asiento
        'ref': 'Ajuste contable',  # Referencia, puedes modificar según tu necesidad
        'partner_id': cliente_obj.id,  # Cliente asociado al asiento
        'move_type': 'entry',  # Tipo de movimiento (entrada)
    })
    
    # Crea las líneas de asiento contable dentro del mismo proceso
    # Línea de débito
    move.write({
        'line_ids': [
            (0, 0, {
                'account_id': cuenta_debe_obj.id,  # Cuenta del débito
                'debit': 0.0,  # Monto a debitar
                'credit': monto,  # No hay crédito
                'partner_id': cliente_obj.id,  # Relaciona con el cliente
                'name': 'Débito a la cuenta ' + str(cuenta_debe),  # Descripción del débito
            }),
            (0, 0, {
                'account_id': cuenta_haber_obj.id,  # Cuenta del crédito
                'debit':monto,  # No hay débito
                'credit':  0.0,  # Monto a acreditar (el mismo que el débito)
                'partner_id': cliente_obj.id,  # Relaciona con el cliente
                'name': 'Crédito a la cuenta ' + str(cuenta_haber),  # Descripción del crédito
            }),
        ]
    })
    
    # Publica el asiento contable
    move.action_post()
    move.mapped('line_ids').filtered(lambda x: x.account_id.id in [1201,2244]).write({'reconciled': True,'amount_residual':0.0,'amount_residual_currency':0.0})
    
    # Añadimos el nombre del cliente a la lista
    cliente_nombres.append(cliente_obj.name)
    
    # Imprime un mensaje para confirmar que se ha creado y publicado el asiento

# Agregar la columna con el nombre del cliente al DataFrame
df['Nombre Cliente'] = cliente_nombres

# Guardar el DataFrame de vuelta en un archivo Excel con la nueva columna
# Reemplaza 'ruta_del_nuevo_archivo.xlsx' con la ruta donde deseas guardar el archivo modificado
df.to_excel('/mnt/contabilidad/ajustes_realizados.xlsx', index=False)

print("El archivo Excel ha sido actualizado y guardado.")

print(f"Asiento contable creado y publicado: {move.name} para el cliente {cliente_obj.name} con monto {monto}")
monto