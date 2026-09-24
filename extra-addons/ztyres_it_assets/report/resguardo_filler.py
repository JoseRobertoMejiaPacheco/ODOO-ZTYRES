# -*- coding: utf-8 -*-
"""Rellena el formato Z-FO-TI-01 "Asignación y resguardo de equipo de cómputo".

No usa openpyxl ni xlsxwriter: abre la plantilla .xlsx original (un zip) y
modifica únicamente las celdas de captura dentro de ``sheet1.xml``. Así el
archivo resultante es EL MISMO formato (logo, bordes, colores, combinaciones
de celdas, área de impresión), solo con los datos escritos.

Este módulo no importa nada de Odoo para poder probarse por separado.
"""
import copy
import io
import os
import re
import textwrap
import zipfile
from datetime import date

from lxml import etree

NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
_NSMAP = {'m': NS}

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'ASIGNACION_Y_RESGUARDO_DE_EQUIPO_DE_COMPUTO.xlsx',
)
SHEET_PATH = 'xl/worksheets/sheet1.xml'
SST_PATH = 'xl/sharedStrings.xml'
STYLES_PATH = 'xl/styles.xml'

UNCHECKED = '\u2610'  # ☐
CHECKED = '\u2612'    # ☒

# ---------------------------------------------------------------------------
# Celdas de la plantilla (ancla de cada celda combinada)
# ---------------------------------------------------------------------------
CELL_NAME = 'D7'
CELL_AREA = 'K7'
CELL_POSITION = 'D8'
CELL_ASSIGN_DATE = 'K8'          # tiene formato de fecha en la plantilla
CELL_EQUIPMENT_TYPE = 'D11'      # "☐ Laptop  ☐ PC de escritorio  ☐ Otro: ____"
CELL_CONDITION = 'J11'           # "☐ Nuevo  ☐ Reasignado ☐ Otro: ____"
CELL_BRAND = 'B13'
CELL_MODEL = 'C13'
CELL_SERIAL = 'E13'
CELL_OS = 'G13'
CELL_STORAGE = 'I13'
CELL_PROCESSOR = 'J13'
CELL_BATTERY_STATE = 'L13'
CELL_BATTERY_PCT = 'M13'
CELL_OBSERVATIONS = ('B17', 'B18', 'B19')   # tres renglones combinados B:M
CELL_RETURN_DATE = 'B35'
CELL_RETURN_REASON = 'B37'
CELL_RETURN_CONDITION = 'I37'

# Accesorios: clave -> celda
ACCESSORY_CELLS = {
    'charger': 'B15',
    'monitor': 'C15',
    'keyboard': 'D15',
    'mouse': 'E15',
    'laptop_base': 'F15',
    'headset': 'H15',
    'bag': 'I15',
    'ups': 'J15',
    'other': 'L15',
}

EQUIPMENT_TYPE_LABELS = {'laptop': 'Laptop', 'desktop': 'PC de escritorio'}
CONDITION_LABELS = {'new': 'Nuevo', 'reassigned': 'Reasignado'}
RETURN_REASON_LABELS = {
    'termination': 'Baja de la empresa',
    'position_change': 'Cambio de puesto',
    'equipment_change': 'Cambio de equipo',
    'repair': 'Reparación',
    'renewal': 'Renovación',
}
RETURN_CONDITION_LABELS = {
    'normal': 'Con desgaste normal de uso',
    'damaged': 'Dañado por mal uso',
    'incomplete': 'Incompleto',
}

_ILLEGAL_XML = re.compile('[\x00-\x08\x0b\x0c\x0e-\x1f]')
OBSERVATION_LINE_WIDTH = 170  # caracteres por renglón (B:M cabe ~220)
OBSERVATION_LAST_LINE_MAX = 200


def _clean(value):
    if value is None or value is False:
        return ''
    return _ILLEGAL_XML.sub('', str(value)).strip()


def excel_serial(d):
    """Fecha -> número de serie de Excel (sistema 1900)."""
    return (d - date(1899, 12, 30)).days


