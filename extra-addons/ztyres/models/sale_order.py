# -*- coding: utf-8 -*-
from odoo import models, fields, api,_
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from odoo.tools import (
    formatLang,

)
class SaleOrder(models.Model):
    _inherit = 'sale.order'
    partner_credit_limit_used = fields.Monetary(related='partner_id.credt_limit_used', readonly=True)
    partner_credit_limit_available = fields.Monetary(related='partner_id.credt_limit_available', readonly=True)    
    show_partner_credit_alert = fields.Boolean(compute='_compute_show_partner_credit_alert')
    partner_credit_limit = fields.Float(related='partner_id.credit_limit', readonly=True)
    partner_credit_amount_overdue = fields.Monetary(related='partner_id.credit_amount_overdue', readonly=True)
    sale_reason_cancel_id = fields.Many2many(comodel_name='ztyres.sale_reason_cancel', string='Motivo de Cancelación')
    payment_term_days = fields.Integer(compute='_compute_payment_term_days',string='Días de Crédito')
    keep = fields.Boolean(string='Mantener Pedido de Venta', default=False)
    is_expo = fields.Boolean(string='Es exportación?', default=False)
    unlock_financial = fields.Boolean(string='Excepcion de pedido', default=False,tracking=True)
    pricelist_locked = fields.Boolean(string="Lista de precios bloqueada", default=False)
    confirmation_date = fields.Datetime(string='Fecha de Confirmación', store=True, copy=False)
    
    @api.onchange('pricelist_id')
    def _check_pricelist_locked(self):
        # Si pricelist_locked es True, entonces se ha establecido una lista de precios anteriormente
        if self.pricelist_locked:
            # Se restaura el valor anterior para prevenir el cambio
            self.pricelist_id = self._origin.pricelist_id
            return {
                'warning': {
                    'title': _("Advertencia!"),
                    'message': _("Una vez seleccionada, no puedes cambiar la lista de precios, se restaurará a la lista seleccionada inicialmente."),
                }
            }
        else:
            # Se bloquea la lista de precios para futuros cambios
            self.pricelist_locked = True

    def _prepare_invoice(self):
        # Llamamos al método original para obtener el diccionario preparado
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        # Copiamos los términos y condiciones del pedido de venta a la factura
        invoice_vals['narration'] = self.note  # Asumiendo que `note` es el campo de términos y condiciones en sale.order
        return invoice_vals
    
    def _get_amount_confirmed_invoices(self):
        domain = [
        ('invoice_status','in',['no']),
        ('partner_id','in',self.partner_id.ids),
        ('x_studio_solicitud_de_embarques','in',['Si']),
        ('state','in',['posted'])
        ]
        orders = self.search(domain)
        if orders:
            return sum(orders.mapped('amount_total'))
        else:
            return 0.0       
    def _get_names_confirmed_invoices(self):
        domain = [
        ('invoice_status','in',['no']),
        ('partner_id','in',self.partner_id.ids),
        ('x_studio_solicitud_de_embarques','in',['Si']),
        ('state','in',['posted'])
        ]
        orders = self.search(domain)
        if orders:
            return orders.mapped('name')
        else:
            return 0.0             
    # def copy(self, default=None):
    #     # Agregar codigo de validacion aca
    #     raise UserError(_('No es posible duplicar un pedido de Venta'))
    
    def copy(self, default=None):
        self.ensure_one()

        new_order = super().copy(default)
        for line in new_order.order_line:
            if not line.product_id:
                continue
            line._compute_price_unit()

        return new_order
    
    def _lock_credit_warning_message(self,updated_credit):
        updated_credit = self._get_amount_confirmed_invoices()+updated_credit
        ''' Build the warning message that will be displayed in a yellow banner on top of the current record
            if the partner exceeds a credit limit (set on the company or the partner itself).
            :param record:                  The record where the warning will appear (Invoice, Sales Order...).
            :param updated_credit (float):  The partner's updated credit limit including the current record.
            :return (str):                  The warning message to be showed.
        '''
        partner_id = self.partner_id.commercial_partner_id
        
        if (partner_id.property_payment_term_id.id != 1) and (partner_id.credit_limit <= 0):
            raise UserError("No es posible confirmar el pedido, Verifique con finanzas")
        
        if not partner_id.credit_limit or updated_credit <= partner_id.credit_limit:
            return ''
        msg = _('%s alcanzó el límite de crédito de : %s\nTotal adeudado ',
                partner_id.name,
                formatLang(self.env, partner_id.credit_limit, currency_obj=self.company_id.currency_id))
        if updated_credit > partner_id.credit:
            msg += _('(incluido este documento)')
        msg += ': %s' % formatLang(self.env, updated_credit, currency_obj=self.company_id.currency_id)
        raise UserError(msg)
    

    def _onchange_check_customer_invoices(self):
        if float(self.partner_id.total_overdue_3_days) >= 1:
            raise UserError(_('Este cliente tiene facturas vencidas. $ %s Por favor, verifica su situación antes de proceder con el pedido de venta.'%(str(self.partner_id.total_overdue))))
    
    def cancel_old_quotation_picking(self):
        now = fields.Datetime.now()
        five_days_ago = now - timedelta(days=5)
        
        quotation_orders = self.search([
            ('keep', '!=', True),
            ('state', 'in', ['draft']),
            ('create_date', '<=', five_days_ago),
        ])    
        cancelled = []
        unreserved = []

        for order in quotation_orders:
            print (order.name)
            pickings = order.picking_ids.filtered(
                lambda p: (
                    p.state not in ('done', 'cancel')
                    and not (p.x_studio_related_field_Ksn7B or '').strip()
                )
            )
            details = []
            for p in pickings:
                for m in p.move_ids:
                    details.append({
                        'product': m.product_id.display_name,
                        'qty': m.product_uom_qty,
                        'location': m.location_id.display_name,
                    })

            if pickings:
                pickings.action_cancel()
            
            order.write({
                'sale_reason_cancel_id': [(4, 3)],
            })
            
            order._action_cancel()

            cancelled.append({
                'order': order.name,
                'partner': order.partner_id.display_name,
                'details': details,
            })
            
        # 📧 Enviar correo si hubo cambios
        if cancelled or unreserved:
            self._send_cancel_unreserve_email(cancelled, unreserved)
            
        sale_orders = self.search([
            ('keep', '!=', True),
            ('state', '=', 'sale'),
            ('confirmation_date', '!=', False),
            ('confirmation_date', '<=', five_days_ago),
        ])
            
        cancelled = []
        unreserved = []
        for order in sale_orders:
            product_lines = order.order_line.filtered(
                lambda l: l.product_id.type == 'product'
            )
            if not product_lines:
                continue

            ordered = sum(product_lines.mapped('product_uom_qty'))
            delivered = sum(product_lines.mapped('qty_delivered'))
            invoiced = sum(product_lines.mapped('qty_invoiced'))

            nothing_delivered = delivered == 0
            nothing_invoiced = invoiced == 0
            partially_delivered = 0 < delivered < ordered
            partially_invoiced = 0 < invoiced < ordered
            fully_delivered = delivered >= ordered
            fully_invoiced = invoiced >= ordered

            # 🟢 No tocar
            if fully_delivered or fully_invoiced:
                continue

            # 🔴 Cancelar todo
            if nothing_delivered and nothing_invoiced:
                pickings = order.picking_ids.filtered(
                    lambda p: p.state not in ('done', 'cancel')
                )

                details = []
                for p in pickings:
                    for m in p.move_ids:
                        details.append({
                            'product': m.product_id.display_name,
                            'qty': m.product_uom_qty,
                            'location': m.location_id.display_name,
                        })

                if pickings:
                    pickings.action_cancel()

                order._action_cancel()

                cancelled.append({
                    'order': order.name,
                    'partner': order.partner_id.display_name,
                    'details': details,
                })
                continue

            # 🟡 Liberar reserva
            if partially_delivered or partially_invoiced:
                moves = order.picking_ids.move_ids.filtered(
                    lambda m: m.state in ('assigned', 'confirmed')
                    and m.reserved_availability > 0
                )

                details = []
                for m in moves:
                    details.append({
                        'product': m.product_id.display_name,
                        'qty': m.reserved_availability,
                        'location': m.location_id.display_name,
                    })

                if moves:
                    moves._do_unreserve()
                    moves.write({'procure_method': 'make_to_order'})

                    unreserved.append({
                        'order': order.name,
                        'partner': order.partner_id.display_name,
                        'details': details,
                    })

        # 📧 Enviar correo si hubo cambios
        if cancelled or unreserved:
            self._send_cancel_unreserve_email(cancelled, unreserved)

    def _send_cancel_unreserve_email(self, cancelled, unreserved):
        body = "<h3>Resumen de pedidos afectados</h3>"

        if cancelled:
            body += "<h4>🔴 Pedidos cancelados</h4><ul>"
            for c in cancelled:
                body += f"<li><b>{c['order']}</b> — {c['partner']}<ul>"
                for d in c['details']:
                    body += (
                        f"<li>{d['product']} | Qty: {d['qty']} | "
                        f"Ubicación: {d['location']}</li>"
                    )
                body += "</ul></li>"
            body += "</ul>"

        if unreserved:
            body += "<h4>🟡 Reservas liberadas</h4><ul>"
            for u in unreserved:
                body += f"<li><b>{u['order']}</b> — {u['partner']}<ul>"
                for d in u['details']:
                    body += (
                        f"<li>{d['product']} | Qty: {d['qty']} | "
                        f"Ubicación: {d['location']}</li>"
                    )
                body += "</ul></li>"
            body += "</ul>"

        mail_values = {
            'subject': 'Odoo — Cancelación y liberación de reservas (Cotizaciones vencidas)',
            'body_html': body,
            'email_to': 'roberto.mejia@ztyres.com, rene.banuelos@ztyres.com, ricardodecoss@ztyres.com'#, @tuempresa.com',
        }

        self.env['mail.mail'].create(mail_values).send()

    def sale_approve_state_draft(self):
        for record in self:
            record.approve_state = 'draft'



    def sale_approve_state_confirm(self):
        for record in self:
            record.approve_state = 'confirm'            


    def _compute_payment_term_days(self):
        for record in self:
            record.payment_term_days = record.payment_term_id.line_ids.days


    def _compute_show_partner_credit_alert(self):
        for order in self:
            order.show_partner_credit_alert = True

    def _action_cancel_delete_picking_ids(self):
        res = super(SaleOrder, self).action_cancel()
        for order in self:    
            for picking in order.picking_ids:
                if picking.state in ['cancel']:
                    picking.sudo().unlink()     
        return res


    @api.onchange('pricelist_id')
    def onchange_pricelist_id(self):
        self.note = self.pricelist_id.terms

    def action_confirm(self):
        #TODO Check this validation
        if self.id == 60933:
            self.x_studio_val_credito =True
            self.x_studio_val_ventas = True
            self.x_studio_solicitud_de_embarques = 'Si'
            return super(SaleOrder, self).action_confirm()        

        if not self.payment_term_days > 0:
            if not self.x_studio_val_pago:
                raise UserError("Por favor verifique con finanzas el pago anticipado.")
        updated_credit = self.partner_id.commercial_partner_id.credit + (self.amount_total * self.currency_rate)
        if not self.unlock_financial:
            self._onchange_check_customer_invoices()
            self._lock_credit_warning_message(updated_credit)
        self.x_studio_val_credito =True
        self.x_studio_val_ventas = True
        self.x_studio_solicitud_de_embarques = 'Si'
        self.quotation_action_confirm()
        
        confirmation = datetime.now()
        self.write({'confirmation_date': confirmation})
        
        return super(SaleOrder, self).action_confirm()

    def action_draft(self):
        for order in self:            
            order.quotation_action_confirm()       
        return super(SaleOrder, self).action_draft()    

    def quotation_action_confirm(self):     
        # Validate sale policies again
        for order in self:
            for picking in order.picking_ids:
                # if picking.x_studio_embarque:
                #     raise UserError("El pedido ya ha sido embarcado.")
                if picking.state not in ['done']:
                    picking.do_unreserve()
                    picking.action_cancel()
                    picking.sudo().unlink()
        for line in self.order_line:
            line.with_context({'lots_ids':line.lots_ids.ids})._ztyres_action_launch_stock_rule()
    
    def action_cancel(self):
        self.x_studio_val_credito =False
        self.x_studio_val_pago =False
        self.x_studio_val_ventas = False
        self.x_studio_solicitud_de_embarques = False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Motivo de Cancelación',
            'res_model': 'ztyres.cancel_reason',
            'view_mode': 'form',            
            'target': 'new',
            'context' : {'sale_id':self}
        }

