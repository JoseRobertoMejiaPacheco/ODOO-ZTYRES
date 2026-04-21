#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para descargar PDFs y XMLs de facturas en Odoo 16 Enterprise
Uso: Ejecutar desde Odoo shell
Cada factura genera su propio PDF y XML independiente
"""

import base64
import os
from datetime import datetime

# ====== CONFIGURACIÓN ======
# Lista de números de factura
FACTURAS = [
'RVNAC/2025/22139',
'RVNAC/2025/22140',
'RVNAC/2025/22141',
'VEMP/2025/00018',
'VNAC/2025/19215',
'VNAC/2025/19222',
'VNAC/2025/19238',
'VNAC/2025/19239',
'VNAC/2025/19248',
'VNAC/2025/19253',
'VNAC/2025/19268',
'VNAC/2025/19269',
'VNAC/2025/19272',
'VNAC/2025/19277',
'VNAC/2025/19282',
'VNAC/2025/19324',
'VNAC/2025/19330',
'VNAC/2025/19349',
'VNAC/2025/19373',
'VNAC/2025/19376',
'VNAC/2025/19389',
'VNAC/2025/19418',
'VNAC/2025/19419',
'VNAC/2025/19421',
'VNAC/2025/19424',
'VNAC/2025/19425',
'VNAC/2025/19431',
'VNAC/2025/19446',
'VNAC/2025/19485',
'VNAC/2025/19489',
'VNAC/2025/19490',
'VNAC/2025/19497',
'VNAC/2025/19544',
'VNAC/2025/19552',
'VNAC/2025/19560',
'VNAC/2025/19562',
'VNAC/2025/19565',
'VNAC/2025/19569',
'VNAC/2025/19586',
'VNAC/2025/19588',
'VNAC/2025/19595',
'VNAC/2025/19596',
'VNAC/2025/19597',
'VNAC/2025/19605',
'VNAC/2025/19614',
'VNAC/2025/19641',
'VNAC/2025/19645',
'VNAC/2025/19659',
'VNAC/2025/19663',
'VNAC/2025/19665',
'VNAC/2025/19670',
'VNAC/2025/19673',
'VNAC/2025/19676',
'VNAC/2025/19684',
'VNAC/2025/19685',
'VNAC/2025/19690',
'VNAC/2025/19698',
'VNAC/2025/19700',
'VNAC/2025/19705',
'VNAC/2025/19708',
'VNAC/2025/19712',
'VNAC/2025/19719',
'VNAC/2025/19726',
'VNAC/2025/19729',
'VNAC/2025/19735',
'VNAC/2025/19742',
'VNAC/2025/19744',
'VNAC/2025/19765',
'VNAC/2025/19776',
'VNAC/2025/19784',
'VNAC/2025/19786',
'VNAC/2025/19790',
'VNAC/2025/19791',
'VNAC/2025/19792',
'VNAC/2025/19807',
'VNAC/2025/19808',
'VNAC/2025/19809',
'VNAC/2025/19812',
'VNAC/2025/19813',
'VNAC/2025/19822',
'VNAC/2025/19826',
'VNAC/2025/19827',
'VNAC/2025/19835',
'VNAC/2025/19846',
'VNAC/2025/19847',
'VNAC/2025/19859',
'VNAC/2025/19869',
'VNAC/2025/19872',
'VNAC/2025/19874',
'VNAC/2025/19878',
'VNAC/2025/19879',
'VNAC/2025/19887',
'VNAC/2025/19890',
'VNAC/2025/19897',
'VNAC/2025/19900',
'VNAC/2025/19917',
'VNAC/2025/19935',
'VNAC/2025/19937',
'VNAC/2025/19940',
'VNAC/2025/19942',
'VNAC/2025/19953',
'VNAC/2025/19959',
'VNAC/2025/19963',
'VNAC/2025/19970',
'VNAC/2025/19979',
'VNAC/2025/19980',
'VNAC/2025/19981',
'VNAC/2025/19982',
'VNAC/2025/19989',
'VNAC/2025/19990',
'VNAC/2025/19992',
'VNAC/2025/19999',
'VNAC/2025/20000',
'VNAC/2025/20005',
'VNAC/2025/20008',
'VNAC/2025/20010',
'VNAC/2025/20014',
'VNAC/2025/20015',
'VNAC/2025/20016',
]

# Carpeta donde se guardarán los archivos
CARPETA_DESTINO = '/mnt/contabilidad/facturas_descargadas'
# ===========================

def descargar_facturas():
    """
    Descarga PDFs y XMLs de las facturas especificadas
    Cada factura genera su propio PDF y XML independiente
    """
    # Crear carpeta si no existe
    if not os.path.exists(CARPETA_DESTINO):
        os.makedirs(CARPETA_DESTINO)
        print(f"✓ Carpeta creada: {CARPETA_DESTINO}")
    
    # Contadores
    exitosas = 0
    fallidas = 0
    pdfs_generados = 0
    xmls_guardados = 0
    
    print(f"\n{'='*60}")
    print(f"Iniciando descarga de {len(FACTURAS)} facturas...")
    print(f"Cada factura tendrá su propio PDF y XML")
    print(f"{'='*60}\n")
    
    # Buscar el reporte una sola vez (fuera del loop para eficiencia)
    report = env['ir.actions.report'].search([
        ('report_name', '=', 'account.report_invoice_with_payments'),
        ('model', '=', 'account.move')
    ], limit=1)
    
    if not report:
        print("✗ ERROR: Reporte no encontrado. Abortando.")
        return
    
    for numero_factura in FACTURAS:
        print(f"Procesando: {numero_factura}")
        
        try:
            # Buscar la factura
            factura = env['account.move'].search([
                ('name', '=', numero_factura),
                ('move_type', 'in', ['out_invoice', 'out_refund'])
            ], limit=1)
            
            if not factura:
                print(f"  ✗ No encontrada: {numero_factura}")
                fallidas += 1
                continue
            
            # Nombre base para los archivos (sanitizado)
            nombre_base = numero_factura.replace('/', '_')
            
            # ===== GENERAR PDF INDIVIDUAL =====
            try:
                # Generar PDF SOLO para esta factura específica
                pdf_content = report._render_qweb_pdf(report.id, factura.ids)[0]
                
                # Guardar PDF individual
                pdf_path = os.path.join(CARPETA_DESTINO, f"{nombre_base}.pdf")
                with open(pdf_path, 'wb') as pdf_file:
                    pdf_file.write(pdf_content)
                print(f"  ✓ PDF guardado: {nombre_base}.pdf ({len(pdf_content)} bytes)")
                pdfs_generados += 1
            except Exception as e:
                print(f"  ✗ Error al generar PDF: {str(e)}")
            
            # ===== GUARDAR XML INDIVIDUAL =====
            try:
                # Buscar el archivo XML adjunto (para México - CFDI)
                attachment = env['ir.attachment'].search([
                    ('res_model', '=', 'account.move'),
                    ('res_id', '=', factura.id),
                    ('name', 'ilike', '.xml')
                ], limit=1)
                
                if attachment:
                    # Decodificar y guardar XML individual
                    xml_content = base64.b64decode(attachment.datas)
                    xml_path = os.path.join(CARPETA_DESTINO, f"{nombre_base}.xml")
                    with open(xml_path, 'wb') as xml_file:
                        xml_file.write(xml_content)
                    print(f"  ✓ XML guardado: {nombre_base}.xml ({len(xml_content)} bytes)")
                    xmls_guardados += 1
                else:
                    # Alternativa: buscar en el campo l10n_mx_edi_cfdi (México)
                    if hasattr(factura, 'l10n_mx_edi_cfdi') and factura.l10n_mx_edi_cfdi:
                        xml_content = base64.b64decode(factura.l10n_mx_edi_cfdi)
                        xml_path = os.path.join(CARPETA_DESTINO, f"{nombre_base}.xml")
                        with open(xml_path, 'wb') as xml_file:
                            xml_file.write(xml_content)
                        print(f"  ✓ XML guardado: {nombre_base}.xml ({len(xml_content)} bytes)")
                        xmls_guardados += 1
                    else:
                        print(f"  ⚠ XML no encontrado para: {numero_factura}")
            except Exception as e:
                print(f"  ✗ Error al guardar XML: {str(e)}")
            
            exitosas += 1
            print()
            
        except Exception as e:
            print(f"  ✗ Error procesando {numero_factura}: {str(e)}\n")
            fallidas += 1
    
    # Resumen final
    print(f"{'='*60}")
    print(f"RESUMEN:")
    print(f"  Total facturas en lista: {len(FACTURAS)}")
    print(f"  Facturas procesadas: {exitosas}")
    print(f"  Facturas fallidas: {fallidas}")
    print(f"  PDFs generados: {pdfs_generados}")
    print(f"  XMLs guardados: {xmls_guardados}")
    print(f"  Archivos en: {CARPETA_DESTINO}")
    print(f"{'='*60}\n")
    
    # Listar archivos generados
    if pdfs_generados > 0 or xmls_guardados > 0:
        print("Archivos generados:")
        archivos = sorted(os.listdir(CARPETA_DESTINO))
        for archivo in archivos:
            ruta_completa = os.path.join(CARPETA_DESTINO, archivo)
            tamaño = os.path.getsize(ruta_completa)
            print(f"  - {archivo} ({tamaño:,} bytes)")

# Ejecutar la función
if __name__ == '__main__':
    descargar_facturas()