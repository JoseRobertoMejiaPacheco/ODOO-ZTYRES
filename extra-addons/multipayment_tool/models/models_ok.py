# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DATOS FIJOS DE LA NOTA DE CRÉDITO (ids de esta base de datos)
# ---------------------------------------------------------------------------
# Producto usado en la línea de la NC de bonificación.
NC_PRODUCT_ID = 50785

# Impuesto de venta aplicado a la NC (IVA 16%). La tasa se lee del propio
# impuesto con compute_all(), ya no se divide entre 1.16 en duro: así el total
# con impuestos cuadra exactamente con el importe capturado.
NC_TAX_ID = 2

# Forma de pago del CFDI de egreso: 11 = Condonación.
NC_PAYMENT_METHOD_ID = 11

# Uso de CFDI: G02 = Devoluciones, descuentos o bonificaciones.
NC_USAGE = 'G02'

# Valor del campo Selection creado con Studio (x_studio_tipo). Es un Selection,
# así que esto tiene que ser la CLAVE de la opción; si no coincide se busca por
# etiqueta y, si tampoco existe, la NC se genera sin ese campo en vez de
# reventar con ValueError.
NC_STUDIO_TIPO = 'Bonificación'
# ---------------------------------------------------------------------------


# region Account Move
class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_payment_info(self):
        aml_ids = self.line_ids.filtered(
            lambda l: l.account_id.account_type in (
                'asset_receivable', 'liability_payable')
        ).ids

        if not aml_ids:
            return []

        query = '''
            SELECT
                part.debit_amount_currency AS amount,
                part.credit_move_id AS counterpart_line_id
            FROM account_partial_reconcile part
            WHERE part.debit_move_id IN %s

            UNION ALL

            SELECT
                part.credit_amount_currency AS amount,
                part.debit_move_id AS counterpart_line_id
            FROM account_partial_reconcile part
            WHERE part.credit_move_id IN %s
        '''

        self.env['account.partial.reconcile'].flush_model([
            'debit_move_id', 'credit_move_id', 'debit_amount_currency',
            'credit_amount_currency'
        ])
        self._cr.execute(query, (tuple(aml_ids), tuple(aml_ids)))
        result = self._cr.dictfetchall()

        # payment_previus_line move_type entry
        # credit_notes_previus_line out_refund
        payment_previus = []
        nc_previus = []
        if self.move_type == 'out_invoice':
            nc_previus.append((0, 0, {
                'move_id': self.id,
                'move_detailed_line_ids': [],
                'payment_origin': 'prev',
                'amount_to_apply': 0.0,
                'payment_name': self.move_type,
            }))
        for r in result:
            aml = self.env['account.move.line'].browse(r['counterpart_line_id'])

            if aml and aml.move_id and aml.move_id.id:
                detail_lines = []
                product_lines = aml.move_id.invoice_line_ids.filtered(
                    lambda line: line.display_type == 'product' and line.debit > 0.0
                )

                for product_line in product_lines:
                    if product_line:
                        detail_lines.append((0, 0, {
                            'name': product_line.name,
                            'amount_taxed': product_line.debit,
                        }))

                if aml.move_id.move_type == 'out_refund':
                    nc_previus.append((0, 0, {
                        'move_id': aml.move_id.id,
                        'move_detailed_line_ids': detail_lines,
                        'payment_origin': 'prev',
                        'amount_to_apply': r.get('amount', 0),
                        'payment_name': aml.move_id.move_type,
                    }))

                elif aml.move_id.move_type == 'entry':
                    payment_previus.append((0, 0, {
                        'move_id': aml.move_id.id,
                        'move_detailed_line_ids': detail_lines,
                        'payment_origin': 'prev',
                        'amount_to_apply': r.get('amount', 0),
                        'payment_name': aml.move_id.move_type,
                    }))

        return {'payments': nc_previus + payment_previus}
# endregion


class ModuleName(models.Model):
    _name = 'multipayment_tool.discount'
    _description = 'Descuento preconfigurado para notas de crédito'
    name = fields.Char(string='Descuento')
    discount = fields.Integer(string='Porcentaje de descuento')


