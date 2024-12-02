import openpyxl
import os
import concurrent.futures

# Especificar la carpeta donde están los archivos de Excel
carpeta = "/home/dev-odoo/Downloads/REPORTES DIRECCION"

# Obtener la lista de archivos en la carpeta
archivos = [f for f in os.listdir(carpeta) if f.endswith('.xlsx')]
total_archivos = len(archivos)

def procesar_archivo(archivo):
    try:
        # Cargar el archivo de Excel sin read_only=True
        ruta_completa = os.path.join(carpeta, archivo)
        wb = openpyxl.load_workbook(ruta_completa, data_only=True)
        
        # Borrar el primer renglón de todas las hojas
        for sheet in wb.worksheets:
            sheet.delete_rows(1)
        
        # Crear una lista de hojas a eliminar
        hojas_a_eliminar = [sheet.title for sheet in wb.worksheets if sheet.title != "reporte_direccion"]
        
        # Eliminar las hojas que no se llamen "reporte_direccion"
        for sheet_name in hojas_a_eliminar:
            wb.remove(wb[sheet_name])
        
        # Guardar los cambios en el archivo de Excel
        wb.save(ruta_completa)
        print(f"Procesado archivo: {archivo}")
    except Exception as e:
        print(f"Error procesando archivo {archivo}: {e}")

# Usar concurrent.futures para procesar archivos en paralelo
with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [executor.submit(procesar_archivo, archivo) for archivo in archivos]
    for i, future in enumerate(concurrent.futures.as_completed(futures), start=1):
        try:
            future.result()
        except Exception as e:
            print(f"Error procesando archivo {archivos[i-1]}: {e}")

print("Proceso completado para todos los archivos en la carpeta.")
