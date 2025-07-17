# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ZtyresExataLine(models.Model):
    _name = 'ztyres_exata.facturacion.line'

    sku_goodyear = fields.Char(string="SKU Goodyear")
    volume_vendas = fields.Integer(string="Volumen Ventas")
    faturamento_bruto = fields.Float(string="Total Ventas", digits=(16, 2))
    data_faturamento = fields.Date(string='Fecha factura')
    codigo_goodyear_distribuidor = fields.Char(string="Codigo goodyear distribuidor")
    id_cliente = fields.Integer(string="ID cliente")
    id_facturacion = fields.Many2one('ztyres_exata.facturacion')