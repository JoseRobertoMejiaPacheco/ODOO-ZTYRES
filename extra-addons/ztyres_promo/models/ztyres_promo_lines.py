# -*- coding: utf-8 -*-
"""Detalle auditable de las líneas consideradas durante el cálculo."""

from odoo import fields, models


class ZtyresPromoDetailLine(models.Model):
    _name = 'ztyres_promo.lines'
    _description = 'Detalle de cálculo de promoción'
    _order = 'partner_id, date, id'

    definitive_nc_id = fields.Many2one(
        'ztyres_promo.notas_credito',
        ondelete='cascade',
    )
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
    move_type = fields.Char(string='Tipo de movimiento')
    move_id = fields.Many2one('account.move', string='Documento')
    product_name = fields.Char(string='Producto')
    name = fields.Char(string='Descripción')
    product_id = fields.Many2one('product.template', string='Producto')
    product_code = fields.Char(string='Código')
    product_brand = fields.Char(string='Marca')
    date = fields.Date(string='Fecha')
    quantity = fields.Float(string='Cantidad')
    price_subtotal = fields.Float(string='Subtotal')
    partner_id = fields.Many2one('res.partner', string='Cliente')
    sale_origin = fields.Char(string='Origen de venta')
    list_origin = fields.Char(string='Lista de origen')
    state = fields.Selection(
        [
            ('valid', 'Válida'),
            ('invalid', 'Inválida'),
            ('partial', 'Parcial'),
        ],
        string='Estado',
    )
    rfc = fields.Char(string='RFC')
    missing_partner_vat = fields.Boolean(
        string='Falta RFC receptor',
        index=True,
    )
