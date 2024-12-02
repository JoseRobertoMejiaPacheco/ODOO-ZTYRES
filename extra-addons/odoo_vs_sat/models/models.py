# -*- coding: utf-8 -*-
import pandas as pd
from io import BytesIO
from odoo import models, fields, api
from odoo.tools import format_date  # Asegúrate de importar format_date
import base64
import io

class OdooVsSatReconcilie(models.Model):
    _name = 'odoo_vs_sat.reconcilie'
    _description = 'Conciliación Notas de Crédito y Facturas'
    _rec_name = "name"  # Cambiar a 'name' para usar el nombre calculado como _rec_name
    start_date = fields.Date(string='Fecha de Inicio')
    end_date = fields.Date(string='Fecha Final')
    attachment_id = fields.Many2one('ir.attachment', string='Archivo Adjunto')
    name = fields.Char(string='Nombre', compute='_compute_rec_name', store=True)

    @api.depends('start_date', 'end_date')
    def _compute_rec_name(self):
        for record in self:
            record.name = record._get_rec_name()

    def _get_rec_name(self):
        if self.start_date and self.end_date:
            # Formatear las fechas con nombres de meses en español
            start_date_str = format_date(self.env, self.start_date)
            end_date_str = format_date(self.env, self.end_date)
            return f'Del {start_date_str} al {end_date_str}'
        return ''

    attachment_ids = fields.Many2many(
        'ir.attachment', 
        'reconcilie_attachment_rel',  # Nombre de la tabla relacional
        'reconcilie_id',               # Campo que referencia a odoo_vs_sat.reconcilie
        'attachment_id',               # Campo que referencia a ir.attachment
        string='Archivos Adjuntos',
        required=False,
    )

    def reconcile(self):
        self.attachment_ids.ensure_one()
        sat = base64.b64decode(self.attachment_ids.filtered(lambda a: a.name == "FACTURAS NOTAS SAT.xlsx").datas)
        df_dict = pd.read_excel(BytesIO(sat))
        if self.start_date and self.end_date:
            pass
        start_date = pd.to_datetime(self.start_date, errors='coerce').replace(hour=0, minute=0, second=0)
        end_date = pd.to_datetime(self.end_date, errors='coerce').replace(hour=23, minute=59, second=59)
        """
        I Ingreso
        E Egreso
        N Nómina
        T Traslado
        P Pago
        """
        df_dict['Fecha emision'] = pd.to_datetime(df_dict['Fecha emision'], errors='coerce')
        df_ingresos = df_dict[
            (df_dict['Fecha emision'] >= start_date) &
            (df_dict['Fecha emision'] <= end_date) &
            (df_dict['Tipo'].isin(['I','E']))
        ]
        df_ingresos['Folio Odoo'] = None
        df_ingresos['Validacion Monto'] = None
        
        def generar_folio(row):
            prefijo = row['Serie']
            numero = str(row['Folio']).zfill(5)
            folio = f"{prefijo}{numero}"
            return folio
        df_ingresos.loc[:, 'Folio Odoo'] = df_ingresos.apply(generar_folio, axis=1)
        
        """SubTotal Es la suma de los importes de los conceptos antes de descuentos e
        impuestos. No se permiten valores negativos.
         Este campo debe tener hasta la cantidad de decimales que
        soporte la moneda, ver ejemplo del campo Moneda.
         Cuando en el campo TipoDeComprobante sea I (Ingreso),
        E (Egreso) o N (Nómina), el importe registrado en este
        campo debe ser igual al redondeo de la suma de los importes
        de los conceptos registrados.
         Cuando en el campo TipoDeComprobante sea T (Traslado)
        o P (Pago) el importe registrado en este campo debe ser
        igual a cero.
        http://omawww.sat.gob.mx/tramitesyservicios/Paginas/documentos/guiaanexo20_07092017.pdf"""
        df_ingresos['SubTotal'] = df_ingresos['SubTotal'] - df_ingresos['Descuento']
        
        short_df_ingresos = df_ingresos.loc[:, ['Tipo','RFC receptor','Razon receptor','UUID','SubTotal','Estado','Folio Odoo','Validacion Monto']]
        query = """
                    SELECT
                        "name" AS "Folio Odoo",
                        invoice_date AS "Fecha Odoo",
                        l10n_mx_edi_cfdi_uuid AS "UUID Odoo",
                        amount_untaxed_signed AS "Total Odoo",
                        state AS "Estado Odoo",
                        CASE
                            WHEN move_type = 'out_refund' THEN 'E'
                            WHEN move_type = 'out_invoice' THEN 'I'
                        END AS "Tipo"
                    FROM
                        account_move
                    WHERE
                        invoice_date BETWEEN %s AND %s
                    AND
                        move_type in ('out_invoice', 'out_refund')
                    AND
                        state in ('posted');
        """
        # Execute the SQL query
        self.env.cr.execute(query, (start_date, end_date))
        
        # Fetch the results
        rows = self.env.cr.dictfetchall()
        
        # Create a pandas DataFrame
        short_df_ingresos_odoo = pd.DataFrame(rows)
        
        df_ingresos_sat_odoo = pd.merge(short_df_ingresos, short_df_ingresos_odoo, on='Folio Odoo', how='outer')
        df_ingresos_sat_odoo['SubTotal'] = df_ingresos_sat_odoo['SubTotal'].astype(float).round(2)
        df_ingresos_sat_odoo['Total Odoo'] = df_ingresos_sat_odoo['Total Odoo'].astype(float).round(2)
        
        df_ingresos_sat_odoo['Validacion Monto'] = df_ingresos_sat_odoo.apply(lambda row: 'Valido' if row['SubTotal'] == row['Total Odoo'] else 'Invalido', axis=1)
        
        short_df_ingresos['SISTEMA'] = 'SAT'
        short_df_ingresos_odoo['SISTEMA'] = 'ODOO'
        short_df_ingresos_odoo.rename(columns={'UUID Odoo':'UUID'}, inplace=True)
        df_combinado = pd.concat([short_df_ingresos, short_df_ingresos_odoo], ignore_index=True)
        
        def etiquetar_duplicados(grupo):
            # Verificar que las columnas necesarias existen en el DataFrame
            required_columns = ['UUID', 'SISTEMA', 'Folio Odoo']
            for col in required_columns:
                if col not in grupo.columns:
                    raise ValueError(f"Falta la columna {col} en el DataFrame")

            # Contar las repeticiones de cada valor en 'UUID' dentro del grupo
            conteo_uuid = grupo['UUID'].value_counts()
            
            # Inicializar la columna 'EMPAREJAMIENTO' con 'CORRECTO' por defecto
            grupo['EMPAREJAMIENTO'] = 'CORRECTO' 
            
            # Marcar los registros como 'INCORRECTO' si el conteo de su 'UUID' es diferente de 2
            for idx in grupo.index:
                uuid = grupo.at[idx, 'UUID']
                if pd.isna(uuid) or uuid not in conteo_uuid:
                    grupo.at[idx, 'EMPAREJAMIENTO'] = 'INCORRECTO'
                elif conteo_uuid[uuid] != 2:
                    grupo.at[idx, 'EMPAREJAMIENTO'] = 'INCORRECTO'
                    
            # Marcar los registros como 'DUPLICADO' si corresponde
            sat_count = (grupo['SISTEMA'] == 'SAT').sum()
            odoo_count = (grupo['SISTEMA'] == 'ODOO').sum()
            
            for idx in grupo.index:
                if grupo.at[idx, 'SISTEMA'] == 'SAT' and sat_count > 1:
                    grupo.at[idx, 'Folio Odoo'] = f"{grupo.at[idx, 'Folio Odoo']}"
                elif grupo.at[idx, 'SISTEMA'] == 'ODOO' and odoo_count > 1:
                    grupo.at[idx, 'Folio Odoo'] = f"{grupo.at[idx, 'Folio Odoo']}"
                    
            return grupo

        df_combinado['SubTotal'] = df_combinado['SubTotal'].astype(float).round(2)
        df_combinado['Total Odoo'] = df_combinado['Total Odoo'].astype(float).round(2)
        df_combinado = df_combinado.groupby('Folio Odoo').apply(etiquetar_duplicados).reset_index(drop=True)
        
        total_sat = df_combinado['SubTotal'].sum()
        total_sat
        
        total_odoo = df_combinado['Total Odoo'].sum()
        total_odoo
        
        diferencia = abs(total_sat - total_odoo)
        
        diferencia
        
        df_incorrecto = df_combinado[df_combinado['EMPAREJAMIENTO'] == 'INCORRECTO']
        df_incorrecto['Suma'] = df_incorrecto['SubTotal'].fillna(0) + df_incorrecto['Total Odoo'].fillna(0)
        total_incorrecto = df_incorrecto['Suma'].sum()
        total_incorrecto
        
        df_correcto = df_combinado[df_combinado['EMPAREJAMIENTO'] == 'CORRECTO']
        total_correcto = df_correcto['SubTotal'].sum()
        total_correcto  
        
        fp = io.BytesIO()
        # Guarda los DataFrames en el archivo Excel
        with pd.ExcelWriter(fp, engine='xlsxwriter') as writer:
            df_combinado.to_excel(writer, sheet_name='EMPAREJAMIENTO', index=False)
            df_incorrecto.to_excel(writer, sheet_name='NO EMPAREJADOS', index=False)
            short_df_ingresos.to_excel(writer, sheet_name='SAT', index=False)
            short_df_ingresos_odoo.to_excel(writer, sheet_name='ODOO', index=False)
        
        # Mueve el puntero al inicio del objeto BytesIO
        fp.seek(0)
        
        # Lee el contenido del objeto BytesIO y lo convierte a base64
        excel_base64 = base64.b64encode(fp.read()).decode('utf-8')
        attachment = self.env['ir.attachment'].create({
            'name': f'Conciliación F NC.xlsx',
            'type': 'binary',
            'datas': excel_base64,
            'store_fname': f'Conciliación F NC.xlsx',
            'mimetype': 'application/vnd.ms-excel',
            'res_model': self._name,
            'res_id': self.id,
        })
        self.attachment_ids = [(4, attachment.id)]
        return attachment