class _Sheet(object):
    """Acceso mínimo a celdas de sheet1.xml conservando estilos."""

    def __init__(self, sheet_xml, sst_xml):
        self.root = etree.fromstring(sheet_xml)
        self.cells = {
            c.get('r'): c for c in self.root.iter('{%s}c' % NS)
        }
        self.shared = []
        for si in etree.fromstring(sst_xml).findall('m:si', _NSMAP):
            self.shared.append(''.join(t.text or '' for t in si.iter('{%s}t' % NS)))

    def _cell(self, ref):
        try:
            return self.cells[ref]
        except KeyError:
            raise ValueError(
                'La plantilla no tiene la celda %s. ¿Cambió el formato?' % ref)

    def text(self, ref):
        c = self._cell(ref)
        kind = c.get('t')
        if kind == 's':
            return self.shared[int(c.find('m:v', _NSMAP).text)]
        if kind == 'inlineStr':
            return ''.join(t.text or '' for t in c.iter('{%s}t' % NS))
        v = c.find('m:v', _NSMAP)
        return v.text if v is not None else ''

    def _reset(self, c):
        for child in list(c):
            c.remove(child)
        if 't' in c.attrib:
            del c.attrib['t']

    def set_text(self, ref, value, style=None):
        c = self._cell(ref)
        self._reset(c)
        c.set('t', 'inlineStr')
        is_el = etree.SubElement(c, '{%s}is' % NS)
        t = etree.SubElement(is_el, '{%s}t' % NS)
        t.text = _clean(value)
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        if style is not None:
            c.set('s', str(style))

    def set_number(self, ref, number):
        c = self._cell(ref)
        self._reset(c)
        v = etree.SubElement(c, '{%s}v' % NS)
        v.text = str(number)

    def style_of(self, ref):
        return int(self._cell(ref).get('s', 0))

    def tobytes(self):
        return etree.tostring(
            self.root, xml_declaration=True, encoding='UTF-8', standalone=True)


def _add_wrapped_style(styles_xml, base_index):
    """Clona un estilo de celda activando el ajuste de texto. -> (xml, índice)."""
    root = etree.fromstring(styles_xml)
    xfs = root.find('m:cellXfs', _NSMAP)
    new = copy.deepcopy(xfs.findall('m:xf', _NSMAP)[base_index])
    align = new.find('m:alignment', _NSMAP)
    if align is None:
        align = etree.SubElement(new, '{%s}alignment' % NS)
        new.remove(align)
        new.insert(0, align)
    align.set('wrapText', '1')
    new.set('applyAlignment', '1')
    xfs.append(new)
    xfs.set('count', str(len(xfs.findall('m:xf', _NSMAP))))
    return (
        etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True),
        len(xfs.findall('m:xf', _NSMAP)) - 1,
    )


# ---------------------------------------------------------------------------
# Casillas de verificación
# ---------------------------------------------------------------------------
def _check(text, label):
    """'☐ Laptop' -> '☒ Laptop' dentro de un texto con varias opciones."""
    marker = '%s %s' % (UNCHECKED, label)
    if marker not in text:
        raise ValueError('No se encontró la casilla "%s" en la plantilla.' % label)
    return text.replace(marker, '%s %s' % (CHECKED, label), 1)


def _check_other(text, value):
    """Marca '☐ Otro: ____' y escribe el valor sobre la línea de guiones."""
    value = _clean(value)
    pattern = re.compile(UNCHECKED + r' Otro:[ ]*_*')
    if not pattern.search(text):
        raise ValueError('No se encontró la casilla "Otro" en la plantilla.')
    return pattern.sub(lambda m: '%s Otro: %s' % (CHECKED, value), text, count=1)


