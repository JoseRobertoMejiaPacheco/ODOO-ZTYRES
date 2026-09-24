# -*- coding: utf-8 -*-
import re
import unicodedata

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..report.resguardo_filler import build_resguardo_xlsx

# Palabras clave (sin acentos, en minúsculas) con las que se decide en qué casilla
# del formato cae cada accesorio. El orden importa: se usa la primera que coincida.
ACCESSORY_KEYWORDS = [
    ('charger', ('cargador', 'charger', 'eliminador')),
    ('monitor', ('monitor', 'pantalla')),
    ('keyboard', ('teclado', 'keyboard')),
    ('mouse', ('mouse', 'raton')),
    ('headset', ('audifono', 'audifonos', 'diadema', 'headset', 'headphones')),
    ('bag', ('mochila', 'funda', 'maletin', 'backpack')),
    ('ups', ('no-break', 'nobreak', 'no break', 'regulador', 'ups')),
    ('laptop_base', ('base', 'dock', 'docking', 'soporte')),
]


def _normalize(text):
    text = unicodedata.normalize('NFKD', text or '')
    return ''.join(c for c in text if not unicodedata.combining(c)).lower()


def _accessory_slot(accessory):
    """Casilla del formato que corresponde al accesorio ('other' si ninguna)."""
    for source in (accessory.type_id.name, accessory.name):
        norm = _normalize(source)
        if not norm:
            continue
        for slot, words in ACCESSORY_KEYWORDS:
            for word in words:
                if re.search(r'(?<![a-z0-9])%s(?![a-z0-9])' % re.escape(word), norm):
                    return slot
    return 'other'


class ItResguardo(models.AbstractModel):
    _name = 'ztyres.it.resguardo'
    _description = 'Formato Z-FO-TI-01 Asignación y resguardo de equipo de cómputo'

    # ------------------------------------------------------------------
    @api.model
    def _selection_label(self, record, field_name):
        value = record[field_name]
        if not value:
            return ''
        return dict(record._fields[field_name].selection).get(value, value)

    @api.model
    def _infer_condition(self, assignment):
        """Nuevo si es la primera asignación del equipo; Reasignado si ya hubo otra."""
        earlier = self.env['ztyres.it.assignment'].search_count([
            ('equipment_id', '=', assignment.equipment_id.id),
            ('id', '!=', assignment.id),
            '|', ('date_from', '<', assignment.date_from),
            '&', ('date_from', '=', assignment.date_from), ('id', '<', assignment.id),
        ])
        return 'reassigned' if earlier else 'new'

    @api.model
    def _prepare_data(self, record):
        """Devuelve (dict para el llenador, equipo, asignación)."""
        if record._name == 'ztyres.it.assignment':
            assignment, equipment = record, record.equipment_id
            if not equipment:
                raise UserError(_(
                    'Este formato es solo para equipo de cómputo. '
                    'La asignación seleccionada no tiene un equipo.'))
        elif record._name == 'ztyres.it.equipment':
            equipment = record
            assignment = equipment._get_current_assignment()
        else:
            raise UserError(_('Modelo no soportado: %s') % record._name)

        user = assignment.user_id or equipment.user_id
        eq = equipment

        # Almacenamiento: "512 GB" + tipo de disco ("SSD") si no viene ya escrito
        storage = eq.storage or ''
        if eq.disk_type and eq.disk_type != 'other':
            disk = self._selection_label(eq, 'disk_type')
            if disk.lower() not in storage.lower():
                storage = ('%s %s' % (storage, disk)).strip()

        os_name = eq.operating_system or ''
        if eq.os_version and eq.os_version.lower() not in os_name.lower():
            os_name = ('%s %s' % (os_name, eq.os_version)).strip()

        if eq.battery_state == 'na':
            battery_state, battery_pct = 'No aplica', 'N/A'
        else:
            battery_state = self._selection_label(eq, 'battery_state')
            battery_pct = '%s%%' % eq.battery_health if eq.battery_health else ''

        slots, others = set(), []
        for acc in eq.accessory_ids:
            slot = _accessory_slot(acc)
            slots.add(slot)
            if slot == 'other':
                others.append(acc.name)

        data = {
            'name': user.name,
            'area': assignment.area or eq.area,
            'position': assignment.position or eq.position,
            'assigned_on': assignment.date_from if assignment
            else fields.Date.context_today(self),
            'equipment_type': eq.equipment_type,
            'brand': eq.brand_id.name,
            'model': eq.model,
            'serial': eq.serial_number,
            'os': os_name,
            'storage': storage,
            'processor': eq.processor,
            'battery_state': battery_state,
            'battery_pct': battery_pct,
            'accessories': slots,
            'accessories_other': ', '.join(others),
            'observations': (assignment.notes if assignment else '') or eq.notes,
        }

        if assignment:
            data['condition'] = assignment.physical_condition or self._infer_condition(assignment)
            data['condition_other'] = assignment.physical_condition_other
            if assignment.date_to:
                data.update({
                    'returned_on': assignment.date_to,
                    'return_reason': assignment.return_reason,
                    'return_reason_other': assignment.return_reason_other,
                    'return_condition': assignment.return_condition,
                    'return_notes': assignment.return_notes,
                })
        else:
            data['condition'] = 'new'
        return data, equipment, assignment

    # ------------------------------------------------------------------
    @api.model
    def build_xlsx(self, record):
        """record: ztyres.it.assignment o ztyres.it.equipment -> (nombre, bytes)."""
        data, equipment, assignment = self._prepare_data(record)
        content = build_resguardo_xlsx(data)
        base = 'Resguardo_%s_%s' % (equipment.inventory_number or equipment.id, data['name'] or 'sin_usuario')
        filename = re.sub(r'[^\w\-]+', '_', base, flags=re.UNICODE).strip('_') + '.xlsx'
        return filename, content
