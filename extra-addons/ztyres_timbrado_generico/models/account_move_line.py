# -*- coding: utf-8 -*-
"""Datos fiscales y comerciales congelados en la línea timbrada."""
from odoo import api, fields, models


class ZtyresVolumenGroup(models.Model):
    _name = 'ztyres_volumen.group'
    _description = 'Grupos'
    _order = 'name, id'

    name = fields.Char(string='Nombre del Grupo', index=True)
    partner_ids = fields.Many2many('res.partner', string='Clientes')
    partner_count = fields.Integer(
        string='Clientes', compute='_compute_partner_count'
    )

    @api.depends('partner_ids')
    def _compute_partner_count(self):
        for group in self:
            group.partner_count = len(group.partner_ids)

    @api.model
    def _map_partners_to_groups(self, partners):
        """Resuelve todos los clientes en una consulta y de forma estable."""
        if not partners:
            return {}
        groups = self.sudo().search([('partner_ids', 'in', partners.ids)])
        groups.mapped('partner_ids')
        direct = {}
        for group in groups:
            for partner_id in group.partner_ids.ids:
                direct.setdefault(partner_id, group)
        result = {}
        for partner in partners:
            group = direct.get(partner.id)
            if group:
                result[partner.id] = group
        return result

    @api.model
    def _get_group_for_partner(self, partner):
        if not partner:
            return self.browse()
        return self._map_partners_to_groups(partner).get(
            partner.id, self.browse()
        )


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    group_id = fields.Many2one(
        'ztyres_volumen.group', string='Grupo', readonly=True, copy=False,
        index=True, ondelete='restrict',
        help='Grupo del cliente congelado al calcular el RFC receptor.',
    )
    edi_vat_receptor = fields.Char(
        string='RFC receptor', readonly=True, copy=False, index=True,
        oldname='partner_vat',
        help='RFC receptor del CFDI, copiado al timbrar el documento.',
    )
