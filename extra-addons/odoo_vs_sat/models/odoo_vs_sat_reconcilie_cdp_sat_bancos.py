# -*- coding: utf-8 -*-
import pandas as pd
from io import BytesIO
from odoo import models, fields, api
import base64
import io
from odoo.exceptions import ValidationError
import pandas as pd
import base64
import io
from io import BytesIO
from odoo import models, fields, api
from datetime import datetime
from babel.dates import format_date

class OdooVsSatReconcilieCDP(models.Model):
    _name = 'odoo_vs_sat.reconcilie.cdp.sat.bancos'
    _description = 'Conciliación Notas de Crédito y Facturas'
    _rec_name = "name"  # Cambiar a 'name' para usar el nombre calculado como _rec_name
    start_date = fields.Date(string='Fecha de Inicio',required=True)
    end_date = fields.Date(string='Fecha Final',required=True)
    attachment_id = fields.Many2one('ir.attachment', string='Archivo Adjunto')
    name = fields.Char(string='Nombre', compute='_compute_rec_name', store=True)

    @api.depends('start_date', 'end_date')
    def _compute_rec_name(self):
        for record in self:
            record.name = record._get_rec_name()

    def _get_rec_name(self):
        if self.start_date and self.end_date:
            # Formatear las fechas con nombres de meses en español
            start_date_str = format_date(self.start_date, format='long', locale='es')
            end_date_str = format_date(self.end_date, format='long', locale='es')
            return f'Del {start_date_str} al {end_date_str}'
        return ''

    attachment_bancos_ids = fields.Many2many(
        'ir.attachment', 
        'reconcilie_cdp_sat_bancos_attachment_bancos_rel',  
        'reconcilie_id',  
        'attachment_id',  
        string='Documentos Bancos'
    )

    attachment_xml_sat_ids = fields.Many2many(
        'ir.attachment', 
        'reconcilie_cdp_sat_bancos_attachment_xml_sat_rel',  
        'reconcilie_id',  
        'attachment_id',  
        string='XML SAT'
    )

    attachment_conciliacion_ids = fields.Many2many(
        'ir.attachment', 
        'reconcilie_cdp_sat_bancos_attachment_conciliacion_rel',  
        'reconcilie_id',  
        'attachment_id',  
        string='Conciliaciones'
    )

    
    @api.constrains('attachment_bancos_ids', 'attachment_xml_sat_ids', 'attachment_conciliacion_ids')
    def _check_single_attachment(self):
        for record in self:
            if len(record.attachment_bancos_ids) > 1:
                raise ValidationError("Solo puedes adjuntar un archivo en 'Documentos Bancos'.")
            if len(record.attachment_xml_sat_ids) > 1:
                raise ValidationError("Solo puedes adjuntar un archivo en 'XML SAT'.")
            if len(record.attachment_conciliacion_ids) > 1:
                raise ValidationError("Solo puedes adjuntar un archivo en 'Conciliaciones'.")
 
    
    def reconcile(self):
        bank = base64.b64decode(self.attachment_bancos_ids.datas)
        sat = base64.b64decode(self.attachment_xml_sat_ids.datas)     
        start_date = pd.to_datetime(self.start_date, errors='coerce').replace(hour=0, minute=0, second=0)
        end_date = pd.to_datetime(self.end_date, errors='coerce').replace(hour=23, minute=59, second=59)
        
        df_bancos_usd = pd.read_excel(BytesIO(bank),
                                      sheet_name='HSBC USD',
                                      usecols=['ID', 'Fecha del apunte', 'BENEF/CTE', 'Importe de crédito', 'Moneda', 'ING/EGR/SDO', 'CONCEPTO']
                                      )
        df_bancos = pd.read_excel(BytesIO(bank),sheet_name='BBVA PESOS')
        df_one_facture = pd.read_excel(BytesIO(sat))
        print(df_one_facture)
        # Reemplazar los saltos de línea en los nombres de las columnas
        df_bancos_usd.columns = df_bancos_usd.columns.str.replace('\n', '')
        # Renombrar las columnas de df_bancos_usd para que coincidan con las de df_bancos
        df_bancos_usd.rename(columns={
            'ID': 'ID',
            'Fecha del apunte': 'FechaValor',
            'BENEF/CTE': 'BENEF/CTE',
            'Importe de crédito': 'Abono',
            'Moneda': 'Divisa',
            'ING/EGR/SDO': 'ING/EGR/SDO',
            'CONCEPTO2': 'CONCEPTO'
        }, inplace=True)

        # Filtrar los registros donde ING/EGR/SDO == 'INGRESO' y CONCEPTO == 'COBRANZA'
        df_bancos_usd['Abono'] = pd.to_numeric(df_bancos_usd['Abono'], errors='coerce')

        df_bancos_usd = df_bancos_usd[(df_bancos_usd['Abono'] > 0) & (df_bancos_usd['Abono'].notna())
        & (df_bancos_usd['ID'].notna() & (df_bancos_usd['ING/EGR/SDO']=='INGRESO')
        & (df_bancos_usd['CONCEPTO']=='COBRANZA'))]       
        
        df_bancos.columns = df_bancos.columns.str.replace('\n', '')
        df_bancos['FechaOperación'] = pd.to_datetime(df_bancos['FechaOperación'], errors='coerce')
        df_bancos['FechaOperación'] = pd.to_datetime(df_bancos['FechaOperación']).apply(lambda x: x.replace(hour=0, minute=0, second=0))
        df_bancos = df_bancos[
            (df_bancos['FechaOperación'] >= start_date) &
            (df_bancos['FechaOperación'] <= end_date) & ((df_bancos['ID']))
        ]
        df_bancos['origen_1']='BANCOS'
        df_bancos['id_bnk'] = df_bancos.index + 1
        df_bancos['id_bnk'] = df_bancos['id_bnk'].astype(int)
             
        df_one_facture['Fecha pago'] = pd.to_datetime(df_one_facture['Fecha pago'], errors='coerce')
        df_one_facture['Fecha pago'] = df_one_facture['Fecha pago'].apply(lambda x: x.replace(hour=0, minute=0, second=0) if pd.notna(x) else x)
        df_one_facture['origen_2']='SAT'
        df_one_facture = df_one_facture[
            (df_one_facture['Fecha pago'] >= start_date) &
            (df_one_facture['Fecha pago'] <= end_date)
        ]
        print(df_one_facture)                
        df_one_facture = df_one_facture.drop_duplicates(subset='UUID', keep='first')
        print(df_one_facture)                
        df_one_facture.reset_index(drop=True, inplace=True)      

        def generar_folio(row):
            prefijo = row['Serie']
            numero = str(int(row['Folio'])).zfill(5)  # Convertimos a entero antes de a string
            folio = f"{prefijo}{numero}"
            return folio
        df_one_facture['Folio'] = df_one_facture.apply(generar_folio, axis=1)         
        
        query = """
        -- Seleccionamos de la tabla principal account_move
        SELECT
            aj.id AS id_diario,
            aj.name AS nombre_diario,
            am.name AS nombre_factura,
            am.date as fecha_de_pago,
            am.state as estado_odoo,
            am.amount_total_signed as monto,
            am.l10n_mx_edi_cfdi_uuid as uuid, -- Todos los campos de account_move
            rp.id AS id_cliente ,
            rp.conpaq_account AS conpaq_account ,
            rp.name AS nombre_cliente, -- Nombre del cliente
            rp.vat AS rfc_cliente -- RFC del cliente
        FROM account_move am
        -- Usamos un JOIN LATERAL para filtrar las líneas relacionadas
        JOIN LATERAL (
            SELECT 1
            FROM account_move_line aml
            JOIN account_account aa 
            ON aml.account_id = aa.id
            WHERE aml.move_id = am.id 
            AND aa.account_type = 'asset_receivable'
            LIMIT 1 -- Optimizamos para verificar solo una coincidencia
        ) subquery ON true
        -- Unimos con res_partner para obtener el nombre y RFC
        LEFT JOIN res_partner rp
        ON am.partner_id = rp.id
        -- Unimos con account_journal para obtener el diario
        LEFT JOIN account_journal aj 
        ON am.journal_id = aj.id
        -- Filtros de tipo de movimiento y rango de fechas
        WHERE am.move_type = 'entry'
        AND am.state = 'posted'
        AND am.date BETWEEN %s AND %s;
        """
        # Execute the SQL query
        self.env.cr.execute(query, (start_date, end_date))

        # Fetch the results
        rows = self.env.cr.dictfetchall()

        # Create a pandas DataFrame
        df_pagos_odoo = pd.DataFrame(rows)
        df_pagos_odoo['origen_3']='ODOO'

        # Define una función que depende de varias columnas
        def calcular_total(fila):
            if fila['id_diario'] in [138]:
                return 'PUE'
            if fila['id_diario'] in [140,141]:
                return 'AJUSTE'
            if fila['id_diario'] in [3]:
                return 'AJUSTE'    
            if fila['id_diario'] in [139]:
                return 'AJUSTE'    
            if fila['id_diario'] in [143]:
                return 'AJUSTE'                
            if fila['id_diario'] in [4]:
                return 'DIFERENCIA CAMBIARIA'    
            elif fila['uuid']:
                return 'PPD'
            else:
                return 'ERROR'

        df_pagos_odoo['timbrado'] = df_pagos_odoo.apply(calcular_total, axis=1)

        df_one_factura_pagos_odoo = pd.merge(
            df_pagos_odoo,
            df_one_facture,
            left_on='uuid',
            right_on='UUID',
            how='outer',
            indicator=True  # Esto ayuda a identificar el origen de cada registro
        )
        df_one_factura_pagos_odoo['id_opo'] = df_one_factura_pagos_odoo.index + 1
        df_one_factura_pagos_odoo['id_opo'] = df_one_factura_pagos_odoo['id_opo'].astype(int)
        df_one_factura_pagos_odoo['monto'] = df_one_factura_pagos_odoo['monto'].astype(float)
        
        # Inicializar la columna id_bnk con None
        df_one_factura_pagos_odoo['id_bnk'] = None

        def asignar_id(renglon, df_bancos, ids_asignados):
            # Verificar si ya tiene un 'id_bnk' asignado, en ese caso no hacer nada
            if renglon['id_opo'] == 524:
                print("2")    
            
            # Filtrar el DataFrame df_bancos según 'id_cliente' y 'monto', excluyendo ids ya asignados
            str_column = 'monto'
            if renglon['MonedaP']=='MXN':
                str_column = 'monto'
            elif renglon['MonedaP']=='USD':
                str_column = 'Monto'
            df_filtrado = df_bancos[
                (df_bancos['ID'] == renglon['id_cliente']) 
                &(df_bancos['Abono'] == renglon[str_column]) 
                & 
                (~df_bancos['id_bnk'].isin(ids_asignados))  # Filtrar ids que no han sido asignados
            ]        
            
            # Verificar si el DataFrame filtrado tiene registros
            if not df_filtrado.empty:
                # Tomar el primer renglón del filtrado
                res = df_filtrado.iloc[0]
                
                # Asegurarse de que el id_bnk no haya sido asignado previamente
                if res['id_bnk'] not in ids_asignados:
                    # Agregar el id_bnk a los ids asignados y devolverlo
                    ids_asignados.add(res['id_bnk'])
                    return res['id_bnk']
            
            # Si no se encuentra el renglón o ya está asignado, retornar None
            return None

        # Crear un conjunto para almacenar los ids_bnk ya asignados
        ids_asignados = set()

        # Aplicar la función 'asignar_id' a cada renglón de 'df_one_factura_pagos_odoo'
        df_one_factura_pagos_odoo['id_bnk'] = df_one_factura_pagos_odoo.apply(
            asignar_id, 
            axis=1, 
            df_bancos=df_bancos, 
            ids_asignados=ids_asignados
        )

        df_joined = pd.merge(df_one_factura_pagos_odoo, df_bancos, on='id_bnk', how='outer', suffixes=('_odoo', '_bancos'))
        columnas_a_eliminar = [
            'Periodo', 'Versión CFDI', 'Uso CFDI', 'UUIDs relacionados', 'Tipo relacion', 
            'CP Expedicion', 'Serie', 'RFC emisor', 'Razon emisor', 'Fecha emision',
            'Fecha certificacion', 'Estado', 'Fecha proceso cancelacion', 'Estado cancelacion', 
            'Estado proceso cancelacion', 'Motivo cancelacion', 'Folio sustitucion cancelacion',
            'NomBancoExt', 'RfcEmisorCtaOrd', 'CtaOrdenante', 'RfcEmisorCtaBen', 
            'CtaBeneficiario', 'TipoCadPago', 'CadPago', 'Número operación', 
            'RetencionesIVA - pago', 'RetencionesISR - pago', 'RetencionesIEPS - pago', 
            'TrasladosBaseIVA8 - pago', 
            'TrasladosImpuestoIVA8 - pago', 'TrasladosImpuestoIVA0 - pago', 
            'TrasladosBaseIVAExento - pago', 'TrasladosBaseIEPS8 - pago', 'TrasladosImpuestoIEPS8 - pago', 
            'Id documento', 'Estatus (Almacen)', 'Fecha emision (Doc)', 'Fecha certificacion (Doc)', 
            'Fecha cancelacion (Doc)', 'Serie documento', 'Folio documento', 'EquivalenciaDR', 
            'MonedaDR', 'TipoCambioDR', 'MetodoDePagoDR', 'NumParcialidad', 'ObjetoImpDR', 
            'RetencionesIVA', 'RetencionesISR', 'RetencionesIEPS', 'TrasladosBaseIVA16', 
            'TrasladosBaseIVA8', 'TrasladosImpuestoIVA8', 
            'TrasladosBaseIVA0', 'TrasladosImpuestoIVA0', 'TrasladosBaseIVAExento', 
            'TrasladosBaseIEPS8', 'TrasladosImpuestoIEPS8', 'Saldo anterior', 
            'Saldo actual',
            # Nuevas columnas a eliminar
            'Descipcion',
            'Referencia', 'Contrato', 'FechaOperación', 'Nombre', 'Código deLeyenda', 
            'TipoOperación', 'Plaza', 'Saldo', 'SDO ARRASTRE', 'ING/EGR/SDO', 'BENEF/CTE', 
            'CONCEPTO', 'SEMANA', 'CONTAB /FOLIO PAGO', 'COMENTARIOS', 'CONCEPTO2', 'AREA'
        ]

        # Eliminar las columnas
        df_joined = df_joined.drop(columns=columnas_a_eliminar, errors='ignore')  # `errors='ignore'` evitará errores si alguna columna no existe
        
        def estatus(renglon):
            """
            Origen 
            origen_3 ODOO
            origen_2 SAT
            origen_1 BANCOS
            
            Diario
            4 Diferencia de cambio
            138	PAGO AL CONTADO
            
            """
            # Verificar si ya tiene un 'id_bnk' asignado, en ese caso no hacer nada
            id_diario = renglon['id_diario']
            # Reemplazar valores nulos o vacíos con espacios
            origen_3 = renglon['origen_3'] if pd.notna(renglon['origen_3']) else ""
            origen_2 = renglon['origen_2'] if pd.notna(renglon['origen_2']) else ""
            origen_1 = renglon['origen_1'] if pd.notna(renglon['origen_1']) else ""
            if id_diario == 138 and origen_1 == 'BANCOS' and origen_3 == 'ODOO':
                return 'CORRECTO'
            elif id_diario not in [4,138,143] and origen_1 == 'BANCOS' and origen_2 == 'SAT' and origen_3 == 'ODOO':
                return 'CORRECTO'
            else:
                return 'INCORRECTO'

        # Aplicar la función 'asignar_id' a cada renglón de 'df_one_factura_pagos_odoo'
        df_joined['estatus'] = df_joined.apply(estatus, axis=1)     

            # Mover columnas 'C' y 'A' al final
        columnas_a_mover = ['nombre_diario','origen_1', 'origen_2','origen_3']
        columnas_ordenadas = [col for col in df_joined.columns if col not in columnas_a_mover] + columnas_a_mover
        df_joined = df_joined[columnas_ordenadas]
        
        df_correcto = df_joined[df_joined['estatus'] == 'CORRECTO']
        df_ajuste = df_joined[df_joined['timbrado'] == 'AJUSTE']
        df_diferencia_cambiaria = df_joined[df_joined['timbrado'] == 'DIFERENCIA CAMBIARIA']
        df_incorrecto = df_joined[
            (~df_joined['timbrado'].isin(['DIFERENCIA CAMBIARIA', 'AJUSTE',''])) & 
            (df_joined['estatus'] == 'INCORRECTO')
        ]   
        
        # Convertir cadenas a objetos datetime
        start_dt = datetime.strptime(start_date.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
        end_dt = datetime.strptime(end_date.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
        
        # Formatear las fechas en español
        start_date_words = format_date(start_dt, format='d MMMM yyyy', locale='es')
        end_date_words = format_date(end_dt, format='d MMMM yyyy', locale='es')
        file_name = f'Pagos del {start_date_words} al {end_date_words} MXN.xlsx'
        fp = io.BytesIO()
        with pd.ExcelWriter(fp) as writer:
            df_correcto.to_excel(writer, sheet_name='CORRECTO', index=False)
            df_ajuste.to_excel(writer, sheet_name='AJUSTES', index=False)
            df_diferencia_cambiaria.to_excel(writer, sheet_name='DIFERENCIA CAMBIARIA', index=False)
            df_incorrecto.to_excel(writer, sheet_name='INCORRECTO', index=False)
            df_one_facture.to_excel(writer, sheet_name='CFDIS', index=False)
            df_bancos.to_excel(writer, sheet_name='BANCOS', index=False)
        
        fp.seek(0)
        attachment_data = base64.b64encode(fp.read()).decode('utf-8')
        attachment = self.env['ir.attachment'].create({
            'name': f'Conciliación {file_name}.xlsx',
            'type': 'binary',
            'datas': attachment_data,
            'store_fname': f'Conciliación {file_name}.xlsx',
            'mimetype': 'application/vnd.ms-excel',
            'res_model': self._name,
            'res_id': self.id,
        })
        
        self.attachment_conciliacion_ids = [(4, attachment.id)]
        return attachment                        
        