class DetailedLine(models.Model):
    _name = 'multipayment_tool.detail_line'
    _description = 'Línea de detalle del documento'
    _rec_name = 'tag_name'
    tag_name = fields.Char(compute='_compute_tag_name')

    name = fields.Char(string='Etiqueta')
    amount_taxed = fields.Float(string='Monto')
    payment_id = fields.Many2one('multipayment_tool.payments')

    @api.depends('name', 'amount_taxed', 'payment_id')
    def _compute_tag_name(self):
        for record in self:
            record.tag_name = f'{record.name} ${record.amount_taxed}'


# -----------------------------------------
# Clase base para modelos con campos similares
# -----------------------------------------
class _MoveCommonFields(models.AbstractModel):
    _name = 'multipayment_tool.abstract_move'
    _description = 'Campos comunes para modelos relacionados a movimientos'
    move_id = fields.Many2one('account.move', string='Movimiento')
    move_type = fields.Selection(related='move_id.move_type', string='Tipo de Movimiento', store=True, readonly=True)
    move_date = fields.Date(related='move_id.date', string='Fecha', store=True)
    move_amount_total = fields.Monetary(related='move_id.amount_total', string='Monto Total', store=True)
    move_amount_residual = fields.Monetary(related='move_id.amount_residual', string='Saldo', store=True)
    currency_id = fields.Many2one(related='move_id.currency_id', string='Moneda')


class paymentsform(models.Model):
    _name = 'multipayment_tool.payment_form'
    _description = 'Formulario de aplicación de pago por factura'
    _rec_name = 'partner_id'

    payments_line_id = fields.Many2one(comodel_name='apply_out_invoice.payments_line', string='Payment Line')
    payment_ids = fields.One2many('multipayment_tool.payments', 'payment_form_id', string='Payments')
    invoice_amount_total = fields.Monetary(compute='_compute_amounts', string='Total Factura')
    total_payments = fields.Monetary(compute='_compute_amounts', string='Total de Pagos Previos')
    total_nc = fields.Monetary(compute='_compute_amounts', string='Total de NC Previas')
    amount_residual = fields.Monetary(compute='_compute_amounts', string='Saldo')
    payment_amount_pending = fields.Monetary(compute='_compute_amounts', string='Pendiente por aplicar')
    currency_id = fields.Many2one(
        'res.currency', string='Moneda', compute='_compute_currency_id', store=True)
    elapsed_days = fields.Char(compute='_compute_elapsed_days', string='Días transcurridos')
    payment_id = fields.Many2one(related='payments_line_id.payment_id_to_apply.payment_id', string='Pago')
    payment_amount = fields.Monetary(related='payments_line_id.payment_id_to_apply.payment_id.amount', string='Pago')
    partner_id = fields.Many2one(related='payments_line_id.payment_id_to_apply.partner_id', string='Cliente')
    invoice_id = fields.Many2one(related='payments_line_id.invoice_id', string='Factura')

    @api.depends('payments_line_id.payment_id_to_apply.currency_id')
    def _compute_currency_id(self):
        """Antes la moneda era siempre la de la compañía por defecto, aunque el
        pago fuera en otra."""
        for record in self:
            record.currency_id = (
                record.payments_line_id.payment_id_to_apply.currency_id
                or self.env.company.currency_id
            )

    @api.depends('payment_ids')
    def _compute_elapsed_days(self):
        for record in self:
            payment_date = record.payments_line_id.payment_id_to_apply.payment_id.date
            date_due = record.payments_line_id.invoice_id.invoice_date_due

            if not payment_date or not date_due:
                record.elapsed_days = "Sin fecha definida"
                continue

            delta = (payment_date - date_due).days

            if delta == 0:
                record.elapsed_days = "Pagado a tiempo"
            elif delta > 0:
                record.elapsed_days = f"Pagado {delta} días después"
            else:
                record.elapsed_days = f"Pagado {abs(delta)} días antes"

    @api.depends('payment_ids.amount_to_apply', 'payment_ids.payment_name',
                 'payment_ids.payment_origin', 'currency_id')
    def _compute_amounts(self):
        for record in self:
            currency = record.currency_id or self.env.company.currency_id
            apm = record.payments_line_id.payment_id_to_apply
            record.invoice_amount_total = record.payments_line_id.invoice_id.amount_total
            record.total_payments = currency.round(sum(
                record.payment_ids
                .filtered(lambda l: l.payment_name == 'entry')
                .mapped('amount_to_apply')))
            record.total_nc = currency.round(sum(
                record.payment_ids
                .filtered(lambda l: l.payment_name == 'out_refund')
                .mapped('amount_to_apply')))
            record.amount_residual = currency.round(
                record.invoice_amount_total - record.total_payments - record.total_nc)
            applied_new = sum(
                apm.lines.payment_form_id.payment_ids
                .filtered(lambda l: l.payment_name == 'entry'
                          and l.payment_origin == 'new')
                .mapped('amount_to_apply'))
            record.payment_amount_pending = currency.round(
                apm.payment_id.amount - applied_new)

    def _check_amounts(self):
        """Antes era un `@api.constrains('payment_amount_pending')` sobre un
        campo NO almacenado: nunca se disparaba. Ahora se invoca explícitamente
        desde el flujo de aplicación."""
        for record in self:
            currency = record.currency_id or self.env.company.currency_id
            tolerance = record.payments_line_id.payment_id_to_apply._get_tolerance()
            if currency.compare_amounts(record.payment_amount_pending, -tolerance) < 0:
                raise ValidationError(_(
                    "Se está aplicando más de lo que trae el pago. "
                    "Excedente: %s", abs(record.payment_amount_pending)))
            if currency.compare_amounts(record.amount_residual, -tolerance) < 0:
                raise ValidationError(_(
                    "La factura %(inv)s quedaría sobrepagada por %(amt)s entre "
                    "pagos y notas de crédito.",
                    inv=record.payments_line_id.invoice_id.name or '',
                    amt=abs(record.amount_residual)))


