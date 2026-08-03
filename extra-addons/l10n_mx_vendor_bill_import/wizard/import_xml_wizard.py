# -*- coding: utf-8 -*-
"""
import_xml_wizard.py  —  v3.2
==============================
Wizard para importar CFDI 4.0 desde la orden de compra en Odoo 16 Community.

Correcciones v3.2:
- Todos los Many2many de candidatos reemplazados por campos JSON + computed
  (evita conflictos de tablas intermedias en TransientModel que causan que
  solo se cree la primera línea del XML).
- POs se capturan antes del write() y se restauran si se pierden.
- Campo de respaldo purchase_order_ids_backup para sobrevivir al _reopen().
"""

import re
import base64
import json
import logging
import unicodedata
from lxml import etree
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TFD_NS = 'http://www.sat.gob.mx/TimbreFiscalDigital'
AMOUNT_TOLERANCE = 1.0


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers fuzzy
# ══════════════════════════════════════════════════════════════════════════════

def _norm(code):
    if not code:
        return ''
    code = code.strip().upper()
    code = unicodedata.normalize('NFKD', code)
    return ''.join(c for c in code if not unicodedata.combining(c))

def _strip_lz(code):
    m = re.match(r'^([A-Z]*)(\d+)([A-Z\d]*)$', code)
    if m:
        p, n, s = m.groups()
        return p + (n.lstrip('0') or '0') + s
    return code.lstrip('0') or code

def _strip_tz(code):
    m = re.match(r'^([A-Z\d]*?)(\d+)([A-Z]*)$', code)
    if m:
        p, n, s = m.groups()
        return p + (n.rstrip('0') or n) + s
    return code

def _variants(raw):
    code = _norm(raw)
    if not code:
        return []
    v = {code, _strip_lz(code), _strip_tz(code), _strip_lz(_strip_tz(code))}
    if code[0].isalpha():
        v.update([code[1:], _strip_lz(code[1:])])
    if code[-1].isalpha():
        v.update([code[:-1], _strip_tz(code[:-1])])
    if len(code) >= 2 and code[0].isalpha() and code[-1].isalpha():
        v.update([code[1:-1], _strip_lz(code[1:-1])])
    digits = re.sub(r'[^0-9]', '', code)
    if digits:
        v.update([digits, digits.lstrip('0') or '0'])
    return [x for x in v if x]

def _score(xml_code, candidates):
    nc = _norm(xml_code)
    ns = _strip_lz(_strip_tz(nc))
    nd = (re.sub(r'[^0-9]', '', nc).lstrip('0') or '0')
    scored = []
    for p in candidates:
        dc = _norm(p.default_code)
        ds = _strip_lz(_strip_tz(dc))
        dd = (re.sub(r'[^0-9]', '', dc).lstrip('0') or '0')
        s = 0
        if nc == dc:           s = 100
        elif ns == ds:         s = 80
        elif nd == dd and nd != '0': s = 60
        elif dc in nc or nc in dc:   s = 40
        elif abs(len(nc)-len(dc))==1 and (nc[:-1]==dc or nc[1:]==dc or dc[:-1]==nc or dc[1:]==nc):
            s = 50
        if s:
            scored.append((s, p))
    if not scored:
        return None, []
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[0][0]
    tops = [p for s, p in scored if s == top]
    if top >= 80 and len(tops) == 1:
        return tops[0], [p for _, p in scored]
    return None, [p for _, p in scored]


# ══════════════════════════════════════════════════════════════════════════════
#  Split: distribución de una línea XML entre varios POs
# ══════════════════════════════════════════════════════════════════════════════

