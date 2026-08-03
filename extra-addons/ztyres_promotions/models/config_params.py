# -*- coding: utf-8 -*-
"""
ztyres_promotions · Parámetros de sistema
==========================================
"Lenguaje de variables de entorno" del módulo de promociones.

La clave en ir.config_parameter es siempre:  ztyres_promotions.<NOMBRE>

Para agregar una variable nueva, solo añade una entrada al PARAM_REGISTRY:
    'MI_VARIABLE': {
        'type':        'float',      # float | int | str | bool | list_str | list_float
        'default':     0.0,          # valor si aún no existe en BD
        'description': 'Para qué sirve.',
        'group':       'Mi grupo',   # agrupación visual, libre
    }
"""

from odoo import api, models


# ---------------------------------------------------------------------------
# PARAM_REGISTRY — aquí viven todas las variables de entorno
# ---------------------------------------------------------------------------
# Nombres planos, sin prefijos forzados.  Pon el nombre que tenga sentido
# para el negocio.  El único prefijo real es "ztyres_promotions." que se
# agrega automáticamente en ir.config_parameter para no colisionar con otros
# módulos.
# ---------------------------------------------------------------------------

PARAM_REGISTRY = {

    # ------------------------------------------------------------------
    # Acceso externo (cotizador fuera de la sesión de Odoo)
    # ------------------------------------------------------------------
    'EXTERNAL_API_KEY': {
        'type': 'str',
        'default': '',
        'description': (
            'Clave que debe enviar el cotizador externo en el header '
            'X-Api-Key. Vacío = API externa deshabilitada (rechaza todo). '
            'Cámbiala aquí cuando quieras rotarla, sin tocar código.'
        ),
        'group': 'Acceso externo',
    },

}


# ---------------------------------------------------------------------------
# Modelo helper
# ---------------------------------------------------------------------------

class PromotionConfigParam(models.AbstractModel):
    """Resuelve parámetros de sistema para el módulo de promociones.

    No tiene tabla propia: delega en ir.config_parameter.

    Uso desde Python de Odoo:
        cfg = self.env['ztyres_promotions.config.param']
        cfg.get('EXTERNAL_API_KEY')  → valor tipado
        cfg.get_all()                → {'EXTERNAL_API_KEY': '...'}
        cfg.set('EXTERNAL_API_KEY', 'abc')  → guarda en BD
        cfg.init_defaults()          → siembra los que aún no existen
    """

    _name = 'ztyres_promotions.config.param'
    _description = 'Parámetros de sistema — Promociones'

    _PREFIX = 'ztyres_promotions.'

    @api.model
    def get(self, nombre, default=None):
        """Devuelve el valor del parámetro, convertido al tipo declarado."""
        meta = PARAM_REGISTRY.get(nombre)
        raw = self.env['ir.config_parameter'].sudo().get_param(
            self._PREFIX + nombre
        )
        if raw is None or raw == '':
            return meta['default'] if meta else default
        return self._cast(raw, meta['type'] if meta else 'str')

    @api.model
    def get_all(self):
        """Devuelve dict con todos los parámetros del registro resueltos."""
        return {nombre: self.get(nombre) for nombre in PARAM_REGISTRY}

    @api.model
    def _cast(self, raw, typ):
        if typ == 'float':
            try:
                return float(raw)
            except (ValueError, TypeError):
                return 0.0
        if typ == 'int':
            try:
                return int(raw)
            except (ValueError, TypeError):
                return 0
        if typ == 'bool':
            return str(raw).strip().lower() in ('1', 'true', 'yes', 'si', 'sí')
        if typ == 'list_str':
            return [s.strip() for s in str(raw).split(',') if s.strip()]
        if typ == 'list_float':
            result = []
            for s in str(raw).split(','):
                try:
                    result.append(float(s.strip()))
                except (ValueError, TypeError):
                    pass
            return result
        return str(raw)

    @api.model
    def set(self, nombre, value):
        """Guarda o actualiza un parámetro en ir.config_parameter."""
        meta = PARAM_REGISTRY.get(nombre)
        typ = meta['type'] if meta else 'str'
        if typ in ('list_str', 'list_float'):
            raw = ','.join(str(v) for v in (value or []))
        elif typ == 'bool':
            raw = '1' if value else '0'
        else:
            raw = str(value)
        self.env['ir.config_parameter'].sudo().set_param(
            self._PREFIX + nombre, raw
        )

    @api.model
    def init_defaults(self):
        """Siembra en BD todos los parámetros que aún no existan."""
        ICP = self.env['ir.config_parameter'].sudo()
        created = []
        for nombre, meta in PARAM_REGISTRY.items():
            key = self._PREFIX + nombre
            if not ICP.get_param(key):
                default = meta['default']
                typ = meta['type']
                if typ in ('list_str', 'list_float'):
                    raw = ','.join(str(v) for v in (default or []))
                elif typ == 'bool':
                    raw = '1' if default else '0'
                else:
                    raw = str(default)
                ICP.set_param(key, raw)
                created.append(key)
        return created