class OdooVsSatReconcilieCDP(models.Model):
    _name = 'odoo_vs_sat.reconcilie.cdp.sat.bancos'
    _description = 'Conciliación Notas de Crédito y Facturas'
    _rec_name = "name"  # Cambiar a 'name' para usar el nombre calculado como _rec_name
    start_date = fields.Date(string='Fecha de Inicio')
    end_date = fields.Date(string='Fecha Final')
    attachment_id = fields.Many2one('ir.attachment', string='Archivo Adjunto')
    name = fields.Char(string='Nombre', compute='_compute_rec_name', store=True)

    @api.depends('start_date', 'end_date')
    def _compute_rec_name(self):
        for record in self:
            record.name = record._get_rec_name()

    def _get_rec_name(self):
        if self.start_date and self.end_date:
            # Formatear las fechas con nombres de meses en español
            start_date_str = format_date(self.env, self.start_date)
            end_date_str = format_date(self.env, self.end_date)
            return f'Del {start_date_str} al {end_date_str}'
        return ''

    attachment_ids = fields.Many2many(
        'ir.attachment', 
        'reconcilie_cdp_sat_bancos_attachment_rel',  # Nombre de la tabla relacional
        'reconcilie_id',               # Campo que referencia a odoo_vs_sat.reconcilie
        'attachment_id',               # Campo que referencia a ir.attachment
        string='Archivos Adjuntos',
        required=False,
    )

    def reconcile(self):
        
        bank = base64.b64decode(self.attachment_ids.filtered(lambda a: a.name == "BANCOS.xlsx").datas)
        sat = base64.b64decode(self.attachment_ids.filtered(lambda b: b.name == "PAGOS SAT.xlsx").datas)
        
        if self.start_date and self.end_date:
            pass
        start_date = pd.to_datetime(self.start_date, errors='coerce').replace(hour=0, minute=0, second=0)
        end_date = pd.to_datetime(self.end_date, errors='coerce').replace(hour=23, minute=59, second=59)
        df_dict_bancos = pd.read_excel(BytesIO(bank))
        df_dict_bancos['FechaValor'] = df_dict_bancos['FechaValor'].astype(str)
        df_dict_bancos['FechaValor'] = df_dict_bancos['FechaValor'].str.replace('/', '-')
        df_dict_bancos = df_dict_bancos.applymap(lambda x: x.strip() if isinstance(x, str) else x)
        df_dict_bancos['BENEF/CTE'] = df_dict_bancos['BENEF/CTE'].str.upper()
        df_dict_bancos['BENEF/CTE'] = df_dict_bancos['BENEF/CTE'].str.strip()
        df_dict_bancos['FechaValor'] = pd.to_datetime(df_dict_bancos['FechaValor']).dt.date
        df_dict_bancos['Abono'] = df_dict_bancos['Abono'].astype(float).round(2)
        
        #Leer SAT
        
        df_dict_sat = pd.read_excel(BytesIO(sat))
        sin_duplicados = df_dict_sat.drop_duplicates(subset=['UUID'])
        sin_duplicados['Fecha pago'] = pd.to_datetime(sin_duplicados['Fecha pago'], errors='coerce')
        sin_duplicados['Fecha pago'] = sin_duplicados['Fecha pago'].apply(lambda x: x.replace(hour=0, minute=0, second=0) if pd.notna(x) else x)
        sin_duplicados['Fecha pago'] = sin_duplicados['Fecha pago'].dt.date
        filtered_df_dict_sat = sin_duplicados[
            (sin_duplicados['Fecha pago'] >= start_date) &
            (sin_duplicados['Fecha pago'] <= end_date)
        ]
        filtered_df_dict_sat['Folio Odoo'] = None
        
        
        import xmlrpc.client
        
        def get_odoo_invoices_by_uuids(uuids):
            url = 'http://192.168.1.2:8069'
            db = 'ZTYRES'
            username = 'roberto.mejia@ztyres.com'
            password = 'roberto.mejia@ztyres.com'
            
            # Conexión al servidor Odoo
            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
            uid = common.authenticate(db, username, password, {})
            
            if not uid:
                return "Autenticación fallida."
            
            # Conexión al objeto de Odoo
            models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
            
            # Consulta masiva de UUIDs
            invoice_data = models.execute_kw(db, uid, password,
                'account.move', 'search_read',
                [[['l10n_mx_edi_cfdi_uuid', 'in', uuids],['state', 'in', ['posted']]]],
                {'fields': ['l10n_mx_edi_cfdi_uuid']})
            
            # Crear un diccionario con los resultados encontrados
            odoo_invoices = {inv['l10n_mx_edi_cfdi_uuid']: inv['l10n_mx_edi_cfdi_uuid'] for inv in invoice_data}
            return odoo_invoices
        
        unique_uuids = filtered_df_dict_sat['UUID'].unique().tolist()
        odoo_uuids = get_odoo_invoices_by_uuids(unique_uuids)
        filtered_df_dict_sat['UUID Odoo'] = filtered_df_dict_sat['UUID'].map(odoo_uuids)
        
        def generar_folio(row):
            prefijo = row['Serie']
            numero = str(row['Folio']).zfill(5)
            folio = f"{prefijo}{numero}"
            return folio
        filtered_df_dict_sat.loc[:, 'Folio Odoo'] = filtered_df_dict_sat.apply(generar_folio, axis=1)
        #sin_duplicados.loc[:, 'Folio Odoo'] = sin_duplicados.apply(generar_folio, axis=1)
        
        #año-mes-día (YYYY-MM-DD). Cambiar en excel
        filtered_df_dict_bancos = df_dict_bancos[
            (df_dict_bancos['FechaValor'] >= start_date) &
            (df_dict_bancos['FechaValor'] <= end_date)
        ]
        
        bancos = filtered_df_dict_bancos
        sat = filtered_df_dict_sat
        sat['sat_id'] = range(1, len(sat) + 1)
        unicos_sat = sat[~sat.duplicated(subset=['Monto', 'Fecha pago','Folio Odoo'], keep=False)]#ID
        unicos_sat = unicos_sat.dropna(subset=['UUID Odoo'])
        bancos['bnk_id'] = range(1, len(bancos) + 1)
        df_combined = pd.merge(bancos,unicos_sat, left_on=['Abono', 'FechaValor'], right_on=['Monto', 'Fecha pago'], how='left')
        df_combined
        
        por_conciliar = df_combined[~df_combined['sat_id'].isin(sat['sat_id'])]
        
        conciliados = df_combined[df_combined['sat_id'].notna() & df_combined['bnk_id'].notna()]
        
        conciliados

        por_conciliar_sat = sat[~sat['sat_id'].isin(conciliados['sat_id'])]
        
        por_conciliar_sat
        
        fp = io.BytesIO()
        # Guarda los DataFrames en el archivo Excel
        with pd.ExcelWriter(fp, engine='xlsxwriter') as writer:
            conciliados.to_excel(writer, sheet_name='CONCILIADOS', index=False)
            por_conciliar.to_excel(writer, sheet_name='POR CONCILIAR BNK', index=False)
            por_conciliar_sat.to_excel(writer, sheet_name='POR CONCILIAR SAT', index=False)
            filtered_df_dict_sat.to_excel(writer, sheet_name='DB SAT', index=False)
            filtered_df_dict_bancos.to_excel(writer, sheet_name='DB BANCOS', index=False)
        
        # Mueve el puntero al inicio del objeto BytesIO
        fp.seek(0)
        
        # Lee el contenido del objeto BytesIO y lo convierte a base64
        excel_base64 = base64.b64encode(fp.read()).decode('utf-8')
        attachment = self.env['ir.attachment'].create({
            'name': f'Conciliación BNK.xlsx',
            'type': 'binary',
            'datas': excel_base64,
            'store_fname': f'Conciliación BNK.xlsx',
            'mimetype': 'application/vnd.ms-excel',
            'res_model': self._name,
            'res_id': self.id,
        })
        self.attachment_ids = [(4, attachment.id)]
        return attachment