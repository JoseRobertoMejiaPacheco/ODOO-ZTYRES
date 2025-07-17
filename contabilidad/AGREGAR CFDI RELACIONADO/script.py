import os
import xml.etree.ElementTree as ET

carpeta = '/mnt/contabilidad/AGREGAR CFDI RELACIONADO/CFDI'
nc = self.env['ztyres_promo.notas_credito'].browse(5)
for line in nc.line_ids:
    if line.nc_credit_id:
        context = line.action_view_details()
        domain = context.get('domain', None)
        domain.append(('state', 'in', ['valid']))
        uuids = self.env['ztyres_promo.lines'].search(domain).mapped('move_id').mapped('l10n_mx_edi_cfdi_uuid')
        uuids = list(set(filter(None, uuids)))  # Elimina duplicados y valores vacíos
        nc_uuid = line.nc_credit_id.l10n_mx_edi_cfdi_uuid
        # Definir espacios de nombres
        namespaces = {
            'cfdi': 'http://www.sat.gob.mx/cfd/4',
            'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'
        }
        ET.register_namespace('cfdi', namespaces['cfdi'])
        ET.register_namespace('tfd', namespaces['tfd'])
        for archivo in os.listdir(carpeta):
            if archivo.endswith('.xml'):
                ruta_xml = os.path.join(carpeta, archivo)
                tree = ET.parse(ruta_xml)
                root = tree.getroot()
                # Buscar nodo TimbreFiscalDigital
                tfd = root.find('.//tfd:TimbreFiscalDigital', namespaces)
                if tfd is not None and tfd.attrib.get('UUID', '').lower() == nc_uuid.lower():
                    print(f'UUID encontrado en: {archivo}')
                    # Crear nodo CfdiRelacionados
                    relacionados = ET.Element('{http://www.sat.gob.mx/cfd/4}CfdiRelacionados', TipoRelacion='01')
                    # Agregar cada UUID relacionado como subnodo
                    for uuid in uuids:
                        relacionado = ET.SubElement(relacionados, '{http://www.sat.gob.mx/cfd/4}CfdiRelacionado')
                        relacionado.set('UUID', uuid)
                    # Insertar después del primer nodo hijo del root (generalmente después del nodo de emisor)
                    root.insert(1, relacionados)
                    # Guardar archivo
                    tree.write(ruta_xml, encoding='utf-8', xml_declaration=True)
                    print(f'CFDI relacionados agregados en {archivo}')
