# -*- coding: utf-8 -*-
"""
Resultado definitivo del cálculo: una línea por (cliente, RFC receptor).

Los algoritmos de tramos ya no viven aquí, viven en
`ztyres_promo.reward_engine`. Se conservan métodos delegadores porque
hay código externo que los llama por nombre.
"""

from odoo import fields, models


class ZtyresPromoCreditNoteLine(models.Model):
    _name = 'ztyres_promo.notas_credito_lines'
    _description = 'Resultado de nota de crédito por promoción'
    _order = 'total_nc_untaxed desc, partner_id'

    partner_id = fields.Many2one('res.partner', string='Cliente')
    # group_id es la clave REAL de agrupación del cálculo (antes lo era
    # group_name). Lleva índice porque sobre él corre el read_group que
    # acumula por grupo, y ondelete='restrict' porque borrar un grupo no
    # debe alterar en silencio una nota de crédito ya calculada.
    group_id = fields.Many2one(
        'ztyres_volumen.group',
        string='Grupo',
        index=True,
        ondelete='restrict',
    )
    # Nombre del grupo AL MOMENTO del cálculo. No es un related: si
    # renombran el grupo, el detalle auditable debe seguir mostrando con
    # qué nombre se pagó.
    group_name = fields.Char(string='Nombre del grupo', index=True)
    price_subtotal = fields.Float(string='Subtotal', digits=(16, 2))
    quantity = fields.Integer(string='Cantidad')
    total_nc_untaxed = fields.Float(string='Total NC', digits=(16, 2))
    reward_percent = fields.Float(
        string='Porcentaje efectivo',
        digits=(16, 2),
        help=(
            'En promociones por rin no es un porcentaje configurado: es el '
            'resultado de dividir la NC entre el subtotal, porque cada rin '
            'aporta su propio porcentaje. Vea la columna Detalle.'
        ),
    )
    reward_detail = fields.Char(
        string='Detalle del beneficio',
        help='Cómo se compuso el importe: tramo alcanzado y aporte por rin.',
    )
    reward_type = fields.Selection(
        [
            ('percentage', 'Porcentaje'),
            ('fixed_amount', 'Monto fijo en NC'),
        ],
        string='Tipo de beneficio',
        default='percentage',
    )
    reward_fixed_amount = fields.Float(
        string='Monto fijo asignado',
        digits=(16, 2),
    )
    nc_credit_id = fields.Many2one('account.move', string='NC')
    definitive_nc_id = fields.Many2one(
        'ztyres_promo.notas_credito',
        ondelete='cascade',
        index=True,
    )
    rfc = fields.Char(string='RFC')
    sat_estatus = fields.Char(string='SAT')

    # ------------------------------------------------------------------
    # Delegadores hacia el motor de beneficios
    # ------------------------------------------------------------------
    @property
    def _engine(self):
        return self.env['ztyres_promo.reward_engine']

    def _get_policy_reward(self, policies, value, reward_type, quantity=None):
        return self._engine.tier_reward(policies, value, reward_type, quantity)

    def _get_discount_percent(self, policies, value):
        percent, _fixed = self._engine.tier_reward(
            policies,
            value,
            'percentage',
        )
        return percent

    def _get_monthly_volume_discount(self, policies, detailed_lines):
        return self._engine.monthly_volume_discount(policies, detailed_lines)

    # ------------------------------------------------------------------
    # Navegación
    # ------------------------------------------------------------------
    def action_view_details(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Detalles de %s' % (self.partner_id.display_name or ''),
            'res_model': 'ztyres_promo.lines',
            'view_mode': 'tree,form',
            'context': {
                'group_by': ['state', 'product_brand', 'move_type'],
            },
            'domain': [
                ('definitive_nc_id', '=', self.definitive_nc_id.id),
                ('partner_id', '=', self.partner_id.id),
                ('rfc', '=', self.rfc),
            ],
        }
