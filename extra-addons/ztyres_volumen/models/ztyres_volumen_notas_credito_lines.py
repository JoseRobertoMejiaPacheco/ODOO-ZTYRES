# -*- coding: utf-8 -*-

from odoo import models, fields, api
class ZtyresVolumenLines(models.Model):
    _name = 'ztyres_volumen.notas_credito_lines'
    _order = 'reward_percent desc,partner_id desc'
    _description = 'ztyres_volumen notas credito lines'
    partner_id = fields.Many2one('res.partner', string='Cliente')
    group_id = fields.Many2one('ztyres_volumen.group', string='Grupo')
    price_subtotal = fields.Float(string="Subtotal", digits=(16, 2))
    quantity = fields.Integer(string="Cantidad")
    price_subtotal_bs = fields.Float(string="Subtotal BS", digits=(16, 2))
    base = fields.Float(string="Base Para Cálculo")
    total_nc_untaxed = fields.Float(string="Total NC", digits=(16, 2))
    reward_percent = fields.Integer(string="Porcentaje de recompensa")
    nc_credit_id = fields.Many2one('account.move', string='NC') 
    definitive_nc_id = fields.Many2one('ztyres_volumen.notas_credito')
    rfc = fields.Char(string='RFC')
    sat_estatus = fields.Char(string='Sat')
    #MAYOREO,PROMOCIÓN,PROMOCIÓN DOT,OUTLET,LISTA PROMO DOT
    def _get_discount_percent(self, policy_line_ids, qty):
        # Recopila todos los descuentos posibles, planos, para los cuales
        # qty cumple con el límite inferior (lower_limit).
        valid_discounts = [
            line
            for discount_line in policy_line_ids
            for line in discount_line
            if qty >= line.lower_limit
        ]
        
        # Si hay descuentos válidos, retorna el máximo; si no, retorna 0.
        if valid_discounts:
            x = max(valid_discounts, key=lambda x: x.discount).discount
            return x
        return 0
    

    def _get_valid_qty(self,lines):
        return sum(
            line.quantity if line.move_id.move_type == 'out_invoice' else -line.quantity
            for line in lines
        )

    def _get_valid_amount(self,lines):
        return sum(
            line.price_subtotal if line.move_id.move_type == 'out_invoice' else -line.price_subtotal
            for line in lines
        )

    def _get_invalid_qty(self,lines):
        return sum(line.quantity for line in lines)
        
    def _get_invalid_amount(self,lines):
        return sum(line.price_subtotal for line in lines)
    
    def _get_nc_bs_amount(self,lines):
        return sum(line.price_subtotal for line in lines)
        
    
    def _valid_lines(self,partner_id,start_date,end_date,pricelist_ids):
        AccountMoveLine = self.env['account.move.line']
        return AccountMoveLine.search([
            ('move_id.move_type', 'in', ['out_invoice', 'out_refund']),
            ('move_id.state', '=', 'posted'),  # Solo movimientos confirmados
            ('product_id.detailed_type','in',['product']),
            ('display_type','in',['product']),
            ('sale_line_ids.list_origin','in',pricelist_ids),
            ('move_id.invoice_date','>=',start_date),
            ('move_id.invoice_date','<=',end_date),
            ('partner_id','in',partner_id.ids),
        ])

    def _invalid_lines(self,partner_id,start_date,end_date,pricelist_ids):
        AccountMoveLine = self.env['account.move.line']
        return AccountMoveLine.search([
            ('move_id.move_type', 'in', ['out_invoice', 'out_refund']),
            ('move_id.state', '=', 'posted'),  # Solo movimientos confirmados
            ('product_id.detailed_type','in',['product']),
            ('display_type','in',['product']),
            ('sale_line_ids.list_origin','not in',pricelist_ids),
            ('move_id.invoice_date','>=',start_date),
            ('move_id.invoice_date','<=',end_date),
            ('partner_id','in',partner_id.ids),
        ])


    def _nc_bridgestone(self,partner_id,start_date,end_date):
        AccountMoveLine = self.env['account.move.line']
        return AccountMoveLine.search([
            ('move_id.move_type', 'in', ['out_refund']),
            ('move_id.state', '=', 'posted'),  # Solo movimientos confirmados
            ('product_id.detailed_type','in',['service']),
            ('display_type','in',['product']),
            ('name','in',['Descuento B Premium 10%']),
            ('move_id.invoice_date','>=',start_date),
            ('move_id.invoice_date','<=',end_date),
            ('partner_id','in',partner_id.ids),
        ])
    
    def action_view_details(self):
        """Método vacío temporalmente"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Detalles',
            'res_model': 'ztyres_volumen.lines',
            'view_mode': 'tree',
            'context': {'group_by': ['partner_id', 'rfc', 'state', 'move_type']},
            'domain': [('definitive_nc_id', '=', self.definitive_nc_id.id),('partner_id','in',self.partner_id.ids)]
        }