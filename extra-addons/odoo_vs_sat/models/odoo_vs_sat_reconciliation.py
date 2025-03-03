# -*- coding: utf-8 -*-
import pandas as pd
from io import BytesIO
from odoo import models, fields, api
from odoo.tools import format_date  # Asegúrate de importar format_date
import base64
import io

import pandas as pd
import base64
import io
from io import BytesIO
from odoo import models, fields, api
from odoo.tools import format_date

class OdooVsSatReconciliation(models.Model):
    _name = 'odoo_vs_sat.reconcilie'
    _description = 'Conciliación Notas de Crédito y Facturas'
    _rec_name = "name"
    
    start_date = fields.Date(string='Fecha de Inicio')
    end_date = fields.Date(string='Fecha Final')
    attachment_id = fields.Many2one('ir.attachment', string='Archivo Adjunto')
    name = fields.Char(string='Nombre', compute='_compute_name', store=True)
    attachment_ids = fields.Many2many(
        'ir.attachment', 
        'reconcilie_attachment_rel',  # Nombre de la tabla relacional
        'reconcilie_id',               # Campo que referencia a odoo_vs_sat.reconcilie
        'attachment_id',               # Campo que referencia a ir.attachment
        string='Archivos Adjuntos',
        required=False,
    )
    
    @api.depends('start_date', 'end_date')
    def _compute_name(self):
        for record in self:
            record.name = record._generate_name()
    
    def _generate_name(self):
        if self.start_date and self.end_date:
            return f'Del {format_date(self.env, self.start_date)} al {format_date(self.env, self.end_date)}'
        return ''

    def reconcile(self):
        self.ensure_one()
        attachment = self.attachment_ids.filtered(lambda a: a.name == "FACTURAS NOTAS SAT.xlsx")
        if not attachment:
            return
        
        df_sat = pd.read_excel(BytesIO(base64.b64decode(attachment.datas)))
        df_sat['Fecha emision'] = pd.to_datetime(df_sat['Fecha emision'], errors='coerce')
        
        start_date = pd.to_datetime(self.start_date).replace(hour=0, minute=0, second=0)
        end_date = pd.to_datetime(self.end_date).replace(hour=23, minute=59, second=59)
        
        df_sat_filtered = df_sat[
            (df_sat['Fecha emision'].between(start_date, end_date)) &
            (df_sat['Tipo'].isin(['I', 'E']))
        ].copy()
        
        df_sat_filtered['Folio Odoo'] = df_sat_filtered['Serie'].astype(str) + df_sat_filtered['Folio'].astype(int).astype(str).str.zfill(5)
        df_sat_filtered['SubTotal'] = df_sat_filtered['SubTotal'] - df_sat_filtered['Descuento']
        
        df_sat_selected = df_sat_filtered[['Tipo', 'RFC receptor', 'Razon receptor', 'UUID', 'SubTotal', 'Total', 'Estado', 'Folio Odoo']]
        
        query = """
            SELECT
                partner_id AS "ID CLIENTE ODOO",
                currency_id AS "ID Moneda Odoo",
                name AS "Folio Odoo",
                invoice_date AS "Fecha Odoo",
                l10n_mx_edi_cfdi_uuid AS "UUID Odoo",
                amount_untaxed_signed AS "Total Odoo",
                amount_tax_signed AS "Iva Trasladado",
                state AS "Estado Odoo",
                CASE
                    WHEN move_type = 'out_refund' THEN 'E'
                    WHEN move_type = 'out_invoice' THEN 'I'
                END AS "Tipo"
            FROM account_move
            WHERE invoice_date BETWEEN %s AND %s
            AND move_type IN ('out_invoice', 'out_refund')
            AND state = 'posted';
        """
        self.env.cr.execute(query, (start_date, end_date))
        df_odoo = pd.DataFrame(self.env.cr.dictfetchall())
        df_odoo.rename(columns={'UUID Odoo': 'UUID'}, inplace=True)
        
        df_merged = pd.merge(df_sat_selected, df_odoo, on='Folio Odoo', how='outer')
        df_merged['SubTotal'] = df_merged['SubTotal'].astype(float).round(2)
        df_merged['Total Odoo'] = df_merged['Total Odoo'].astype(float).round(2)
        df_merged['Validacion Monto'] = df_merged.apply(lambda row: 'Valido' if row['SubTotal'] == row['Total Odoo'] else 'Invalido', axis=1)
        
        df_sat_selected['SISTEMA'] = 'SAT'
        df_odoo['SISTEMA'] = 'ODOO'
        df_combined = pd.concat([df_sat_selected, df_odoo], ignore_index=True)
        
        df_combined['EMPAREJAMIENTO'] = df_combined.groupby('UUID')['UUID'].transform(lambda x: 'CORRECTO' if x.count() == 2 else 'INCORRECTO')
        
        totals = {
            'Total SAT': df_combined['SubTotal'].sum(),
            'Total Odoo': df_combined['Total Odoo'].sum(),
            'Diferencia': abs(df_combined['SubTotal'].sum() - df_combined['Total Odoo'].sum())
        }
        
        df_incorrect = df_combined[df_combined['EMPAREJAMIENTO'] == 'INCORRECTO']
        df_incorrect['Suma'] = df_incorrect[['SubTotal', 'Total Odoo']].sum(axis=1)
        totals['Total Incorrecto'] = df_incorrect['Suma'].sum()
        totals['Total Correcto'] = df_combined[df_combined['EMPAREJAMIENTO'] == 'CORRECTO']['SubTotal'].sum()
        
        fp = io.BytesIO()
        with pd.ExcelWriter(fp, engine='xlsxwriter') as writer:
            df_combined.to_excel(writer, sheet_name='EMPAREJAMIENTO', index=False)
            df_incorrect.to_excel(writer, sheet_name='NO EMPAREJADOS', index=False)
            df_sat_selected.to_excel(writer, sheet_name='SAT', index=False)
            df_odoo.to_excel(writer, sheet_name='ODOO', index=False)
        
        fp.seek(0)
        attachment_data = base64.b64encode(fp.read()).decode('utf-8')
        attachment = self.env['ir.attachment'].create({
            'name': 'Conciliación F NC.xlsx',
            'type': 'binary',
            'datas': attachment_data,
            'store_fname': 'Conciliación F NC.xlsx',
            'mimetype': 'application/vnd.ms-excel',
            'res_model': self._name,
            'res_id': self.id,
        })
        
        self.attachment_ids = [(4, attachment.id)]
        return attachment