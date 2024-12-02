from odoo import _, api, fields, models
from odoo.osv import expression

class Product(models.Model):
    _inherit = "product.product"
    
    estado_conteo_dot = fields.Selection(
        string='Estado de Conteo',
        selection=[('draft', 'Sin Contar'), ('done', 'Contado')],default='draft'
    )
    
    def cambiar_estado_conteo(self):
        for record in self:
            if record.estado_conteo_dot == 'done':
                record.estado_conteo_dot = 'draft'
            elif record.estado_conteo_dot == 'draft':
                record.estado_conteo_dot = 'done' 
                
    # def _get_domain_locations_new_custom(self, location_ids):
    #     locations = self.env['stock.location'].browse(location_ids)
    #     # TDE FIXME: should move the support of child_of + auto_join directly in expression
    #     loc_domain, dest_loc_domain = [], []
    #     # this optimizes [('location_id', 'child_of', locations.ids)]
    #     # by avoiding the ORM to search for children locations and injecting a
    #     # lot of location ids into the main query
    #     for location in locations:
    #         loc_domain = loc_domain and ['|'] + loc_domain or loc_domain
    #         loc_domain.append(('location_id.parent_path', '=like', location.parent_path + '%'))
    #         loc_domain.append(('location_id.vender','=',True))
    #         dest_loc_domain = dest_loc_domain and ['|'] + dest_loc_domain or dest_loc_domain
    #         dest_loc_domain.append(('location_dest_id.parent_path', '=like', location.parent_path + '%'))
    #         dest_loc_domain.append(('location_id.vender','=',True))

    #     return (
    #         loc_domain,
    #         dest_loc_domain + ['!'] + loc_domain if loc_domain else dest_loc_domain,
    #         loc_domain + ['!'] + dest_loc_domain if dest_loc_domain else loc_domain
    #     )
        
        
    def _get_domain_locations(self):
        '''
        Parses the context and returns a list of location_ids based on it.
        It will return all stock locations when no parameters are given
        Possible parameters are shop, warehouse, location, compute_child
        '''
        Warehouse = self.env['stock.warehouse']

        def _search_ids(model, values):
            ids = set()
            domain = []
            for item in values:
                if isinstance(item, int):
                    ids.add(item)
                else:
                    domain = expression.OR([[(self.env[model]._rec_name, 'ilike', item)], domain])
            if domain:
                ids |= set(self.env[model].search(domain).ids)
            return ids

        # We may receive a location or warehouse from the context, either by explicit
        # python code or by the use of dummy fields in the search view.
        # Normalize them into a list.
        location = self.env.context.get('location')
        if location and not isinstance(location, list):
            location = [location]
        warehouse = self.env.context.get('warehouse')
        if warehouse and not isinstance(warehouse, list):
            warehouse = [warehouse]
        # filter by location and/or warehouse
        if warehouse:
            w_ids = set(Warehouse.browse(_search_ids('stock.warehouse', warehouse)).mapped('view_location_id').ids)
            if location:
                l_ids = _search_ids('stock.location', location)
                location_ids = w_ids & l_ids
            else:
                location_ids = w_ids
        else:
            if location:
                location_ids = _search_ids('stock.location', location)
            else:
                location_ids = set(Warehouse.search([]).mapped('view_location_id').ids)
        context = bool(self.env.context.get('qty_custom')) or False
        res = self._get_domain_locations_new(location_ids) #if context==1 else self._get_domain_locations_new_custom(location_ids)
        return res