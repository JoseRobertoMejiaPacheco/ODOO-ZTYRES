from datetime import datetime
import pytz
from odoo import _, api, fields, models
from odoo.exceptions import UserError

class SvlHistory(models.Model):
    _name = 'stock.valuation.layer.resume.history'
    _description = 'Historial de Valoración de Inventario'

    name = fields.Char(compute='_compute_name',store=True)
    state = fields.Selection(string='Estado', selection=[('draft', 'Borrador'), ('done', 'Guardado')],default='draft')
    active = fields.Boolean(default=True,string="Activo")

    def action_done(self):
        for record in self:
            if not record.svl_resume_ids:
                raise UserError(_('No puede guardar una valoración de inventario vacía :( '))

            record.state = 'done'

    def action_draft(self):
        for record in self:
            record.state = 'draft'

    def unlink(self):
        for record in  self:
            if record.state == 'done':
                raise UserError(_('Este registro solo se puede archivar :( '))
        res = super().unlink()
        return res

    @api.depends('inventory_datetime')
    def _compute_name(self):
        for record in self:
            if record.inventory_datetime:
                user_tz = self.env.user.tz or pytz.utc
                local = pytz.timezone(user_tz)
                inventory_datetime = datetime.strftime(pytz.utc.localize(record.inventory_datetime).astimezone(local),"%d/%m/%Y, %H:%M:%S")                         
                record.name = "Valoración de Inventario de %s"%(inventory_datetime)
    
    total_count = fields.Float(compute='_compute_total_count',store=True)
    
    @api.depends('svl_resume_ids')
    def _compute_total_count(self):
        for record in self:
            record.total_count = sum(record.svl_resume_ids.mapped('quantity') )        
    

    svl_resume_ids = fields.One2many('stock.valuation.layer.resume.line', inverse_name='svl_resume_history_id',ondelete='cascade')
    
    inventory_datetime = fields.Datetime(required=True)
    value_total = fields.Float(compute='_compute_value_total',store=True)

    def get_svl_resume_ids(self):
        
        return {
            'name': _('Lista'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.valuation.layer.resume.line',
            'domain': [('id', 'in', self.svl_resume_ids.ids)],
        }
        

    @api.depends('svl_resume_ids','inventory_datetime')
    def _compute_value_total(self):
        for record in self:
            record.value_total = sum(record.svl_resume_ids.mapped('value') )
    def open_at_date(self):
        self.svl_resume_ids.unlink()
        not_transit_domain = [('stock_move_id.location_id.usage', 'not in',['supplier']),('stock_move_id.location_dest_id.usage', 'not in',['transit']),('create_date', '<=', self.inventory_datetime), ('product_id.type', '=', 'product')]
        not_transit = self.env['stock.valuation.layer'].search(not_transit_domain)
        transit_domain = [('stock_move_id.location_id.usage', 'in',['supplier']),('stock_move_id.location_dest_id.usage', 'in',['transit']),('create_date', '<=', self.inventory_datetime), ('product_id.type', '=', 'product')]
        transit = self.env['stock.valuation.layer'].search(transit_domain)
        diferentes_ids = not_transit - transit
        groups = self.env['stock.valuation.layer'].read_group([('id','in',diferentes_ids.ids)], ['value:sum', 'quantity:sum'], ['product_id'])
        line_ids = self.svl_resume_ids.create(self.removekey(groups,'__domain')).ids
        self.svl_resume_ids = [(6, 0, line_ids) ]
        print(self.svl_resume_ids)

    def removekey(self,d, key):
        new_arr_vals = []
        for value in d:    
            value.update({'product_id':value['product_id'][0]})
            r = dict(value)
            del r[key]
            print(value)
            new_arr_vals.append(r)
        return new_arr_vals

