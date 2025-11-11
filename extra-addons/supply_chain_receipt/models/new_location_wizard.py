# models/wizard_add_location.py
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class AddLocationWizard(models.TransientModel):
    _name = 'supply_chain_receipt.add_location_wizard'
    _description = 'Wizard para Agregar Ubicaciones a la línea'

    receipt_line_id = fields.Many2one(
        'supply_chain_receipt.receipt_line',
        string='Línea de Recepción',
        required=True
    )
    product_id = fields.Many2one(
        'product.product',
        related='receipt_line_id.product_id',
        store=False, readonly=True
    )
    line_ids = fields.One2many(
        'supply_chain_receipt.add_location_wizard.line',
        'wizard_id',
        string='Capturas'
    )

    def action_confirm(self):
        """Crea las líneas O2M sin borrar las existentes."""
        self.ensure_one()
        LocationModel = self.env['supply_chain_receipt.location']
        vals_to_create = []
        for wline in self.line_ids:
            if not (wline.location_id and wline.lot_id and wline.product_uom_qty):
                raise UserError(_("Hay capturas incompletas. Revisa ubicación, lote y cantidad."))
            vals_to_create.append({
                'receipt_line_id': self.receipt_line_id.id,
                'location_id': wline.location_id.id,
                'lot_id': wline.lot_id.id,
                'product_uom_qty': wline.product_uom_qty,
            })
        if vals_to_create:
            LocationModel.create(vals_to_create)
            _logger.info("Wizard creó %s ubicaciones en la línea %s", len(vals_to_create), self.receipt_line_id.id)
        return {'type': 'ir.actions.act_window_close'}


class AddLocationWizardLine(models.TransientModel):
    _name = 'supply_chain_receipt.add_location_wizard.line'
    _description = 'Líneas del Wizard de Ubicaciones'

    wizard_id = fields.Many2one('supply_chain_receipt.add_location_wizard', required=True, ondelete='cascade')
    entry_text = fields.Char(
        string='Captura rápida',
        help="Formato: 'Ubicación Año Cantidad' (ej. '1-A-1 2025 50')"
    )
    location_id = fields.Many2one('stock.location', string='Ubicación')
    lot_id = fields.Many2one('stock.lot', string='Lote')
    product_uom_qty = fields.Float(string='Cantidad', digits='Product Unit of Measure')

    product_id = fields.Many2one(
        'product.product',
        related='wizard_id.product_id',
        store=False, readonly=True
    )

    @api.onchange('entry_text')
    def _onchange_entry_text(self):
        """Reutiliza el parser del modelo real para mantener una sola lógica."""
        if not self.entry_text:
            return
        parser = self.env['supply_chain_receipt.location']
        location, lot_str, qty = parser._parse_entry_text(self.entry_text)
        product = self.product_id
        if not product:
            raise UserError(_("No se pudo inferir el producto desde la línea."))

        lot = self.env['stock.lot'].search([
            ('name', '=', lot_str),
            ('product_id', '=', product.id)
        ], limit=1)
        if not lot:
            lot = self.env['stock.lot'].create({
                'name': lot_str,
                'product_id': product.id,
                'company_id': self.env.company.id,
            })
        self.location_id = location
        self.lot_id = lot
        self.product_uom_qty = qty
