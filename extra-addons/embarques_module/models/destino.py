import csv
import unicodedata

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import file_open


class EmbarquesDestino(models.Model):
    """Destino logístico: zona, rangos admitidos y costo de paquetería.

        Estado | Ciudad logística | Zona | Rangos permitidos | Paquetería

    El nombre operativo es libre. Estado, ciudad y localidad SAT son
    referencias opcionales para relacionarlo con direcciones oficiales.
    """

    _name = 'embarques.destino'
    _description = 'Destino Logístico'
    _order = 'state_id, name, id'

    name = fields.Char(
        string='Destino', compute='_compute_name', store=True, index=True,
        help='Usa el Nombre manual cuando se captura; de lo contrario se '
             'calcula desde Localidad SAT o Ciudad/Municipio.')
    manual_name = fields.Char(
        string='Nombre manual',
        help='Captúralo solamente cuando el lugar no exista como Localidad '
             'SAT ni como Ciudad/Municipio.')
    active = fields.Boolean(string='Activo', default=True)

    company_id = fields.Many2one(
        'res.company', string='Compañía',
        default=lambda self: self.env.company)

    city_id = fields.Many2one(
        'res.city', string='Ciudad / Municipio',
        ondelete='restrict', index=True,
        help='Referencia oficial opcional para detectar automáticamente el '
             'destino desde la dirección de entrega.')
    state_id = fields.Many2one(
        'res.country.state', string='Estado', ondelete='restrict', index=True)
    locality_id = fields.Many2one(
        'l10n_mx_edi.res.locality', string='Localidad SAT',
        ondelete='restrict',
        help='Referencia fiscal opcional para Carta Porte. No interviene en '
             'rutas, paquetería ni descuentos.')

    zona_id = fields.Many2one(
        'embarques.zona', string='Zona', required=True, ondelete='restrict',
        help='Zona logística del destino. Junto con el rango de llantas '
             'alcanzado determina el porcentaje de descuento.')
    discount_policy_ids = fields.Many2many(
        'embarques.discount.policy',
        'embarques_destino_policy_rel', 'destino_id', 'policy_id',
        string='Rangos y Descuentos',
        help='Selecciona una o varias combinaciones de rango y descuento.')
    distance_km = fields.Float(string='Distancia (km)', digits=(16, 1))
    seed_key = fields.Char(string='Clave de plantilla', index=True, copy=False)
    unidad_ids = fields.Many2many(
        'embarques.unidad',
        'embarques_destino_unidad_rel', 'destino_id', 'unidad_id',
        string='Rangos Permitidos',
        help='Rangos comerciales que pueden entregar aquí (las columnas SI/NO del '
             'Excel). Si el embarque va con un rango que este destino no '
             'admite, no hay descuento automático.')
    # ── Paquetería ────────────────────────────────────────────────────────────
    currency_id = fields.Many2one(
        'res.currency', string='Moneda',
        default=lambda self: self._default_currency_id())
    paqueteria_estado = fields.Selection(
        [
            ('sin_costo', 'Sin costo'),
            ('con_costo', 'Con costo'),
        ],
        string='Paquetería',
        help='"Sin costo" es el SIN COSTO del Excel: el destino no paga '
             'paquetería. En blanco tampoco cobra, pero señala que el dato '
             'falta.')
    paqueteria_cost = fields.Monetary(
        string='Paquetería por Pieza', currency_field='currency_id',
        help='Importe de referencia por pieza. Sólo se cobra cuando '
             'Paquetería está marcada como "Con costo".')
    paqueteria_free_from_qty = fields.Integer(
        string='Envío gratis desde (llantas)', default=0,
        help='Cantidad de llantas a partir de la cual el envío es gratis. '
             'Cero significa que siempre se cobra cuando el '
             'destino está marcado como "Con costo".')
    configuration_status = fields.Selection([
        ('ok', 'Correcto'),
        ('warning', 'Advertencia'),
        ('error', 'Error'),
    ], string='Validación', compute='_compute_configuration_status', store=True)
    configuration_message = fields.Char(
        string='Detalle de Validación', compute='_compute_configuration_status',
        store=True)

    @api.model
    def _default_currency_id(self):
        """Pesos mexicanos por defecto, con respaldo en la moneda de la compañía."""
        mxn = self.env.ref('base.MXN', raise_if_not_found=False)
        if mxn and mxn.active:
            return mxn
        return self.env.company.currency_id

    # ── Compute ───────────────────────────────────────────────────────────────

    @api.depends('manual_name', 'city_id', 'locality_id')
    def _compute_name(self):
        for rec in self:
            rec.name = (
                (rec.manual_name or '').strip()
                or rec.locality_id.name
                or rec.city_id.name
                or False)

    @api.depends(
        'name', 'manual_name', 'state_id', 'city_id', 'locality_id',
        'zona_id', 'discount_policy_ids', 'discount_policy_ids.active',
        'discount_policy_ids.unidad_id', 'discount_policy_ids.percentage',
        'unidad_ids', 'paqueteria_estado', 'paqueteria_cost',
        'paqueteria_free_from_qty')
    def _compute_configuration_status(self):
        for rec in self:
            errors = []
            warnings = []
            if not rec.name:
                errors.append(_('falta destino o nombre manual'))
            if not rec.zona_id:
                errors.append(_('falta zona'))
            if not rec.discount_policy_ids:
                errors.append(_('faltan rangos y descuentos'))
            else:
                # Un destino sólo puede tener un porcentaje por rango. Datos
                # históricos/importados podían conservar varias opciones para
                # la misma capacidad y el badge decía incorrectamente Correcto.
                by_range = {}
                for option in rec.discount_policy_ids.filtered('active'):
                    if not option.unidad_id:
                        continue
                    by_range.setdefault(option.unidad_id.id, []).append(option)
                duplicated = [options for options in by_range.values() if len(options) > 1]
                if duplicated:
                    details = []
                    for options in duplicated:
                        details.append('%s: %s' % (
                            options[0].unidad_id.display_name,
                            ', '.join('%.2f%%' % option.percentage for option in options)))
                    errors.append(_('rangos repetidos/conflictivos (%s)') % '; '.join(details))
            if not (rec.state_id or rec.city_id or rec.locality_id):
                warnings.append(_('sin referencia geográfica oficial'))
            if (rec.locality_id and rec.state_id
                    and rec.locality_id.state_id != rec.state_id):
                errors.append(_('la localidad SAT pertenece a otro estado'))
            if (rec.city_id and rec.state_id
                    and rec.city_id.state_id != rec.state_id):
                errors.append(_('la ciudad pertenece a otro estado'))
            if rec.paqueteria_estado == 'con_costo':
                if rec.paqueteria_cost <= 0:
                    errors.append(_('falta tarifa de paquetería'))
                if rec.paqueteria_free_from_qty == 1:
                    errors.append(_('envío gratis desde 1 contradice "Con costo"'))
            elif rec.paqueteria_estado == 'sin_costo':
                if rec.paqueteria_cost or rec.paqueteria_free_from_qty:
                    errors.append(_(
                        '"Sin costo" no puede tener tarifa ni mínimo'))
            else:
                warnings.append(_('paquetería sin definir'))
            messages = errors or warnings
            rec.configuration_status = (
                'error' if errors else 'warning' if warnings else 'ok')
            rec.configuration_message = '; '.join(messages) if messages else _(
                'Configuración correcta')

    @api.onchange(
        'manual_name', 'state_id', 'city_id', 'locality_id', 'zona_id',
        'discount_policy_ids', 'unidad_ids',
        'paqueteria_estado', 'paqueteria_cost',
        'paqueteria_free_from_qty')
    def _onchange_refresh_configuration_status(self):
        """Refresca el badge dentro de la lista editable antes de guardar."""
        for rec in self:
            if rec.paqueteria_cost > 0 and not rec.paqueteria_estado:
                rec.paqueteria_estado = 'con_costo'
        self._compute_configuration_status()

    @api.onchange('discount_policy_ids')
    def _onchange_discount_policy_ids(self):
        for rec in self:
            rec.unidad_ids = rec.discount_policy_ids.mapped('unidad_id')

    # ── Constraints ───────────────────────────────────────────────────────────

    @api.constrains('state_id', 'city_id', 'locality_id')
    def _check_locality_state(self):
        for rec in self:
            if (rec.city_id and rec.state_id
                    and rec.city_id.state_id != rec.state_id):
                raise ValidationError(_(
                    'La ciudad "%(city)s" no pertenece al estado '
                    '"%(state)s".') % {
                        'city': rec.city_id.display_name,
                        'state': rec.state_id.display_name,
                    })
            if (rec.locality_id and rec.state_id
                    and rec.locality_id.state_id != rec.state_id):
                raise ValidationError(_(
                    'La localidad SAT "%(locality)s" no pertenece al estado '
                    '"%(state)s".') % {
                        'locality': rec.locality_id.display_name,
                        'state': rec.state_id.display_name,
                    })

    @api.onchange('city_id')
    def _onchange_city_id_clear_locality(self):
        if self.city_id:
            self.state_id = self.city_id.state_id
        if (self.locality_id and self.state_id
                and self.locality_id.state_id != self.state_id):
            self.locality_id = False
            return {'warning': {
                'title': _('Localidad SAT eliminada'),
                'message': _(
                    'La localidad seleccionada no pertenece al estado de la '
                    'nueva ciudad. Selecciona una localidad del mismo estado.'),
            }}

    @api.onchange('locality_id')
    def _onchange_locality_id(self):
        if self.locality_id:
            if not self.state_id:
                self.state_id = self.locality_id.state_id

    @api.constrains('name', 'manual_name', 'city_id', 'locality_id')
    def _check_destination_name(self):
        for rec in self:
            if not rec.name:
                raise ValidationError(_(
                    'Selecciona una Localidad SAT o Ciudad/Municipio; si el '
                    'lugar no existe oficialmente, captura Nombre manual.'))

    @api.constrains('name', 'city_id', 'locality_id', 'company_id', 'active')
    def _check_duplicados(self):
        for rec in self:
            if not rec.active:
                continue
            domain = [
                ('id', '!=', rec.id),
                ('company_id', '=', rec.company_id.id),
                ('active', '=', True),
            ]
            if rec.locality_id:
                domain.append(('locality_id', '=', rec.locality_id.id))
            elif rec.city_id:
                domain.append(('city_id', '=', rec.city_id.id))
            else:
                domain.append(('name', '=ilike', rec.name.strip()))
                domain.append(('state_id', '=', rec.state_id.id))
            if self.search_count(domain):
                raise ValidationError(
                    _('Ya existe un renglón para el destino "%s".') % rec.name)

    @api.constrains('zona_id', 'discount_policy_ids')
    def _check_discount_configuration(self):
        for rec in self:
            if not rec.zona_id:
                raise ValidationError(_(
                    'Selecciona una zona para el destino "%s".') % rec.name)
            if not rec.discount_policy_ids:
                raise ValidationError(_(
                    'Selecciona al menos un rango y descuento para "%s".') %
                    rec.name)
            ranges = rec.discount_policy_ids.mapped('unidad_id')
            if len(ranges) != len(rec.discount_policy_ids):
                raise ValidationError(_(
                    'El destino "%s" tiene dos descuentos para el mismo '
                    'rango. Selecciona sólo uno por rango.') % rec.name)

    @api.constrains(
        'paqueteria_estado', 'paqueteria_cost', 'paqueteria_free_from_qty')
    def _check_paqueteria(self):
        for rec in self:
            if rec.paqueteria_cost < 0:
                raise ValidationError(
                    _('La paquetería de "%s" no puede ser negativa.') % rec.name)
            if rec.paqueteria_estado == 'con_costo' and not rec.paqueteria_cost:
                raise ValidationError(
                    _('Captura el importe de paquetería de "%s", o márcalo '
                      'como sin costo.') % rec.name)
            if rec.paqueteria_free_from_qty < 0:
                raise ValidationError(_(
                    'La cantidad para envío gratis de "%s" no puede ser negativa.')
                    % rec.name)
            if (rec.paqueteria_estado == 'sin_costo'
                    and (rec.paqueteria_cost
                         or rec.paqueteria_free_from_qty)):
                raise ValidationError(_(
                    'El destino "%s" está marcado Sin costo; la tarifa y '
                    'Envío gratis desde deben quedar en cero.') % rec.name)
            if (rec.paqueteria_estado == 'con_costo'
                    and rec.paqueteria_free_from_qty == 1):
                raise ValidationError(_(
                    '"%s" está marcado Con costo, pero Envío gratis desde 1 '
                    'haría gratis cualquier pedido. Usa Sin costo o captura '
                    'un mínimo mayor a 1.') % rec.name)

    @api.onchange('paqueteria_estado')
    def _onchange_paqueteria_estado(self):
        if self.paqueteria_estado != 'sin_costo':
            return
        had_values = bool(
            self.paqueteria_cost or self.paqueteria_free_from_qty)
        self.paqueteria_cost = 0.0
        self.paqueteria_free_from_qty = 0
        self._compute_configuration_status()
        if had_values:
            return {'warning': {
                'title': _('Paquetería sin costo'),
                'message': _(
                    'Se eliminaron la tarifa y el mínimo porque este destino '
                    'quedó marcado Sin costo.'),
            }}

    # ── ORM y paquetería ──────────────────────────────────────────────────────

    def init(self):
        """Conserva los nombres libres capturados en la versión anterior."""
        self.env.cr.execute("""
            UPDATE embarques_destino
               SET manual_name = name
             WHERE manual_name IS NULL
               AND name IS NOT NULL
               AND city_id IS NULL
               AND locality_id IS NULL
        """)

    @api.model
    def _load_logistico_seed(self):
        """Carga idempotente de zonas, políticas y destinos del Excel fuente."""
        def normalized(value):
            value = unicodedata.normalize('NFKD', value or '')
            return ''.join(char for char in value
                           if not unicodedata.combining(char)).strip().casefold()

        with file_open(
                'embarques_module/data/logistico_seed.csv', mode='r') as stream:
            rows = list(csv.DictReader(stream))
        if not rows:
            return True

        Country = self.env['res.country'].sudo()
        State = self.env['res.country.state'].sudo()
        City = self.env['res.city'].sudo()
        Locality = self.env['l10n_mx_edi.res.locality'].sudo()
        Zone = self.env['embarques.zona'].sudo()
        Unit = self.env['embarques.unidad'].sudo()
        Policy = self.env['embarques.discount.policy'].sudo()
        Destination = self.sudo()

        mexico = Country.search([('code', '=', 'MX')], limit=1)
        states = {
            state.code.upper(): state
            for state in State.search([('country_id', '=', mexico.id)])
            if state.code
        }
        zones = {}
        for sequence, zone_name in enumerate(
                sorted({row['zone'] for row in rows}), 1):
            zones[zone_name] = Zone.search(
                [('name', '=ilike', zone_name)], limit=1) or Zone.create({
                    'name': zone_name, 'sequence': sequence * 10,
                    'note': 'Fuente: LOGISTICO- AGOSTO 2026',
                })

        capacities = (1200, 650, 250, 120, 30)
        units = {}
        for sequence, capacity in enumerate(capacities, 1):
            units[capacity] = Unit.search([
                ('capacidad_llantas', '=', capacity), ('active', '=', True),
            ], limit=1) or Unit.create({
                'capacidad_llantas': capacity, 'sequence': sequence * 10,
            })

        option_zones = {}
        profile_options = {}
        for row in rows:
            option_keys = []
            for capacity in capacities:
                raw = row['range_%s' % capacity].strip()
                if not raw or raw.upper() == 'N/A':
                    continue
                key = (capacity, round(float(raw) * 100.0, 6))
                option_keys.append(key)
                option_zones.setdefault(key, set()).add(row['zone'])
            profile_options[row['profile_code']] = option_keys

        options = {}
        for (capacity, percentage), zone_names in sorted(option_zones.items()):
            option = Policy.search([
                ('unidad_id', '=', units[capacity].id),
                ('percentage', '=', percentage),
                ('company_id', '=', False),
            ], limit=1)
            values = {
                'active': True,
                'zona_ids': [(6, 0, [
                    zones[name].id for name in sorted(zone_names)
                ])],
            }
            if option:
                option.write(values)
            else:
                values.update({
                    'unidad_id': units[capacity].id,
                    'percentage': percentage,
                    'seed_code': 'OPT_%s_%s' % (
                        capacity, str(percentage).replace('.', '_')),
                    'company_id': False,
                })
                option = Policy.create(values)
            options[(capacity, percentage)] = option

        cities_by_state = {}
        localities_by_state = {}
        for state in states.values():
            cities_by_state[state.id] = {}
            for city in City.search([('state_id', '=', state.id)]):
                cities_by_state[state.id].setdefault(normalized(city.name), city)
            localities_by_state[state.id] = {}
            for locality in Locality.search([('state_id', '=', state.id)]):
                localities_by_state[state.id].setdefault(
                    normalized(locality.name), locality)

        existing_by_key = {
            destination.seed_key: destination
            for destination in Destination.search([('seed_key', '!=', False)])
        }
        for row in rows:
            allowed = [
                units[int(value)].id
                for value in row['allowed_ranges'].split('|') if value
            ]
            selected_options = [
                options[key].id for key in profile_options[row['profile_code']]
            ]
            existing_destination = existing_by_key.get(row['seed_key'])
            if existing_destination:
                values = {}
                current_options = existing_destination.discount_policy_ids.filtered('active')
                range_counts = {}
                for option in current_options:
                    if option.unidad_id:
                        range_counts[option.unidad_id.id] = (
                            range_counts.get(option.unidad_id.id, 0) + 1)
                has_duplicate_ranges = any(
                    count > 1 for count in range_counts.values())
                # Los destinos administrados por la semilla que quedaron con
                # rangos duplicados/conflictivos se reparan contra el perfil
                # canónico del CSV. No sobrescribimos configuraciones sanas.
                if not existing_destination.discount_policy_ids or has_duplicate_ranges:
                    values['discount_policy_ids'] = [(6, 0, selected_options)]
                if not existing_destination.unidad_ids:
                    values['unidad_ids'] = [(6, 0, allowed)]
                if values:
                    existing_destination.write(values)
                continue
            state = states.get(row['state_code'].upper())
            source_name = row['source_name'].strip()
            city = locality = False
            if state:
                city = cities_by_state[state.id].get(
                    normalized(row.get('city_name')))
                locality = localities_by_state[state.id].get(
                    normalized(row.get('locality_name')))
            # Esta semilla es deliberadamente estricta: ninguna fila puede
            # entrar como nombre libre ni con una referencia parcial.
            if not (state and city and locality):
                continue
            manual_name = False
            if locality:
                identity_domain = [('locality_id', '=', locality.id)]
            elif city:
                identity_domain = [
                    ('city_id', '=', city.id), ('locality_id', '=', False),
                ]
            else:
                identity_domain = [
                    ('name', '=ilike', source_name),
                    ('state_id', '=', state.id if state else False),
                ]
            existing_destination = Destination.search([
                ('active', '=', True),
                ('company_id', '=', False),
            ] + identity_domain, limit=1)
            if existing_destination:
                values = {}
                if not existing_destination.seed_key:
                    values['seed_key'] = row['seed_key']
                if not existing_destination.discount_policy_ids:
                    values['discount_policy_ids'] = [(6, 0, selected_options)]
                if not existing_destination.unidad_ids:
                    values['unidad_ids'] = [(6, 0, allowed)]
                if values:
                    existing_destination.write(values)
                existing_by_key[row['seed_key']] = existing_destination
                continue
            destination = Destination.create({
                'seed_key': row['seed_key'],
                'manual_name': manual_name,
                'state_id': state.id if state else False,
                'city_id': city.id if city else False,
                'locality_id': locality.id if locality else False,
                'zona_id': zones[row['zone']].id,
                'discount_policy_ids': [(6, 0, selected_options)],
                'distance_km': float(row['distance_km']),
                'unidad_ids': [(6, 0, allowed)],
                'paqueteria_estado': 'con_costo',
                'paqueteria_cost': float(row['shipping_cost']),
                'paqueteria_free_from_qty': int(
                    float(row['free_from_qty'] or 0)),
                'company_id': False,
            })
            existing_by_key[row['seed_key']] = destination
        return True

    @api.model_create_multi
    def create(self, vals_list):
        normalized = []
        for original in vals_list:
            vals = dict(original)
            if (vals.get('paqueteria_cost', 0) > 0
                    and not vals.get('paqueteria_estado')):
                vals['paqueteria_estado'] = 'con_costo'
            normalized.append(vals)
        return super().create(normalized)

    def write(self, vals):
        """Normaliza paquetería; @api.depends realiza el recálculo almacenado."""
        result = super().write(vals)
        inferred = self.filtered(
            lambda rec: rec.paqueteria_cost > 0
            and not rec.paqueteria_estado)
        if inferred:
            super(EmbarquesDestino, inferred).write({
                'paqueteria_estado': 'con_costo',
            })
        return result

    def _paqueteria_unit_cost(self, piezas):
        """Importe POR PIEZA a cobrar a un pedido con `piezas` piezas.

        ``con_costo`` devuelve el importe mientras no se alcance la cantidad
        para envío gratis. ``sin_costo`` siempre devuelve cero.
        """
        self.ensure_one()
        if piezas <= 0 or self.paqueteria_estado != 'con_costo':
            return 0.0
        if (self.paqueteria_free_from_qty
                and piezas >= self.paqueteria_free_from_qty):
            return 0.0
        return self.paqueteria_cost

    # ── Resolución del destino ────────────────────────────────────────────────

    @api.model
    def _normalized_place_name(self, value):
        value = unicodedata.normalize('NFKD', value or '')
        return ''.join(
            char for char in value if not unicodedata.combining(char)
        ).strip().casefold()

    @api.model
    def _cities_equivalent(self, city_a, city_b):
        """True para el mismo municipio aunque Odoo tenga res.city duplicados.

        Algunos catálogos históricos contienen dos registros de ``res.city``
        con el mismo nombre y estado. Para logística son la misma plaza y no
        debemos bloquear un embarque sólo porque sus IDs sean diferentes.
        """
        if not city_a or not city_b:
            return False
        if city_a.id == city_b.id:
            return True
        if self._normalized_place_name(city_a.name) != self._normalized_place_name(city_b.name):
            return False
        state_a = city_a.state_id
        state_b = city_b.state_id
        if not state_a or not state_b:
            return not state_a and not state_b
        if state_a.id == state_b.id:
            return True
        code_a = (state_a.code or '').strip().casefold()
        code_b = (state_b.code or '').strip().casefold()
        if code_a and code_b and code_a == code_b:
            return True
        return (
            self._normalized_place_name(state_a.name)
            == self._normalized_place_name(state_b.name)
        )

    @api.model
    def _equivalent_city_ids(self, city):
        """IDs de res.city que representan el mismo municipio/estado."""
        if not city:
            return []
        domain = [('name', '=ilike', city.name)]
        if city.state_id:
            domain.append(('state_id', '=', city.state_id.id))
        candidates = self.env['res.city'].search(domain)
        equivalent = candidates.filtered(
            lambda candidate: self._cities_equivalent(city, candidate))
        return equivalent.ids or city.ids

    @api.model
    def _match(self, city, company=None):
        """Destino por municipio cuando no hubo coincidencia de localidad.

        Prioridad: renglón genérico del municipio (sin localidad). Si existen
        res.city duplicados con el mismo nombre/estado, se consideran la misma
        ciudad. Si no hay genérico, sólo usamos un destino específico cuando es
        el ÚNICO destino activo de ese municipio.
        """
        company = company or self.env.company
        if not city:
            return self.browse()
        city_ids = self._equivalent_city_ids(city)
        base_domain = [
            ('company_id', 'in', [company.id, False]),
            ('city_id', 'in', city_ids),
            ('active', '=', True),
        ]
        generic = self.search(base_domain + [('locality_id', '=', False)], limit=1)
        if generic:
            return generic
        candidates = self.search(base_domain, limit=2)
        return candidates if len(candidates) == 1 else self.browse()

    @api.model
    def _match_partner(self, partner, company=None):
        """Destino de entrega: localidad exacta; si falla, estado/municipio."""
        if not partner:
            return self.browse()
        company = company or partner.company_id or self.env.company
        locality = getattr(partner, 'l10n_mx_edi_locality_id', False)
        if locality:
            # La localidad puede conservar un valor anterior cuando el usuario
            # cambia la ciudad. Nunca permitimos que esa localidad desactualizada
            # lleve el traslado a un destino de otro municipio.
            city_ids = self._equivalent_city_ids(partner.city_id)
            destination = self.search([
                ('company_id', 'in', [company.id, False]),
                ('locality_id', '=', locality.id),
                ('city_id', 'in', city_ids),
                ('active', '=', True),
            ], limit=1)
            if destination:
                return destination
        destination = self._match(partner.city_id, company=company)
        if destination:
            return destination
        # Respaldo para plazas libres: coincide con el texto de ciudad de la
        # dirección y, cuando existe, con el mismo estado.
        place_name = (partner.city or '').strip()
        if not place_name:
            return self.browse()
        domain = [
            ('company_id', 'in', [company.id, False]),
            ('name', '=ilike', place_name),
            ('active', '=', True),
        ]
        if partner.state_id:
            domain += ['|', ('state_id', '=', partner.state_id.id),
                       ('state_id', '=', False)]
        return self.search(domain, limit=1)
