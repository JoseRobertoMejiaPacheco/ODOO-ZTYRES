# -*- coding: utf-8 -*-
"""
Resultado definitivo del cálculo: una línea por (cliente, RFC receptor).

Los algoritmos de tramos ya no viven aquí, viven en
`ztyres_promo.reward_engine`. Se conservan métodos delegadores porque
hay código externo que los llama por nombre.
"""

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare


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
    price_total = fields.Float(
        string='Subtotal (con IVA)',
        digits=(16, 2),
        compute='_compute_amounts_with_tax',
        store=True,
        help=(
            'Lo acumulado por el cliente, con IVA. Es la cifra que hay que '
            'comparar contra los niveles de la promoción, porque los '
            'límites Desde/Hasta se capturan con IVA.'
        ),
    )
    quantity = fields.Integer(string='Cantidad')
    total_nc_untaxed = fields.Float(string='Total NC', digits=(16, 2))
    total_nc_taxed = fields.Float(
        string='Total NC (con IVA)',
        digits=(16, 2),
        compute='_compute_amounts_with_tax',
        store=True,
        help=(
            'Lo que el cliente recibe de verdad. La nota de crédito se '
            'emite por el importe sin IVA y el timbrado se lo suma, así '
            'que esta es la cifra final del documento.'
        ),
    )

    @api.depends('price_subtotal', 'total_nc_untaxed')
    def _compute_amounts_with_tax(self):
        """Los dos montos anteriores, con IVA.

        Se guardan (store=True) y no se calculan al vuelo para que la
        vista de lista pueda sumarlos por columna, que es justo lo que se
        necesita en una tabla de resultados.

        La contra de guardarlos: si alguien cambia la tasa en
        `ztyres_promo.tier_amount_tax_rate` después de un cálculo, estas
        dos columnas quedan con la tasa vieja hasta el siguiente
        recálculo. Es el comportamiento correcto para un resultado ya
        emitido — refleja con qué tasa se pagó — pero conviene saberlo.
        """
        factor = self.env['ztyres_promo.reward_engine']._tier_tax_factor()
        for line in self:
            line.price_total = (line.price_subtotal or 0.0) * factor
            line.total_nc_taxed = (line.total_nc_untaxed or 0.0) * factor

    reward_percent = fields.Float(
        string='Porcentaje efectivo',
        # Ocho decimales. No es capricho: es la precisión con la que este
        # número, multiplicado por el subtotal, DEVUELVE el Total NC al
        # centavo, que es lo que se necesita para poder comprobarlo en
        # Excel o en la calculadora.
        #
        # Con el caso real (subtotal $1,337,501.34, NC $62,247.57):
        #
        #     2 dec  4.65          ->  62,193.81   faltan $53.76
        #     4 dec  4.654         ->  62,247.31   faltan  $0.26
        #     6 dec  4.654019      ->  62,247.57   cuadra
        #     8 dec  4.65401926    ->  62,247.57   cuadra
        #
        # Se eligieron 8 y no 6 por margen: el error de redondear el
        # porcentaje crece con el subtotal. Con 6 decimales, un
        # subtotal de 100 millones ya se desvía 50 centavos; con 8, medio
        # centavo. Mostrar menos decimales de los necesarios es lo que
        # hacía que la cuenta "no diera".
        digits=(16, 8),
        help=(
            'NC ÷ subtotal. En promociones por rin, con Key Sizes o con '
            'base en precios PMS no es un porcentaje capturado: es la '
            'mezcla de porcentajes de este cliente, y por eso trae tantos '
            'decimales.\n\n'
            'Multiplicado por el subtotal devuelve el Total NC al '
            'centavo: sirve para comprobar la cifra en Excel o en la '
            'calculadora. Use el valor completo, no el que se ve '
            'redondeado en el reporte.\n\n'
            'El importe que manda sigue siendo Total NC, que es la suma '
            'de los renglones. Para ver de dónde salió cada peso, la '
            'columna "Detalle del beneficio" trae cada grupo con su '
            'base, su porcentaje y su importe.'
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
            ('gift_card', 'Tarjeta de regalo'),
        ],
        string='Tipo de beneficio',
        default='percentage',
    )
    reward_fixed_amount = fields.Float(
        string='Monto fijo asignado',
        digits=(16, 2),
    )
    gift_card_amount = fields.Float(
        string='Tarjeta de regalo ($ con IVA)',
        digits=(16, 2),
        help=(
            'Valor de la tarjeta que le corresponde a este cliente/RFC, '
            'con IVA, tal como se le entrega.\n\n'
            'Va aparte de "Total NC" a propósito: si la tarjeta se entrega '
            'por fuera, el importe de NC es cero y sumar las dos columnas '
            'daría un total de notas de crédito que no existe.'
        ),
    )
    has_reward = fields.Boolean(
        string='Ganó recompensa',
        compute='_compute_has_reward',
        store=True,
        index=True,
        help=(
            'Verdadero únicamente cuando la recompensa correspondiente al '
            'tipo de promoción es mayor que cero al redondear a centavos.'
        ),
    )

    @api.depends('reward_type', 'total_nc_untaxed', 'gift_card_amount')
    def _compute_has_reward(self):
        for line in self:
            amount = (
                line.gift_card_amount
                if line.reward_type == 'gift_card'
                else line.total_nc_untaxed
            )
            line.has_reward = (
                float_compare(amount or 0.0, 0.0, precision_digits=2) > 0
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