class ImportXmlSplit(models.TransientModel):
    """
    Sub-línea: asigna una cantidad del concepto XML a una línea de pedido concreta.
    La suma de todos los splits de una línea debe igualar la cantidad del XML.
    """
    _name  = 'import.xml.split'
    _description = 'Distribución de cantidad XML por pedido'

    line_id   = fields.Many2one('import.xml.line', ondelete='cascade', required=True)
    wizard_id = fields.Many2one(
        'import.xml.wizard',
        string='Wizard',
        ondelete='cascade',
        store=True,
        readonly=True,
        index=True,
    )

    # ── Pedido / línea ────────────────────────────────────────────────────────
    purchase_line_id = fields.Many2one(
        'purchase.order.line',
        string='Línea de Pedido',
        required=True,
    )
    purchase_order_id = fields.Many2one(
        related='purchase_line_id.order_id',
        string='Pedido',
        readonly=True,
        store=False,
    )

    # IDs de líneas candidatas del producto en JSON
    po_candidates_json = fields.Char(readonly=True)
    # IDs de los pedidos de compra del wizard (para domain en vista)
    wizard_po_order_ids = fields.Char(readonly=True)

    # Computed para domain
    po_candidate_line_ids = fields.Many2many(
        'purchase.order.line',
        compute='_compute_po_cands',
        string='Candidatas',
    )

    @api.depends('po_candidates_json', 'wizard_po_order_ids')
    def _compute_po_cands(self):
        for rec in self:
            # Prioridad 1: candidatos específicos del producto
            if rec.po_candidates_json:
                try:
                    ids = json.loads(rec.po_candidates_json)
                    if ids:
                        rec.po_candidate_line_ids = [(6, 0, ids)]
                        continue
                except Exception:
                    pass
            # Prioridad 2: todas las líneas de los POs del wizard
            if rec.wizard_po_order_ids:
                try:
                    po_ids = json.loads(rec.wizard_po_order_ids)
                    if po_ids:
                        lines = rec.env['purchase.order.line'].search([
                            ('order_id', 'in', po_ids)
                        ])
                        rec.po_candidate_line_ids = [(6, 0, lines.ids)]
                        continue
                except Exception:
                    pass
            rec.po_candidate_line_ids = [(5,)]

    # ── Cantidades ────────────────────────────────────────────────────────────
    qty_to_receive = fields.Float('A recibir', digits=(16, 0), required=True)
    qty_pending_po = fields.Float(
        'Pendiente PO',
        compute='_compute_qty_pending',
        store=False,
        digits=(16, 0),
    )

    @api.depends('purchase_line_id')
    def _compute_qty_pending(self):
        for rec in self:
            if rec.purchase_line_id:
                rec.qty_pending_po = (
                    rec.purchase_line_id.product_qty
                    - rec.purchase_line_id.qty_received
                )
            else:
                rec.qty_pending_po = 0.0

    @api.onchange('purchase_line_id')
    def _onchange_purchase_line(self):
        if self.purchase_line_id and self.line_id:
            pending   = self.purchase_line_id.product_qty - self.purchase_line_id.qty_received
            already   = sum(s.qty_to_receive for s in self.line_id.split_ids if s != self)
            remaining = self.line_id.cantidad - already
            self.qty_to_receive = min(pending, max(remaining, 0.0))
        self._recalc_line()

    @api.onchange('qty_to_receive')
    def _onchange_qty_to_receive(self):
        self._recalc_line()

    def _recalc_line(self):
        """Recalcula qty_distributed/remaining en la línea padre en tiempo real."""
        if not self.line_id:
            return
        dist = sum(
            s.qty_to_receive for s in self.line_id.split_ids
        )
        self.line_id.qty_distributed = dist
        self.line_id.qty_remaining   = self.line_id.cantidad - dist
        self.line_id.distribution_ok = abs(self.line_id.cantidad - dist) < 0.001


# ══════════════════════════════════════════════════════════════════════════════
#  Línea principal (un registro por <Concepto> del XML)
# ══════════════════════════════════════════════════════════════════════════════