class payments(models.Model):
    _name = 'multipayment_tool.payments'
    _description = 'Documento aplicado a la factura'
    _inherit = 'multipayment_tool.abstract_move'

    discount_id = fields.Many2one('multipayment_tool.discount', string='Porcentaje de Descuento')
    amount_to_apply = fields.Monetary(string='Pago')
    move_detailed_line_ids = fields.One2many('multipayment_tool.detail_line', 'payment_id', string="Líneas de detalle")

    payment_origin = fields.Selection(
        string='Origen',
        selection=[('prev', 'Previo'), ('new', 'Nuevo')], default='new')
    payment_name = fields.Selection(
        string='Documento',
        selection=[('entry', 'Pago'), ('out_refund', 'Nota de Crédito'), ('out_invoice', 'Factura de Cliente')])
    payment_form_id = fields.Many2one(comodel_name='multipayment_tool.payment_form', string='Payment Form')

    # ------------------------------------------------------------------
    # Nota de crédito manual
    # ------------------------------------------------------------------
    nc_mode = fields.Selection(
        string='Tipo de NC',
        selection=[
            ('discount', 'Descuento preconfigurado'),
            ('amount', 'Monto manual'),
            ('percent', 'Porcentaje manual'),
        ],
        default='discount',
        help="«Descuento preconfigurado» usa el catálogo de descuentos. "
             "«Monto» y «Porcentaje» permiten capturar la NC libremente.")
    nc_value = fields.Float(
        string='Valor NC',
        help="Importe fijo o porcentaje, según el tipo de NC seleccionado.")
    nc_base = fields.Selection(
        string='Base del %',
        selection=[('total', 'Total de la factura'), ('residual', 'Saldo de la factura')],
        default='total')
    nc_reason = fields.Char(
        string='Motivo de la NC',
        help="Obligatorio. Se usa como concepto de la línea de la nota de "
             "crédito y como referencia del documento.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_apm(self):
        """Registro `apply_out_invoice.payments` al que pertenece la línea."""
        self.ensure_one()
        return self.payment_form_id.payments_line_id.payment_id_to_apply

    def _get_currency(self):
        self.ensure_one()
        return (self.payment_form_id.currency_id
                or self.currency_id
                or self.env.company.currency_id)

    def _get_invoice_record(self):
        self.ensure_one()
        return self.payment_form_id.payment_ids.filtered(
            lambda l: l.payment_name == 'out_invoice')

    def _is_new_nc(self):
        self.ensure_one()
        return self.payment_name == 'out_refund' and self.payment_origin == 'new'

    # ------------------------------------------------------------------
    # Cálculo del importe de la NC
    # ------------------------------------------------------------------
    def _compute_nc_target_amount(self):
        """Importe objetivo de la NC según el modo, redondeado a la moneda.

        El cálculo anterior encadenaba tres `compute_all` con /1.16 en duro y
        sin redondear, lo que dejaba fracciones de centavo: otra fuente de las
        diferencias que impedían timbrar.
        """
        self.ensure_one()
        currency = self._get_currency()
        invoice = self._get_invoice_record()
        if not invoice:
            return 0.0

        if self.nc_mode == 'discount':
            if not self.discount_id:
                return 0.0
            base = invoice.move_amount_total
            amount = base * (self.discount_id.discount or 0) / 100.0
        elif self.nc_mode == 'percent':
            base = (invoice.move_amount_total if self.nc_base == 'total'
                    else abs(invoice.move_amount_residual))
            amount = base * (self.nc_value or 0.0) / 100.0
        else:  # 'amount'
            amount = self.nc_value or 0.0

        return currency.round(max(amount, 0.0))

    # ------------------------------------------------------------------
    # Conciliación
    # ------------------------------------------------------------------
    def _reconcile_nc(self):
        for record in self:
            if not record._is_new_nc():
                continue
            invoice = record._get_invoice_record()
            if not invoice or not record.move_id:
                continue
            currency = record._get_currency()
            apm = record._get_apm()

            # Antes se filtraba por `line.account_type`, que no existe en
            # account.move.line en Odoo 16; se usa el helper del módulo base.
            nc_credit_line = record.move_id.get_open_receivable_lines()[:1]
            invoice_debit_line = invoice.move_id.get_open_receivable_lines()[:1]
            if not nc_credit_line or not invoice_debit_line:
                continue

            # Se topa al saldo real de ambos apuntes para no sobre-conciliar.
            amount = currency.round(min(
                record.amount_to_apply or nc_credit_line.apm_residual(),
                nc_credit_line.apm_residual(),
                invoice_debit_line.apm_residual(),
            ))
            if currency.is_zero(amount):
                continue
            apm.sudo().create_partial_reconcile(
                credit_move_id=nc_credit_line.id,
                debit_move_id=invoice_debit_line.id,
                amount=amount,
            )

    def _reconcile_payment(self):
        for record in self:
            if not (record.payment_name == 'entry' and record.payment_origin == 'new'):
                continue
            invoice = record._get_invoice_record()
            if not invoice:
                continue
            currency = record._get_currency()
            apm = record._get_apm()
            credit_line = apm.payment_id.get_open_receivable_lines()[:1]
            debit_line = invoice.move_id.get_open_receivable_lines()[:1]
            if not credit_line or not debit_line:
                continue
            amount = currency.round(min(
                record.amount_to_apply,
                credit_line.apm_residual(),
                debit_line.apm_residual(),
            ))
            if currency.is_zero(amount):
                continue
            apm.sudo().create_partial_reconcile(
                credit_move_id=credit_line.id,
                debit_move_id=debit_line.id,
                amount=amount,
            )

    def _create_adjustment_entry(self):
        """Ajuste de la diferencia de centavos en la FACTURA.

        Antes:
            if 0.01 <= record.move_id.amount_residual <= 0.05:

        Ese tope de 0.05 es exactamente por lo que una diferencia de 0.07 nunca
        se ajustaba. Además la cuenta ('888.88.8888.8888.8888') y el diario
        (id=140) estaban en duro. Ahora se delega en el motor de ajuste del
        módulo base, con tolerancia y cuentas configurables.
        """
        for record in self:
            if not (record.payment_name == 'out_invoice'
                    and record.payment_origin == 'prev'):
                continue
            apm = record._get_apm()
            if not apm:
                continue
            target = record.move_id.get_open_receivable_lines()[:1]
            apm.settle_residual(target, _(
                "Ajuste por redondeo - %(inv)s / %(pay)s",
                inv=record.move_id.name or '',
                pay=apm.payment_id.name or ''))

    def _generate_edi_docs(self):
        for record in self:
            if record._is_new_nc() and record.move_id:
                docs = record.move_id.edi_document_ids.filtered(
                    lambda d: d.state in ('to_send', 'to_cancel')
                    and d.blocking_level != 'error')
                if docs:
                    docs._process_documents_web_services(with_commit=True)

    # ------------------------------------------------------------------
    # Creación de la nota de crédito
    # ------------------------------------------------------------------
    def _create_credit_notes(self):
        """Genera la NC. Antes sólo corría si había `discount_id`; ahora
        cualquiera de los tres modos (descuento, monto o porcentaje)."""
        for record in self:
            if not record._is_new_nc() or record.move_id:
                # Si el usuario eligió una NC existente, no se crea otra.
                continue
            record.ensure_one()
            record._check_nc_ready()

            invoice = record._get_invoice_record()
            invoice.ensure_one()
            currency = record._get_currency()
            amount = currency.round(record.amount_to_apply)
            if currency.is_zero(amount):
                continue

            tax = self.env['account.tax'].browse(NC_TAX_ID).exists()
            price_unit = amount
            if invoice.move_id.amount_tax > 0 and tax:
                # La tasa se toma del impuesto (antes se asumía 16% en duro).
                unit = tax.compute_all(
                    1.0, currency=currency, quantity=1.0,
                    partner=invoice.move_id.partner_id)
                factor = unit.get('total_included') or 1.0
                price_unit = amount / factor if factor else amount

            line_vals = {
                'product_id': NC_PRODUCT_ID,
                'quantity': 1,
                'name': record.nc_reason,
                'price_unit': price_unit,
            }
            if tax:
                line_vals['tax_ids'] = [(6, 0, tax.ids)]

            credit_note_vals = {
                'move_type': 'out_refund',
                'invoice_date': fields.Date.context_today(record).strftime(
                    DEFAULT_SERVER_DATE_FORMAT),
                'journal_id': invoice.move_id.journal_id.id,
                'currency_id': invoice.move_id.currency_id.id,
                'partner_id': invoice.move_id.partner_id.id,
                'partner_shipping_id': invoice.move_id.partner_id.id,
                'ref': record.nc_reason,
                'narration': record.nc_reason,
                'invoice_origin': invoice.move_id.name,
                'l10n_mx_edi_payment_method_id': NC_PAYMENT_METHOD_ID,
                'l10n_mx_edi_usage': NC_USAGE,
                'invoice_line_ids': [(0, 0, line_vals)],
            }

            move_fields = self.env['account.move']._fields
            # Campos que pueden no existir según la instalación (studio /
            # localización personalizada): se escriben sólo si están.
            origin_field = ('l10n_mx_edi_origin' if 'l10n_mx_edi_origin' in move_fields
                            else 'l10n_mx_edi_cfdi_origin'
                            if 'l10n_mx_edi_cfdi_origin' in move_fields else None)
            if origin_field and invoice.move_id.l10n_mx_edi_cfdi_uuid:
                credit_note_vals[origin_field] = \
                    f'01|{invoice.move_id.l10n_mx_edi_cfdi_uuid}'

            # x_studio_tipo es un campo Selection creado con Studio: hay que
            # escribir la CLAVE, no la etiqueta, o create() lanza ValueError.
            tipo_value = record._get_studio_tipo_value(move_fields)
            if tipo_value:
                credit_note_vals['x_studio_tipo'] = tipo_value

            generic = False
            if 'generic_edi' in move_fields:
                generic = invoice.move_id.generic_edi
                credit_note_vals['generic_edi'] = generic
            if generic and 'edi_vat_receptor' in move_fields:
                credit_note_vals['edi_vat_receptor'] = 'XAXX010101000'

            credit_note = self.env['account.move'].sudo().create(credit_note_vals)
            credit_note.sudo().action_post()
            record.move_id = credit_note.id

    def _get_studio_tipo_value(self, move_fields=None):
        """Resuelve el valor a escribir en `x_studio_tipo`.

        Es un campo Selection creado con Studio ("Tipo"). El código original
        escribía la cadena "Bonificación" directamente, lo que revienta con
        ValueError si esa no es la CLAVE del selection (Studio no siempre usa
        la etiqueta como clave). Aquí se acepta la clave o, si no coincide, se
        busca por etiqueta. Si no existe ninguna, no se escribe el campo en
        lugar de tumbar la generación de la NC.

        No se declara `studio_customization` en `depends` a propósito: es un
        módulo autogenerado por Studio y depender de él no es portable.
        """
        self.ensure_one()
        target = NC_STUDIO_TIPO
        move_fields = move_fields or self.env['account.move']._fields
        field = move_fields.get('x_studio_tipo')
        if not field:
            return False
        try:
            selection = field.get_description(self.env).get('selection') or []
        except Exception:
            return False
        keys = [option[0] for option in selection]
        if target in keys:
            return target
        by_label = [option[0] for option in selection if option[1] == target]
        if by_label:
            return by_label[0]
        _logger.warning(
            "multipayment_tool: '%s' no es un valor válido de x_studio_tipo "
            "(opciones: %s). La NC se genera sin ese campo.", target, keys)
        return False

    def _check_nc_ready(self):
        """El motivo es obligatorio y el importe debe ser positivo."""
        self.ensure_one()
        currency = self._get_currency()
        if not self.nc_reason or not self.nc_reason.strip():
            raise UserError(_(
                "Indique el motivo de la nota de crédito antes de aplicar el "
                "pago. Es obligatorio y se usa como concepto del CFDI."))
        if currency.compare_amounts(self.amount_to_apply, 0) <= 0:
            raise UserError(_(
                "El importe de la nota de crédito debe ser mayor a cero."))
        if self.nc_mode == 'discount' and not self.discount_id:
            raise UserError(_(
                "Seleccione el descuento preconfigurado o cambie el tipo de NC "
                "a monto o porcentaje."))

    # ------------------------------------------------------------------
    # Constraints y onchange
    # ------------------------------------------------------------------
    @api.constrains('nc_mode', 'nc_value', 'nc_reason', 'payment_name',
                    'payment_origin')
    def _check_nc_values(self):
        for record in self:
            if not record._is_new_nc():
                continue
            if record.nc_mode in ('amount', 'percent'):
                if record.nc_value <= 0:
                    raise ValidationError(_(
                        "El valor de la nota de crédito debe ser mayor a cero."))
                if record.nc_mode == 'percent' and record.nc_value > 100:
                    raise ValidationError(_(
                        "El porcentaje de la nota de crédito no puede ser "
                        "mayor a 100."))

    @api.ondelete(at_uninstall=False)
    def _check_delete_payment_prev(self):
        for rec in self:
            if rec.payment_origin == 'prev':
                raise UserError(_("No se puede eliminar un pago aplicado previamente."))

    @api.onchange('amount_to_apply', 'payment_name', 'payment_origin')
    def _onchange_anything(self):
        if self.payment_form_id:
            # solo para que el formulario padre refresque
            self.payment_form_id.payment_amount_pending = \
                self.payment_form_id.payment_amount_pending

    @api.onchange('nc_mode')
    def _onchange_nc_mode(self):
        for rec in self:
            if rec.nc_mode != 'discount':
                rec.discount_id = False
            else:
                rec.nc_value = 0.0
            rec.amount_to_apply = rec._compute_nc_target_amount()

    @api.onchange('discount_id', 'nc_value', 'nc_base')
    def onchange_discount_id(self):
        """Nombre conservado. Antes sólo manejaba `discount_id` y encadenaba
        tres `compute_all` con /1.16 en duro; ahora cubre los tres modos y
        redondea a la moneda."""
        for rec in self:
            if not rec._is_new_nc():
                continue
            rec.amount_to_apply = rec._compute_nc_target_amount()

    @api.onchange('payment_name', 'move_id')
    def _onchange_discount_id(self):
        for rec in self:
            currency = rec._get_currency()
            if currency.is_zero(rec.payment_form_id.payment_amount_pending) \
                    and currency.is_zero(rec.payment_form_id.amount_residual):
                raise UserError(_(
                    'No es posible agregar más líneas ya que el saldo es 0 por '
                    'aplicar o la factura está saldada'))

            rec.discount_id = False
            if rec.payment_name != rec.move_id.move_type:
                rec.move_id = False
            if rec.payment_name == 'out_invoice':
                raise UserError(_(
                    'Característica en desarrollo... no es posible agregar facturas'))
            if not rec.payment_name:
                return {'domain': {'move_id': [('id', 'in', -1)]}}
            if rec.payment_name == 'out_refund':
                # Notas de crédito con saldo
                return {
                    'domain': {
                        'move_id': [
                            ('move_type', '=', 'out_refund'),
                            ('payment_state', '!=', 'paid'),
                            ('amount_residual', '>', 0),
                            ('state', '=', 'posted'),
                            ('partner_id', 'in',
                             rec.payment_form_id.payments_line_id
                             .payment_id_to_apply.partner_id.ids),
                        ]
                    }
                }
            elif rec.payment_name == 'entry' and rec.payment_origin == 'new':
                # Pagos disponibles del contexto
                rec.move_id = rec.payment_form_id.payments_line_id \
                    .payment_id_to_apply.payment_id.move_id or False
                return {'domain': {'move_id': [('id', 'in', rec.move_id.ids)]}}
            return {}
