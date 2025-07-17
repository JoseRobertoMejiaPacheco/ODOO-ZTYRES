from odoo import models, fields, api
from odoo.exceptions import UserError

class UnappliedReceivablesReport(models.Model):
    _name = 'unapplied.receivables.report'
    _auto = False
    _description = 'Reporte de Cuentas por Cobrar No Aplicadas'
    
    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    move_id = fields.Many2one('account.move', string='Factura', readonly=True)
    move_type = fields.Selection([
        ('entry', 'Pago'),
        ('out_refund', 'Nota de crédito'),
    ], string='Tipo de Movimiento', readonly=True)
    date = fields.Date('Fecha de Movimiento', readonly=True)
    date_maturity = fields.Date('Fecha de Vencimiento', readonly=True)
    amount_residual_currency = fields.Monetary('Saldo Pendiente', readonly=True, currency_field='currency_id')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('posted', 'Publicado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', readonly=True)
    invoice_date = fields.Date('Fecha de la Factura', readonly=True)
    parent_state = fields.Selection([
        ('draft', 'Borrador'),
        ('posted', 'Publicado'),
        ('cancel', 'Cancelado'),
    ], string='Estado de la Factura', readonly=True)
    account_id = fields.Many2one('account.account', string='Cuenta', readonly=True)
    amount = fields.Monetary('Monto', readonly=True, currency_field='currency_id')
    
    currency_id = fields.Many2one('res.currency', string='Moneda', readonly=True)
    
    @property
    def _table_query(self):
        return '%s %s %s' % (self._select(), self._from(), self._where())
    
    @api.model
    def _select(self):
        return """
            SELECT 
                MIN(aml.id) AS id,
                rp.id AS partner_id,
                aml.move_id,
                am.move_type,
                aml.date,
                aml.date_maturity,
                aml.amount_residual_currency,
                am.state,
                am.invoice_date,
                aml.parent_state,
                aml.account_id,
                aml.currency_id,
                SUM(ROUND(aml.balance * ct.rate, ct.precision)) AS amount
        """
    
    @api.model
    def _from(self):
        return """
            FROM 
                account_move_line aml
            LEFT JOIN 
                account_account AS account_move_line__account_id 
                ON aml.account_id = account_move_line__account_id.id
            LEFT JOIN 
                (VALUES (1, 1.0, 2)) AS ct(company_id, rate, precision) 
                ON ct.company_id = aml.company_id
            LEFT JOIN 
                res_partner rp
                ON aml.partner_id = rp.id
            LEFT JOIN 
                account_move am
                ON aml.move_id = am.id
        """
    
    @api.model
    def _where(self):
        return """
            WHERE
                aml.parent_state = 'posted'
                AND am.state = 'posted'
                AND aml.company_id IN (1)
                AND (
                    aml.display_type NOT IN ('line_section', 'line_note') 
                    OR aml.display_type IS NULL
                )
                AND aml.date <= '2025-12-12'
                AND (
                    aml.date >= '2000-01-01'
                    OR account_move_line__account_id.include_initial_balance = TRUE
                )
                AND (
                    account_move_line__account_id.non_trade IS NULL 
                    OR account_move_line__account_id.non_trade = FALSE
                )
                AND account_move_line__account_id.account_type = 'asset_receivable'
                AND (
                    aml.credit != 0.0 
                    OR aml.debit != 0.0 
                    OR aml.amount_currency = 0.0
                )
                AND (
                    aml.journal_id IS NULL 
                    OR aml.journal_id NOT IN (4)
                )
            GROUP BY 
                aml.move_id,
                aml.move_name,
                aml.account_id,
                aml.amount_residual_currency,
                am.move_type,
                rp.id,
                rp.name,
                account_move_line__account_id.account_type,
                account_move_line__account_id.name,
                am.state,
                aml.parent_state,
                am.invoice_date,
                aml.date,
                aml.date_maturity,
                aml.currency_id
            HAVING 
                aml.amount_residual_currency <> 0 
                AND am.move_type IN ('entry','out_refund')
        """