class ImportXmlLine(models.TransientModel):
    _name = 'import.xml.line'
    _description = 'Línea de importación XML CFDI'

    wizard_id = fields.Many2one('import.xml.wizard', ondelete='cascade')

    # ── Datos del XML ─────────────────────────────────────────────────────────
    no_identificacion = fields.Char('Cód. XML',        readonly=True)
    descripcion       = fields.Char('Descripción XML', readonly=True)
    cantidad          = fields.Float('Cantidad XML',   readonly=True, digits=(16, 0))
    valor_unitario    = fields.Float('P. Unit. XML',   readonly=True, digits=(16, 6))
    importe           = fields.Float('Importe XML',    readonly=True, digits=(16, 2))
    taxes_json        = fields.Char(readonly=True)
    numero_pedimento  = fields.Char(readonly=True)

    # ── Producto ──────────────────────────────────────────────────────────────
    product_state = fields.Selection([
        ('ok',     'Asignado'),
        ('manual', 'Selección manual'),
        ('new',    'Crear producto'),
    ], default='manual', string='Estado')

    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        domain=[('purchase_ok', '=', True)],
    )

    # Candidatos en JSON + computed (evita tabla M2M que rompe el loop)
    candidate_ids_json = fields.Char(readonly=True)
    candidate_ids = fields.Many2many(
        'product.product',
        compute='_compute_candidates',
        string='Candidatos',
    )

    @api.depends('candidate_ids_json')
    def _compute_candidates(self):
        for rec in self:
            if rec.candidate_ids_json:
                try:
                    rec.candidate_ids = [(6, 0, json.loads(rec.candidate_ids_json))]
                except Exception:
                    rec.candidate_ids = [(5,)]
            else:
                rec.candidate_ids = [(5,)]

    create_product   = fields.Boolean('¿Crear?')
    new_product_name = fields.Char('Nombre nuevo producto')
    new_product_code = fields.Char('Referencia interna')

    # ── Líneas de PO candidatas en JSON + computed ────────────────────────────
    po_candidates_json = fields.Char(readonly=True)
    po_candidate_line_ids = fields.Many2many(
        'purchase.order.line',
        compute='_compute_po_candidate_line_ids',
        string='Líneas PO candidatas',
    )

    @api.depends('po_candidates_json')
    def _compute_po_candidate_line_ids(self):
        for rec in self:
            if rec.po_candidates_json:
                try:
                    rec.po_candidate_line_ids = [(6, 0, json.loads(rec.po_candidates_json))]
                except Exception:
                    rec.po_candidate_line_ids = [(5,)]
            else:
                rec.po_candidate_line_ids = [(5,)]

    # ── Distribución ──────────────────────────────────────────────────────────
    split_ids = fields.One2many('import.xml.split', 'line_id', string='Distribución')

    qty_distributed = fields.Float(
        'Total distribuido', compute='_compute_dist', store=True, digits=(16, 0))
    qty_remaining = fields.Float(
        'Por distribuir',   compute='_compute_dist', store=True, digits=(16, 0))
    distribution_ok = fields.Boolean(compute='_compute_dist', store=True)

    @api.depends('split_ids.qty_to_receive', 'cantidad')
    def _compute_dist(self):
        for rec in self:
            dist = sum(rec.split_ids.mapped('qty_to_receive'))
            rec.qty_distributed = dist
            rec.qty_remaining   = rec.cantidad - dist
            rec.distribution_ok = abs(rec.cantidad - dist) < 0.001

    warning = fields.Char('Advertencia', readonly=True)

    def action_open_distribution(self):
        """Abre el form de distribución de esta línea en un popup."""
        self.ensure_one()
        view = self.env.ref(
            'l10n_mx_vendor_bill_import.view_import_xml_line_dist_form',
            raise_if_not_found=False,
        )
        return {
            'type': 'ir.actions.act_window',
            'name': 'Distribución — %s' % (self.descripcion or self.no_identificacion or ''),
            'res_model': 'import.xml.line',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': view.id if view else False,
            'target': 'new',
            'flags': {'mode': 'edit'},
        }

    def action_save_distribution(self):
        """Guarda los splits y regresa al wizard principal."""
        self.ensure_one()
        # Forzar recálculo
        dist = sum(self.split_ids.mapped('qty_to_receive'))
        self.qty_distributed = dist
        self.qty_remaining   = self.cantidad - dist
        self.distribution_ok = abs(self.cantidad - dist) < 0.001
        # Reabrir el wizard padre
        return {
            'type': 'ir.actions.act_window',
            'name': _('Importar Factura XML CFDI 4.0'),
            'res_model': 'import.xml.wizard',
            'res_id': self.wizard_id.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # ── onchanges ────────────────────────────────────────────────────────────
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_state = 'ok'
            self.create_product = False
            self._refresh_po_candidates()
        else:
            self.product_state = 'manual'

    @api.onchange('create_product')
    def _onchange_create_product(self):
        if self.create_product:
            self.product_state = 'new'
            self.product_id    = False
            if not self.new_product_name:
                self.new_product_name = self.descripcion
            if not self.new_product_code:
                self.new_product_code = self.no_identificacion
        else:
            self.product_state = 'manual' if not self.product_id else 'ok'

    def _refresh_po_candidates(self):
        if not self.product_id or not self.wizard_id:
            return
        lines = self.env['purchase.order.line'].search([
            ('order_id', 'in', self.wizard_id.purchase_order_ids.ids),
            ('product_id', '=', self.product_id.id),
        ])
        self.po_candidates_json = json.dumps(lines.ids)


# ══════════════════════════════════════════════════════════════════════════════
#  Wizard principal
# ══════════════════════════════════════════════════════════════════════════════

class ImportXmlWizard(models.TransientModel):
    _name = 'import.xml.wizard'
    _description = 'Importar Factura CFDI 4.0'

    xml_file     = fields.Binary('Archivo XML', required=True)
    xml_filename = fields.Char('Nombre')

    # CFDI (readonly — se escriben via write() en action_analyze)
    cfdi_uuid     = fields.Char('UUID',             readonly=True)
    supplier_rfc  = fields.Char('RFC Proveedor',    readonly=True)
    supplier_name = fields.Char('Nombre Proveedor', readonly=True)
    receiver_rfc  = fields.Char('RFC Receptor',     readonly=True)
    invoice_date  = fields.Date('Fecha',             readonly=True)
    currency_code = fields.Char('Moneda',            readonly=True)
    total_amount  = fields.Float('Total XML',        readonly=True)
    folio         = fields.Char('Folio',             readonly=True)
    serie         = fields.Char('Serie',             readonly=True)

    origin_po_id  = fields.Many2one('purchase.order', string='Pedido de origen', readonly=True)

    purchase_order_ids = fields.Many2many(
        'purchase.order',
        'import_xml_wiz_po_rel',
        'wiz_id', 'po_id',
        string='Pedidos de Compra',
        domain="[('state', 'in', ['purchase','done']), ('invoice_status', '!=', 'invoiced')]",
    )
    # Respaldo en JSON para sobrevivir al _reopen()
    purchase_order_ids_backup = fields.Char(readonly=True)

    # Campo auxiliar: el cliente escribe aquí los IDs antes de llamar action_analyze
    # Se actualiza via onchange cada vez que cambia purchase_order_ids
    purchase_order_ids_json = fields.Char('POs JSON (aux)', readonly=False)

    line_ids  = fields.One2many('import.xml.line',  'wizard_id', string='Conceptos')

    state = fields.Selection([
        ('upload',  'Cargar XML'),
        ('resolve', 'Revisar conceptos'),
    ], default='upload')

    uuid_warning   = fields.Char(compute='_compute_uuid_warning',   store=False)
    amount_warning = fields.Char(compute='_compute_amount_warning', store=False)
    po_total       = fields.Float(compute='_compute_amount_warning', store=False)
    pending_count  = fields.Integer(compute='_compute_pending_count', store=False)

    @api.depends('cfdi_uuid')
    def _compute_uuid_warning(self):
        for rec in self:
            if rec.cfdi_uuid:
                ex = self.env['account.move'].search([
                    ('narration', 'ilike', rec.cfdi_uuid),
                    ('move_type', '=', 'in_invoice'),
                ], limit=1)
                rec.uuid_warning = (
                    '🚫 UUID ya registrado en %s (%s).' % (ex.name, ex.state)
                ) if ex else ''
            else:
                rec.uuid_warning = ''

    @api.depends('purchase_order_ids', 'total_amount')
    def _compute_amount_warning(self):
        for rec in self:
            if rec.purchase_order_ids:
                tot = sum(rec.purchase_order_ids.mapped('amount_total'))
                rec.po_total = tot
                diff = abs(rec.total_amount - tot)
                rec.amount_warning = (
                    '⚠ Diferencia de $%.2f entre XML (%.2f) y pedidos (%.2f).'
                    % (diff, rec.total_amount, tot)
                ) if diff > AMOUNT_TOLERANCE else ''
            else:
                rec.po_total       = 0.0
                rec.amount_warning = ''

    @api.depends('line_ids.product_state', 'line_ids.distribution_ok', 'line_ids.split_ids')
    def _compute_pending_count(self):
        for rec in self:
            rec.pending_count = len(rec.line_ids.filtered(
                lambda l: (
                    (l.product_state == 'manual' and not l.product_id and not l.create_product)
                    or (l.product_id and rec.purchase_order_ids and not l.split_ids)
                    or (l.split_ids and not l.distribution_ok)
                )
            ))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        po_id = self.env.context.get('default_origin_po_id')
        if po_id:
            res['origin_po_id']       = po_id
            res['purchase_order_ids'] = [(4, po_id)]
            po = self.env['purchase.order'].browse(po_id)
            res['supplier_rfc']  = po.partner_id.vat  or ''
            res['supplier_name'] = po.partner_id.name or ''
        return res

    @api.onchange('purchase_order_ids')
    def _onchange_purchase_order_ids(self):
        """Mantiene purchase_order_ids_json sincronizado.
        Este campo persiste en DB y es leído por action_analyze."""
        self.purchase_order_ids_json = json.dumps(self.purchase_order_ids.ids)

    @api.onchange('xml_file')
    def _onchange_xml_file(self):
        if not self.xml_file:
            return
        try:
            self._parse_xml()
        except UserError as e:
            return {'warning': {'title': _('Error XML'), 'message': str(e)}}
        except Exception as e:
            return {'warning': {'title': _('Error inesperado'), 'message': str(e)}}

    # ── Parser ────────────────────────────────────────────────────────────────

    def _parse_cfdi_root(self):
        raw = base64.b64decode(self.xml_file)
        if raw.startswith(b'\xef\xbb\xbf'):
            raw = raw[3:]
        try:
            root = etree.fromstring(raw)
        except etree.XMLSyntaxError as e:
            raise UserError(_('XML inválido: %s') % e)

        tag = root.tag
        if 'sat.gob.mx/cfd' not in tag:
            raise UserError(_('No parece un CFDI válido. Tag: %s') % tag)

        ns = tag.split('}')[0].lstrip('{')
        C  = '{%s}' % ns

        if root.get('Version', '') != '4.0':
            raise UserError(_('Solo se soporta CFDI 4.0. Encontrado: %s') % root.get('Version'))
        if root.get('TipoDeComprobante', '') != 'I':
            raise UserError(_('Solo facturas de ingreso (I). Tipo: %s') % root.get('TipoDeComprobante'))

        emisor   = root.find(f'{C}Emisor')
        receptor = root.find(f'{C}Receptor')

        uuid = ''
        comp = root.find(f'{C}Complemento')
        if comp is not None:
            tfd = comp.find(f'{{{TFD_NS}}}TimbreFiscalDigital')
            if tfd is None:
                for child in comp:
                    if 'TimbreFiscalDigital' in child.tag:
                        tfd = child
                        break
            if tfd is not None:
                uuid = tfd.get('UUID', '')

        fecha_str = root.get('Fecha', '')
        fecha = fields.Date.from_string(fecha_str[:10]) if fecha_str else False

        header_vals = {
            'supplier_rfc':  emisor.get('Rfc', '')    if emisor   is not None else '',
            'supplier_name': emisor.get('Nombre', '')  if emisor   is not None else '',
            'receiver_rfc':  receptor.get('Rfc', '')  if receptor is not None else '',
            'invoice_date':  fecha,
            'currency_code': root.get('Moneda', 'MXN'),
            'total_amount':  float(root.get('Total', 0) or 0),
            'folio':         root.get('Folio', ''),
            'serie':         root.get('Serie', ''),
            'cfdi_uuid':     uuid,
        }
        return root, C, header_vals

    def _parse_xml(self):
        root, C, hv = self._parse_cfdi_root()
        for k, v in hv.items():
            setattr(self, k, v)

    def action_back_to_upload(self):
        self.ensure_one()
        self.line_ids.unlink()
        self.state = 'upload'
        return self._reopen()

    # ── Analizar XML ──────────────────────────────────────────────────────────

    def action_analyze(self):
        self.ensure_one()
        if not self.xml_file:
            raise UserError(_('Carga un archivo XML primero.'))

        # ── 1. Determinar POs con prioridad al campo JSON auxiliar ───────────────
        # El onchange escribe purchase_order_ids_json en el cliente antes de que
        # el RPC llegue al servidor, así que contiene los IDs reales del form
        # aunque el ORM haya perdido el Many2many al guardar.
        po_ids = []

        # Prioridad 1: campo JSON auxiliar (más confiable)
        if self.purchase_order_ids_json:
            try:
                po_ids = [int(x) for x in json.loads(self.purchase_order_ids_json) if x]
            except Exception:
                pass

        # Prioridad 2: Many2many en memoria (si el ORM lo conservó)
        if not po_ids:
            po_ids = list(self.purchase_order_ids.ids)

        # Prioridad 3: respaldo de ejecución anterior
        if not po_ids and self.purchase_order_ids_backup:
            try:
                po_ids = json.loads(self.purchase_order_ids_backup)
            except Exception:
                pass

        _logger.info('action_analyze: po_ids resueltos = %s', po_ids)

        # ── 2. Parsear CFDI y escribir encabezado en DB ──────────────────────────
        root, C, header_vals = self._parse_cfdi_root()
        header_vals['purchase_order_ids_backup'] = json.dumps(po_ids)
        header_vals['purchase_order_ids_json']   = json.dumps(po_ids)
        # Escribir POs explícitamente junto con el header para garantizar persistencia
        header_vals['purchase_order_ids'] = [(6, 0, po_ids)]
        self.write(header_vals)

        # ── 3. Verificar que quedaron bien ───────────────────────────────────────
        current_ids = list(self.purchase_order_ids.ids)
        if set(po_ids) != set(current_ids):
            _logger.warning('POs aún incorrectos tras write(). Forzando: %s', po_ids)
            self.env.cr.execute(
                "DELETE FROM import_xml_wiz_po_rel WHERE wiz_id = %s", (self.id,)
            )
            if po_ids:
                vals_list = [(self.id, pid) for pid in po_ids]
                self.env.cr.executemany(
                    "INSERT INTO import_xml_wiz_po_rel (wiz_id, po_id) VALUES (%s, %s)",
                    vals_list,
                )
            self.invalidate_recordset(['purchase_order_ids'])

        po_ids = list(self.purchase_order_ids.ids)
        _logger.info('action_analyze: po_ids finales en DB = %s', po_ids)

        conceptos = root.find(f'{C}Conceptos')
        if conceptos is None:
            raise UserError(_('No se encontró Conceptos en el XML.'))

        # 5. Limpiar líneas previas
        self.line_ids.unlink()

        partner = self._find_partner()

        # 6. Crear una línea por cada <Concepto>
        for c in conceptos.findall(f'{C}Concepto'):
            taxes = []
            imp_node = c.find(f'{C}Impuestos')
            if imp_node is not None:
                for t in (imp_node.find(f'{C}Traslados') or []):
                    taxes.append({
                        'type': 'traslado',
                        'impuesto':    t.get('Impuesto', ''),
                        'tipo_factor': t.get('TipoFactor', ''),
                        'tasa':        float(t.get('TasaOCuota', 0) or 0),
                    })
                for r in (imp_node.find(f'{C}Retenciones') or []):
                    taxes.append({
                        'type': 'retencion',
                        'impuesto':    r.get('Impuesto', ''),
                        'tipo_factor': r.get('TipoFactor', ''),
                        'tasa':        float(r.get('TasaOCuota', 0) or 0),
                    })

            info_ad   = c.find(f'{C}InformacionAduanera')
            no_id     = c.get('NoIdentificacion', '')
            desc      = c.get('Descripcion', '')
            cantidad  = float(c.get('Cantidad', 1) or 1)
            v_unit    = float(c.get('ValorUnitario', 0) or 0)
            importe   = float(c.get('Importe', 0) or 0)
            pedimento = info_ad.get('NumeroPedimento', '') if info_ad is not None else ''

            product, candidates, prod_state = self._resolve_product(
                no_id, desc, partner, po_ids
            )
            po_line_ids, po_warning = self._get_po_candidate_lines(product, po_ids)

            xml_line = self.env['import.xml.line'].create({
                'wizard_id':          self.id,
                'no_identificacion':  no_id,
                'descripcion':        desc,
                'cantidad':           cantidad,
                'valor_unitario':     v_unit,
                'importe':            importe,
                'numero_pedimento':   pedimento,
                'taxes_json':         json.dumps(taxes),
                'product_id':         product.id if product else False,
                'candidate_ids_json': json.dumps([p.id for p in candidates]),
                'product_state':      prod_state,
                'po_candidates_json': json.dumps(po_line_ids),
                'warning':            po_warning,
                'new_product_name':   desc,
                'new_product_code':   no_id,
            })

            if product and po_line_ids:
                self._create_auto_splits(xml_line, po_line_ids, cantidad)

        self.write({'state': 'resolve'})
        return self._reopen()

    def _get_po_candidate_lines(self, product, po_ids):
        if not product or not po_ids:
            return [], ''
        lines = self.env['purchase.order.line'].search([
            ('order_id', 'in', po_ids),
            ('product_id', '=', product.id),
        ])
        if not lines:
            return [], '⚠ Producto no encontrado en los pedidos seleccionados.'
        warning = ''
        if len(lines) > 1:
            warning = (
                '⚠ Producto en %d líneas/pedidos. Distribuye la cantidad entre ellas.'
                % len(lines)
            )
        return lines.ids, warning

    def _create_auto_splits(self, xml_line, po_line_ids, cantidad_xml):
        po_lines = self.env['purchase.order.line'].browse(po_line_ids)
        cands_json = json.dumps(po_line_ids)

        pending_map = {}
        for pol in po_lines:
            pending = pol.product_qty - pol.qty_received
            if pending > 0:
                pending_map[pol] = pending

        wizard_po_json = json.dumps(
            xml_line.wizard_id.purchase_order_ids.ids if xml_line.wizard_id else []
        )
        if not pending_map:
            # Todos los POs ya tienen todo recibido — no crear splits con 0
            # La línea quedará en amarillo para que el usuario decida qué hacer
            _logger.info(
                'Línea "%s": todos los POs tienen qty_received completa, sin splits automáticos.',
                xml_line.descripcion
            )
            return

        if len(pending_map) == 1:
            pol, pending = list(pending_map.items())[0]
            self.env['import.xml.split'].create({
                'line_id':             xml_line.id,
                'wizard_id':           xml_line.wizard_id.id,
                'purchase_line_id':    pol.id,
                'qty_to_receive':      min(cantidad_xml, pending),
                'po_candidates_json':  cands_json,
                'wizard_po_order_ids': wizard_po_json,
            })
            return

        # Múltiples POs: crear filas en 0 para que el usuario distribuya manualmente
        for pol in pending_map:
            self.env['import.xml.split'].create({
                'line_id':             xml_line.id,
                'wizard_id':           xml_line.wizard_id.id,
                'purchase_line_id':    pol.id,
                'qty_to_receive':      0,
                'po_candidates_json':  cands_json,
                'wizard_po_order_ids': wizard_po_json,
            })

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Importar Factura XML CFDI 4.0'),
            'res_model': 'import.xml.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # ── Confirmar ─────────────────────────────────────────────────────────────

    def action_confirm(self):
        self.ensure_one()

        if self.uuid_warning:
            raise UserError(
                _('El UUID ya fue importado.\n%s') % self.uuid_warning
            )

        # Recalcular distribución desde DB para evitar valores stale
        line_ids = self.line_ids.ids
        splits_by_line = {}
        if line_ids:
            all_sp = self.env['import.xml.split'].search([('line_id', 'in', line_ids)])
            for sp in all_sp:
                lid = sp.line_id.id
                splits_by_line.setdefault(lid, []).append(sp)

        errors = []
        for line in self.line_ids:
            if not line.product_id and not line.create_product:
                errors.append(
                    '• "%s" (%s): falta producto.' % (line.descripcion, line.no_identificacion)
                )
                continue
            if self.purchase_order_ids and line.product_id:
                sp_list = splits_by_line.get(line.id, [])
                if not sp_list:
                    errors.append('• "%s": sin distribución de pedido.' % line.descripcion)
                else:
                    dist = sum(s.qty_to_receive for s in sp_list)
                    if abs(line.cantidad - dist) > 0.001:
                        errors.append(
                            '• "%s": distribuido (%.4f) ≠ XML (%.4f).'
                            % (line.descripcion, dist, line.cantidad)
                        )
                    for sp in sp_list:
                        pend = sp.purchase_line_id.product_qty - sp.purchase_line_id.qty_received
                        if sp.qty_to_receive > pend + 0.001:
                            errors.append(
                                '• "%s" / %s: a recibir (%.4f) > pendiente PO (%.4f).'
                                % (line.descripcion,
                                   sp.purchase_line_id.order_id.name,
                                   sp.qty_to_receive, pend)
                            )
        if errors:
            raise UserError(_('Corrige los siguientes problemas:\n\n') + '\n'.join(errors))

        for line in self.line_ids.filtered(lambda l: l.create_product and not l.product_id):
            self._create_product(line)

        pickings_done = self._validate_stock_moves()
        invoice       = self._create_and_confirm_invoice()

        for po in self.purchase_order_ids:
            po.message_post(
                body=_(
                    '📦 XML CFDI importado. Factura: <b>%s</b> | UUID: %s.<br/>'
                    'Recepciones: %s'
                ) % (invoice.name, self.cfdi_uuid or '—', ', '.join(pickings_done) or '—'),
                subtype_xmlid='mail.mt_note',
            )

        return {
            'type': 'ir.actions.act_window',
            'name': _('Factura de Proveedor'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_product(self, line):
        name = line.new_product_name or line.descripcion or line.no_identificacion or 'Producto'
        code = line.new_product_code or line.no_identificacion or ''
        tmpl = self.env['product.template'].create({
            'name':         name,
            'default_code': code,
            'type':         'product',
            'purchase_ok':  True,
            'sale_ok':      False,
            'uom_id':       self.env.ref('uom.product_uom_unit').id,
            'uom_po_id':    self.env.ref('uom.product_uom_unit').id,
        })
        partner = self._find_partner()
        if partner:
            self.env['product.supplierinfo'].create({
                'partner_id':      partner.id,
                'product_tmpl_id': tmpl.id,
                'product_code':    code,
                'price':           line.valor_unitario,
            })
        line.product_id    = tmpl.product_variant_ids[0]
        line.product_state = 'ok'

    def _validate_stock_moves(self):
        """
        Valida las recepciones de almacén.
        Lanza UserError si algo falla — NO suprime errores silenciosamente.
        """
        if not self.purchase_order_ids:
            return []

        # ── 1. Recopilar splits desde DB ──────────────────────────────────────
        # Buscar por line_id perteneciente al wizard (wizard_id puede no estar
        # escrito si create() no lo incluyó — búsqueda por line_id es más segura)
        line_ids = self.line_ids.ids
        if not line_ids:
            raise UserError(_('No hay conceptos en el wizard. Vuelve a analizar el XML.'))

        all_splits = self.env['import.xml.split'].search([
            ('line_id', 'in', line_ids),
            ('qty_to_receive', '>', 0),
            ('purchase_line_id', '!=', False),
        ])

        if not all_splits:
            raise UserError(_(
                'No hay distribución de pedidos configurada.\n'
                'En la tabla "Distribución por pedido" debes tener al menos una fila '
                'con cantidad mayor a cero.'
            ))

        # ── 2. Agrupar por picking ─────────────────────────────────────────────
        # picking_id → {move_id → qty}
        picking_map = {}   # {picking.id: {'picking': record, 'moves': {move.id: qty}}}
        errores_move = []

        for sp in all_splits:
            moves = self.env['stock.move'].search([
                ('purchase_line_id', '=', sp.purchase_line_id.id),
                ('state', 'not in', ['done', 'cancel']),
            ], order='id asc')

            if not moves:
                errores_move.append(
                    '• %s / %s: no se encontró movimiento de almacén pendiente.'
                    % (sp.line_id.descripcion or sp.line_id.no_identificacion,
                       sp.purchase_line_id.order_id.name)
                )
                continue

            # Tomar el primer move (el que corresponde a la recepción principal)
            move = moves[0]
            picking = move.picking_id
            if not picking:
                errores_move.append(
                    '• %s: el movimiento de almacén no tiene recepción asignada.'
                    % (sp.line_id.descripcion or sp.line_id.no_identificacion)
                )
                continue

            pid = picking.id
            if pid not in picking_map:
                picking_map[pid] = {'picking': picking, 'moves': {}}
            mid = move.id
            picking_map[pid]['moves'][mid] = (
                picking_map[pid]['moves'].get(mid, 0.0) + sp.qty_to_receive
            )

        if errores_move:
            raise UserError(_(
                'No se puede validar el almacén:\n\n%s\n\n'
                'Verifica que los pedidos tienen recepciones pendientes.'
            ) % '\n'.join(errores_move))

        # ── 3. Validar cada picking ────────────────────────────────────────────
        done_pickings = []

        for pid, data in picking_map.items():
            picking   = data['picking']
            move_qtys = data['moves']

            if picking.state in ('done', 'cancel'):
                continue

            # Confirmar y asignar
            if picking.state == 'draft':
                picking.action_confirm()
            if picking.state in ('confirmed', 'waiting', 'partially_available'):
                picking.action_assign()

            # Fijar qty_done en cada move
            for mid, qty in move_qtys.items():
                move = self.env['stock.move'].browse(mid)
                # Eliminar move_line_ids automáticos y crear uno exacto
                move.move_line_ids.unlink()
                self.env['stock.move.line'].create({
                    'move_id':          move.id,
                    'picking_id':       picking.id,
                    'product_id':       move.product_id.id,
                    'product_uom_id':   move.product_uom.id,
                    'location_id':      move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'qty_done':         qty,
                })

            # Validar — el contexto immediate_transfer=True evita el wizard
            # de "¿Deseas procesar inmediatamente?"
            result = picking.with_context(
                skip_backorder=True,
                immediate_transfer=True,
            ).button_validate()

            # Si aún devuelve un wizard de backorder, procesarlo
            if isinstance(result, dict):
                model = result.get('res_model', '')
                res_id = result.get('res_id')
                if model == 'stock.backorder.confirmation' and res_id:
                    bo_wiz = self.env[model].browse(res_id)
                    if bo_wiz.exists():
                        bo_wiz.process_cancel_backorder()
                elif model == 'stock.immediate.transfer' and res_id:
                    it_wiz = self.env[model].browse(res_id)
                    if it_wiz.exists():
                        it_wiz.process()
                        # Después del immediate transfer puede venir backorder
                        result2 = picking.with_context(skip_backorder=True).button_validate()
                        if isinstance(result2, dict) and result2.get('res_model') == 'stock.backorder.confirmation':
                            bo2 = self.env['stock.backorder.confirmation'].browse(result2.get('res_id'))
                            if bo2.exists():
                                bo2.process_cancel_backorder()

            done_pickings.append(picking.name)

        return done_pickings

    def _create_and_confirm_invoice(self):
        partner  = self._find_partner()
        currency = self.env['res.currency'].search([('name', '=', self.currency_code)], limit=1)
        ref_parts = [p for p in [self.serie, self.folio] if p]
        ref = '-'.join(ref_parts) if ref_parts else (self.cfdi_uuid or '')

        narr = []
        if self.cfdi_uuid:
            narr.append('UUID: %s' % self.cfdi_uuid)
        if self.purchase_order_ids:
            narr.append('Pedidos relacionados: %s' % ', '.join(
                self.purchase_order_ids.mapped('name')
            ))

        main_po   = False
        extra_pos = self.env['purchase.order']
        if len(self.purchase_order_ids) == 1:
            main_po = self.purchase_order_ids[0]
        elif self.purchase_order_ids:
            main_po   = self.purchase_order_ids.sorted('amount_total', reverse=True)[0]
            extra_pos = self.purchase_order_ids - main_po

        invoice_vals = {
            'move_type':    'in_invoice',
            'partner_id':   partner.id if partner else False,
            'invoice_date': self.invoice_date or fields.Date.context_today(self),
            'currency_id':  currency.id if currency else self.env.company.currency_id.id,
            'ref':          ref,
            'narration':    '\n'.join(narr),
            'invoice_line_ids': [],
            **({'purchase_id': main_po.id} if main_po else {}),
        }

        for line in self.line_ids:
            if not line.product_id:
                continue
            tax_ids = self._find_taxes(json.loads(line.taxes_json or '[]'))
            desc = line.descripcion or '/'
            if line.numero_pedimento:
                desc += '\nPedimento: %s' % line.numero_pedimento

            if line.split_ids:
                for sp in line.split_ids:
                    if sp.qty_to_receive <= 0:
                        continue
                    lv = {
                        'product_id': line.product_id.id,
                        'name':       desc,
                        'quantity':   sp.qty_to_receive,
                        'price_unit': line.valor_unitario,
                        'tax_ids':    [(6, 0, tax_ids)],
                    }
                    if sp.purchase_line_id:
                        lv['purchase_line_id'] = sp.purchase_line_id.id
                    invoice_vals['invoice_line_ids'].append((0, 0, lv))
            else:
                invoice_vals['invoice_line_ids'].append((0, 0, {
                    'product_id': line.product_id.id,
                    'name':       desc,
                    'quantity':   line.cantidad,
                    'price_unit': line.valor_unitario,
                    'tax_ids':    [(6, 0, tax_ids)],
                }))

        invoice = self.env['account.move'].create(invoice_vals)

        if self.xml_file:
            self.env['ir.attachment'].create({
                'name':      self.xml_filename or ('%s.xml' % (self.cfdi_uuid or 'cfdi')),
                'type':      'binary',
                'datas':     self.xml_file,
                'res_model': 'account.move',
                'res_id':    invoice.id,
                'mimetype':  'application/xml',
            })

        invoice.action_post()

        for po in extra_pos:
            po.message_post(
                body=_(
                    '🧾 Factura <b>%s</b> creada desde XML CFDI (UUID: %s).<br/>'
                    'PO principal: <b>%s</b>.'
                ) % (invoice.name, self.cfdi_uuid or '—', main_po.name if main_po else '—'),
                subtype_xmlid='mail.mt_note',
            )

        return invoice

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _find_partner(self):
        P = self.env['res.partner']
        p = P.search([('vat', '=', self.supplier_rfc)], limit=1)
        if not p and self.supplier_rfc:
            p = P.search([('vat', 'ilike', self.supplier_rfc)], limit=1)
        if not p and self.supplier_name:
            p = P.search([('name', 'ilike', self.supplier_name)], limit=1)
        return p

    def _resolve_product(self, no_id, desc, partner, po_ids):
        Product = self.env['product.product']

        if po_ids and no_id:
            po_lines = self.env['purchase.order.line'].search([
                ('order_id', 'in', po_ids),
                '|',
                ('product_id.default_code', '=ilike', no_id.strip()),
                ('product_id.default_code', '=ilike', _norm(no_id)),
            ])
            if po_lines:
                prods = po_lines.mapped('product_id')
                if len(prods) == 1:
                    return prods[0], list(prods), 'ok'
                return None, list(prods), 'manual'

        if partner and no_id:
            sinfo = self.env['product.supplierinfo'].search([
                ('partner_id', '=', partner.id),
                ('product_code', '=ilike', no_id.strip()),
            ], limit=5)
            if len(sinfo) == 1:
                prod = sinfo[0].product_id or sinfo[0].product_tmpl_id.product_variant_ids[:1]
                if prod:
                    return prod, [prod], 'ok'
            elif len(sinfo) > 1:
                prods = [
                    s.product_id or s.product_tmpl_id.product_variant_ids[:1]
                    for s in sinfo
                ]
                return None, [p for p in prods if p], 'manual'

        if no_id:
            exact = Product.search([('default_code', '=ilike', no_id.strip())], limit=5)
            if len(exact) == 1:
                return exact[0], [exact[0]], 'ok'
            if len(exact) > 1:
                return None, list(exact), 'manual'

            vs = _variants(no_id)
            cands = Product
            for v in vs:
                if v:
                    cands |= Product.search([('default_code', '=ilike', v)], limit=10)
            if not cands:
                for v in vs:
                    if v and len(v) >= 3:
                        cands |= Product.search([('default_code', 'ilike', v)], limit=20)
            if cands:
                best, ranked = _score(no_id, cands)
                if best:
                    return best, ranked, 'ok'
                if ranked:
                    return None, ranked, 'manual'

        return None, [], 'manual'

    def _find_taxes(self, taxes_data):
        Tax = self.env['account.tax']
        ids = []
        for t in taxes_data:
            tipo        = t.get('type', '')
            impuesto    = t.get('impuesto', '')
            tipo_factor = t.get('tipo_factor', '')
            tasa        = t.get('tasa', 0)
            if tipo == 'traslado' and impuesto == '002':
                if tipo_factor == 'Exento':
                    found = Tax.search([
                        ('type_tax_use', '=', 'purchase'),
                        ('amount', '=', 0),
                        ('amount_type', '=', 'percent'),
                    ], limit=1)
                else:
                    found = Tax.search([
                        ('type_tax_use', '=', 'purchase'),
                        ('amount', '=', round(tasa * 100, 2)),
                        ('amount_type', '=', 'percent'),
                    ], limit=1)
                if found:
                    ids.append(found.id)
            elif tipo == 'retencion':
                found = Tax.search([
                    ('type_tax_use', '=', 'purchase'),
                    ('amount', '=', -round(tasa * 100, 2)),
                    ('amount_type', '=', 'percent'),
                ], limit=1)
                if found:
                    ids.append(found.id)
        return ids