def _wrap_observations(text):
    lines = []
    for para in _clean(text).splitlines():
        lines.extend(textwrap.wrap(para, OBSERVATION_LINE_WIDTH) or [''])
    while lines and not lines[-1]:
        lines.pop()
    if len(lines) > 3:
        lines = lines[:2] + [' '.join(l for l in lines[2:] if l)]
    # El último renglón no ajusta texto: se recorta con "…" si no cabe
    if lines and len(lines[-1]) > OBSERVATION_LAST_LINE_MAX:
        lines[-1] = lines[-1][:OBSERVATION_LAST_LINE_MAX - 1].rstrip() + '\u2026'
    return lines


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------
def build_resguardo_xlsx(data):
    """Devuelve los bytes del .xlsx con el formato lleno.

    ``data`` es un dict (todas las llaves son opcionales):

    name, area, position, assigned_on (date)
    equipment_type ('laptop' | 'desktop' | otro texto), equipment_type_other
    condition ('new' | 'reassigned' | 'other'), condition_other
    brand, model, serial, os, storage, processor, battery_state, battery_pct
    accessories (iterable de llaves de ACCESSORY_CELLS), accessories_other
    observations
    returned_on (date), return_reason, return_reason_other,
    return_condition, return_notes
    """
    with zipfile.ZipFile(TEMPLATE_PATH) as zin:
        sheet = _Sheet(zin.read(SHEET_PATH), zin.read(SST_PATH))
        styles_xml = None

        # --- Datos del resguardante ---------------------------------------
        for ref, key in ((CELL_NAME, 'name'), (CELL_AREA, 'area'),
                         (CELL_POSITION, 'position')):
            if _clean(data.get(key)):
                sheet.set_text(ref, data[key])
        if data.get('assigned_on'):
            sheet.set_number(CELL_ASSIGN_DATE, excel_serial(data['assigned_on']))

        # --- Tipo de equipo -----------------------------------------------
        text = sheet.text(CELL_EQUIPMENT_TYPE)
        eq_type = data.get('equipment_type')
        if eq_type in EQUIPMENT_TYPE_LABELS:
            text = _check(text, EQUIPMENT_TYPE_LABELS[eq_type])
        elif eq_type:
            text = _check_other(text, data.get('equipment_type_other') or eq_type)
        sheet.set_text(CELL_EQUIPMENT_TYPE, text)

        # --- Condición física ---------------------------------------------
        text = sheet.text(CELL_CONDITION)
        cond = data.get('condition')
        if cond in CONDITION_LABELS:
            text = _check(text, CONDITION_LABELS[cond])
        elif cond == 'other':
            text = _check_other(text, data.get('condition_other'))
        sheet.set_text(CELL_CONDITION, text)

        # --- Datos del equipo ---------------------------------------------
        for ref, key in ((CELL_BRAND, 'brand'), (CELL_MODEL, 'model'),
                         (CELL_SERIAL, 'serial'), (CELL_OS, 'os'),
                         (CELL_STORAGE, 'storage'), (CELL_PROCESSOR, 'processor'),
                         (CELL_BATTERY_STATE, 'battery_state'),
                         (CELL_BATTERY_PCT, 'battery_pct')):
            if _clean(data.get(key)):
                sheet.set_text(ref, data[key])

        # --- Accesorios entregados ----------------------------------------
        marked = set(data.get('accessories') or ())
        unknown = marked - set(ACCESSORY_CELLS)
        if unknown:
            raise ValueError('Accesorio desconocido: %s' % ', '.join(sorted(unknown)))
        for key, ref in ACCESSORY_CELLS.items():
            if key not in marked:
                continue
            text = sheet.text(ref)
            if key == 'other':
                other = _clean(data.get('accessories_other'))
                text = text.replace(UNCHECKED, CHECKED, 1).rstrip()
                if other:
                    text = '%s %s' % (text, other)
                    # La celda L15:M15 no ajusta texto: se clona su estilo con wrap
                    styles_xml, new_style = _add_wrapped_style(
                        zin.read(STYLES_PATH), sheet.style_of(ref))
                    sheet.set_text(ref, text, style=new_style)
                    continue
            else:
                text = text.replace(UNCHECKED, CHECKED, 1)
            sheet.set_text(ref, text)

        # --- Observaciones ------------------------------------------------
        for ref, line in zip(CELL_OBSERVATIONS, _wrap_observations(data.get('observations'))):
            if line:
                sheet.set_text(ref, line)

        # --- Devolución (solo si ya hay fecha de devolución) ---------------
        returned_on = data.get('returned_on')
        if returned_on:
            text = sheet.text(CELL_RETURN_DATE)
            text = re.sub(
                r'_+ / _+ / _+',
                '%02d / %02d / %04d' % (returned_on.day, returned_on.month, returned_on.year),
                text, count=1)
            sheet.set_text(CELL_RETURN_DATE, text)

            reason = data.get('return_reason')
            if reason:
                lines = sheet.text(CELL_RETURN_REASON).split('\n')
                out = []
                for line in lines:
                    if reason in RETURN_REASON_LABELS and line.strip() == '%s %s' % (
                            UNCHECKED, RETURN_REASON_LABELS[reason]):
                        line = line.replace(UNCHECKED, CHECKED, 1)
                    elif reason == 'other' and line.startswith('%s Otro:' % UNCHECKED):
                        line = _check_other(line, data.get('return_reason_other'))
                    out.append(line)
                sheet.set_text(CELL_RETURN_REASON, '\n'.join(out))

            rcond = data.get('return_condition')
            notes = _clean(data.get('return_notes'))
            if rcond or notes:
                text = sheet.text(CELL_RETURN_CONDITION)
                if rcond in RETURN_CONDITION_LABELS:
                    text = _check(text, RETURN_CONDITION_LABELS[rcond])
                if notes:
                    text = '%s %s' % (text.rstrip(), notes)
                sheet.set_text(CELL_RETURN_CONDITION, text)

        # --- Empaquetar: mismo zip, solo cambian sheet1 (y estilos si aplica) --
        new_sheet = sheet.tobytes()
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                content = zin.read(item.filename)
                if item.filename == SHEET_PATH:
                    content = new_sheet
                elif item.filename == STYLES_PATH and styles_xml is not None:
                    content = styles_xml
                zout.writestr(item, content)
    return out.getvalue()
