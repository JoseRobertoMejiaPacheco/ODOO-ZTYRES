# -*- coding: utf-8 -*-
import base64
import json
import logging

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class PromotionsExternalAPI(http.Controller):
    """Controlador del cotizador.

    La API /external/* sigue siendo una integración servidor-a-servidor
    protegida por API key. El cotizador dentro de Odoo (/cotizador/*)
    requiere sesión de usuario: nunca debe quedar como auth=public porque
    las respuestas contienen catálogo, existencias y promociones.
    """

    def _cotizador_access(self):
        """Permite al usuario interno autorizado o a cualquier usuario Portal.

        El menú backend sigue protegido por group_cotizador_access. Para
        portal no se concede acceso a modelos ni al backend: solo a estas
        rutas del cotizador, que son de lectura/cálculo y usan sudo() de
        forma deliberada detrás de esta barrera de sesión.
        """
        user = request.env.user
        return (
            user.has_group('ztyres_promotions.group_cotizador_access')
            or user.has_group('base.group_portal')
        )

    def _require_cotizador_access(self):
        if not self._cotizador_access():
            return self._json({'error': 'No tienes permiso para usar el cotizador'}, 403)
        return None

    def _portal_product_ids(self, product_ids=None):
        """IDs de variantes de llanta que el portal puede consultar.

        Se valida directamente contra product.template.tire y solo contra
        los IDs solicitados; nunca reconstruye el catálogo completo en un
        refresh de stock o en cada línea del carrito.
        """
        domain = [('product_tmpl_id.tire', '=', True)]
        if product_ids is not None:
            product_ids = list({int(x) for x in product_ids})
            if not product_ids:
                return set()
            domain.append(('id', 'in', product_ids))
        return set(request.env['product.product'].sudo().search(domain).ids)

    def _sanitize_lines(self, lines):
        """Normaliza y limita líneas recibidas desde el navegador.

        Para portal se evita que un usuario pueda consultar por ID productos
        ajenos al catálogo publicado o enviar cantidades absurdamente grandes.
        Para internos también se valida el shape para que el endpoint sea
        robusto ante payloads manipulados.
        """
        if not isinstance(lines, list) or len(lines) > 100:
            return None
        allowed = None
        clean = []
        for line in lines:
            if not isinstance(line, dict):
                return None
            try:
                product_id = int(line.get('product_id') or 0)
                qty = float(line.get('qty') or 0)
            except (TypeError, ValueError):
                return None
            if product_id <= 0 or qty <= 0 or qty > 100000:
                return None
            clean.append({'product_id': product_id, 'qty': qty})
        if request.env.user.has_group('base.group_portal'):
            allowed = self._portal_product_ids([line['product_id'] for line in clean])
            if len(allowed) != len({line['product_id'] for line in clean}):
                return None
        return clean

    def _validate_portal_cart(self, cart):
        if not request.env.user.has_group('base.group_portal'):
            return cart
        if not isinstance(cart, dict) or len(cart) > 100:
            return None
        requested_ids = []
        clean = {}
        for key, value in cart.items():
            try:
                product_id = int(key)
                qty = float(value)
            except (TypeError, ValueError):
                return None
            if qty <= 0 or qty > 100000:
                return None
            requested_ids.append(product_id)
            clean[product_id] = qty
        allowed = self._portal_product_ids(requested_ids)
        if len(allowed) != len(requested_ids):
            return None
        return clean

    def _require_same_origin(self):
        """Defensa adicional para POST JSON con csrf=False.

        El frontend oficial manda X-Ztyres-Cotizador=1. Un formulario o
        script de un sitio externo no puede añadir este header en una
        petición cross-origin sin pasar por CORS/preflight. Se valida
        además Origin/Referer cuando el navegador los proporciona.
        """
        if request.httprequest.headers.get('X-Ztyres-Cotizador') != '1':
            return False
        host = request.httprequest.host
        origin = request.httprequest.headers.get('Origin')
        referer = request.httprequest.headers.get('Referer')
        if origin and origin.rstrip('/') != request.httprequest.host_url.rstrip('/'):
            return False
        if not origin and referer:
            from urllib.parse import urlparse
            if urlparse(referer).netloc != host:
                return False
        return True

    """Dos familias de rutas, a propósito separadas:

    /ztyres_promotions/external/*  — para el cotizador HTML/JS que
    vive FUERA de Odoo (otro dominio, sin sesión). Requiere la API key
    compartida (header X-Api-Key). Se configura en Ajustes > Técnico >
    Parámetros del sistema, con la clave
    ztyres_promotions.EXTERNAL_API_KEY. Sin ella, /external/* rechaza
    todo.

    /ztyres_promotions/cotizador*  — para la app Owl que vive DENTRO
    de Odoo (servida por este mismo controlador). Esta NO usa API
    key: la conexión ya es directa con Odoo (mismo origen, sin CORS),
    así que pedir una key ahí no protege nada que la propia ruta
    pública no esté ya exponiendo — es una capa de más sin beneficio
    real. El día que esa ruta pase a requerir sesión (auth='user'),
    la autenticación normal de Odoo hace ese trabajo.

    Ambas familias llaman a los mismos métodos internos (_get_catalog,
    _get_partners, etc.) para no duplicar lógica de negocio — lo único
    que cambia entre una y otra es el control de acceso.
    """

    # ------------------------------------------------------------
    # Autenticación — SOLO para /external/*
    # ------------------------------------------------------------

    # Clave en ir.config_parameter. Se lee directo, sin modelo
    # intermedio: era un registro tipado completo para resolver este
    # único string.
    API_KEY_PARAM = 'ztyres_promotions.EXTERNAL_API_KEY'

    def _expected_key(self):
        """Key configurada, o '' si no hay ninguna.

        `get_param` devuelve False cuando la clave no existe o está
        vacía. Se normaliza a '' aquí para que los llamadores puedan
        confiar en `bool(...)`: sin key configurada, la API externa
        rechaza todo.
        """
        return request.env['ir.config_parameter'].sudo().get_param(
            self.API_KEY_PARAM
        ) or ''

    def _check_key(self):
        sent = request.httprequest.headers.get('X-Api-Key')
        expected = self._expected_key()
        return bool(expected) and sent == expected

    def _check_key_loose(self):
        """Igual que _check_key, pero también acepta la key por query
        string (?key=...). Solo para la ruta de imagen externa: un
        <img src> no puede mandar headers personalizados, así que ahí
        no hay de otra — la key viaja en la URL en vez del header
        X-Api-Key."""
        sent = (
            request.httprequest.headers.get('X-Api-Key')
            or request.httprequest.args.get('key')
        )
        expected = self._expected_key()
        return bool(expected) and sent == expected

    def _json(self, data, status=200):
        resp = Response(
            json.dumps(data, default=str, ensure_ascii=False),
            content_type='application/json',
            status=status,
        )
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Api-Key'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        return resp

    # ------------------------------------------------------------
    # Lógica compartida — sin auth, sin sudo aquí (cada caller decide)
    # ------------------------------------------------------------
    def _get_catalog(self):
        return request.env['product.template'].sudo().get_tire_catalog()

    def _get_partners(self):
        partners = request.env['res.partner'].sudo().search(
            [('customer_rank', '>', 0)], limit=300, order='name'
        )
        return [
            {'id': p.id, 'name': p.display_name, 'vat': p.vat or ''}
            for p in partners
        ]

    def _get_quote(self, partner_id, lines):
        return request.env['sale.order'].sudo().get_promotions_preview(
            partner_id, lines
        )

    def _get_promos(self):
        return request.env['sale.order'].sudo().get_cotizador_promos()

    def _get_stock_refresh(self, product_ids):
        ids = [int(i) for i in (product_ids or [])]
        return request.env['product.template'].sudo().get_stock_refresh(ids)

    def _get_image_bytes(self, product_id, big):
        product = request.env['product.product'].sudo().browse(product_id)
        if not product.exists():
            return None
        if big:
            image_b64 = product.image_1920 or product.image_128
        else:
            image_b64 = product.image_128 or product.image_1920
        if not image_b64:
            return None
        try:
            return base64.b64decode(image_b64)
        except Exception:
            return None

    # ============================================================
    # /external/* — cotizador HTML/JS externo (requiere API key)
    # ============================================================
    @http.route('/ztyres_promotions/external/catalog', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    def external_catalog(self, **kw):
        if request.httprequest.method == 'OPTIONS':
            return self._json({})
        if not self._check_key():
            return self._json({'error': 'API key inválida o no configurada'}, 401)
        return self._json(self._get_catalog())

    @http.route('/ztyres_promotions/external/partners', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    def external_partners(self, **kw):
        if request.httprequest.method == 'OPTIONS':
            return self._json({})
        if not self._check_key():
            return self._json({'error': 'API key inválida o no configurada'}, 401)
        return self._json(self._get_partners())

    @http.route('/ztyres_promotions/external/promos', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    def external_promos(self, **kw):
        if request.httprequest.method == 'OPTIONS':
            return self._json({})
        if not self._check_key():
            return self._json({'error': 'API key inválida o no configurada'}, 401)
        return self._json(self._get_promos())

    @http.route('/ztyres_promotions/external/image/<int:product_id>',
                type='http', auth='public', methods=['GET', 'OPTIONS'],
                csrf=False)
    def external_product_image(self, product_id, **kw):
        """Imagen del producto para el cotizador externo, vía sudo()
        — la ruta nativa de Odoo (/web/image/...) respeta el control
        de acceso normal, y para un visitante sin sesión eso puede
        dar 403 o directamente 500 según el producto/los permisos.
        """
        if request.httprequest.method == 'OPTIONS':
            return self._json({})
        if not self._check_key_loose():
            return Response(status=401)
        image_bytes = self._get_image_bytes(
            product_id, big=request.httprequest.args.get('size') == 'big'
        )
        if image_bytes is None:
            return Response(status=404)
        resp = Response(image_bytes, content_type='image/png')
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Cache-Control'] = 'public, max-age=3600'
        return resp

    @http.route('/ztyres_promotions/external/quote', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    def external_quote(self, **kw):
        if request.httprequest.method == 'OPTIONS':
            return self._json({})
        if not self._check_key():
            return self._json({'error': 'API key inválida o no configurada'}, 401)
        try:
            payload = json.loads(request.httprequest.data or b'{}')
        except ValueError:
            return self._json({'error': 'JSON inválido en el body'}, 400)

        partner_id = payload.get('partner_id') or 0
        lines = self._sanitize_lines(payload.get('lines') or [])
        if not lines:
            return self._json({'error': 'Líneas inválidas o vacías'}, 400)

        try:
            result = self._get_quote(partner_id, lines)
        except Exception as e:
            _logger.exception('Error calculando promociones externas')
            return self._json({'error': str(e)}, 400)

        return self._json(result)

    @http.route('/ztyres_promotions/external/stock', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    def external_stock_refresh(self, **kw):
        """Disponibilidad/DOT/precio al momento, solo para los
        product_id que pide el cotizador (ver get_stock_refresh) —
        NO el catálogo completo."""
        if request.httprequest.method == 'OPTIONS':
            return self._json({})
        if not self._check_key():
            return self._json({'error': 'API key inválida o no configurada'}, 401)
        try:
            payload = json.loads(request.httprequest.data or b'{}')
        except ValueError:
            return self._json({'error': 'JSON inválido en el body'}, 400)
        try:
            result = self._get_stock_refresh(payload.get('product_ids'))
        except Exception as e:
            _logger.exception('Error refrescando disponibilidad externa')
            return self._json({'error': str(e)}, 400)
        return self._json(result)

    # ============================================================
    # /cotizador — página pública del cotizador (sin sesión, sin
    # API key). Renderiza la plantilla QWeb que carga el bundle
    # público (Owl nativo, sin CDN) y monta el componente — ver
    # views/cotizador_owl_templates.xml y
    # static/src/cotizador_owl/public_main.js.
    # ============================================================
    @http.route('/ztyres_promotions/cotizador', type='http',
                auth='user', methods=['GET'], csrf=False)
    def cotizador_public_page(self, **kw):
        denied = self._require_cotizador_access()
        if denied:
            return denied
        return request.render('ztyres_promotions.cotizador_public_page', {
            'ztyres_cotizador_uid': request.env.user.id,
            'ztyres_cotizador_partner_id': request.env.user.partner_id.id,
        })

    # ============================================================
    # /cotizador/* — datos para la app Owl, consumidos tanto por la
    # página pública de arriba como por la versión interna del
    # backend (registry.category("actions"), ver backend_action.js).
    # Sin API key: la conexión ya es directa con Odoo (mismo origen),
    # así que pedir una key ahí no protege nada que la propia ruta
    # pública no esté ya exponiendo. El día que se quiera exigir
    # login para estos datos, basta cambiar auth='user' por
    # auth='user' aquí.
    # ============================================================
    @http.route('/ztyres_promotions/cotizador/catalog', type='http',
                auth='user', methods=['GET'], csrf=False)
    def cotizador_catalog(self, **kw):
        denied = self._require_cotizador_access()
        if denied:
            return denied
        return self._json(self._get_catalog())

    @http.route('/ztyres_promotions/cotizador/partners', type='http',
                auth='user', methods=['GET'], csrf=False)
    def cotizador_partners(self, **kw):
        denied = self._require_cotizador_access()
        if denied:
            return denied
        if request.env.user.has_group('base.group_portal'):
            p = request.env.user.partner_id
            return self._json([{'id': p.id, 'name': p.display_name, 'vat': p.vat or ''}])
        return self._json(self._get_partners())

    @http.route('/ztyres_promotions/cotizador/promos', type='http',
                auth='user', methods=['GET'], csrf=False)
    def cotizador_promos(self, **kw):
        """Promociones vigentes para el catálogo.

        La selección de una promoción es estado local del navegador y
        queda aislada por usuario; no se guarda en una variable global
        del servidor."""
        denied = self._require_cotizador_access()
        if denied:
            return denied
        return self._json(self._get_promos())

    @http.route('/ztyres_promotions/cotizador/image/<int:product_id>',
                type='http', auth='user', methods=['GET'], csrf=False)
    def cotizador_product_image(self, product_id, **kw):
        denied = self._require_cotizador_access()
        if denied:
            return denied
        image_bytes = self._get_image_bytes(
            product_id, big=request.httprequest.args.get('size') == 'big'
        )
        if image_bytes is None:
            return Response(status=404)
        resp = Response(image_bytes, content_type='image/png')
        resp.headers['Cache-Control'] = 'public, max-age=3600'
        return resp

    @http.route('/ztyres_promotions/cotizador/quote', type='http',
                auth='user', methods=['POST'], csrf=False)
    def cotizador_quote(self, **kw):
        denied = self._require_cotizador_access()
        if denied:
            return denied
        if not self._require_same_origin():
            return self._json({'error': 'Solicitud no autorizada'}, 403)
        try:
            payload = json.loads(request.httprequest.data or b'{}')
        except ValueError:
            return self._json({'error': 'JSON inválido en el body'}, 400)

        partner_id = payload.get('partner_id') or 0
        if request.env.user.has_group('base.group_portal'):
            partner_id = request.env.user.partner_id.id
        lines = payload.get('lines') or []
        if not lines:
            return self._json({'error': 'Faltan lines'}, 400)

        try:
            result = self._get_quote(partner_id, lines)
        except Exception as e:
            _logger.exception('Error calculando promociones (cotizador Owl)')
            return self._json({'error': str(e)}, 400)

        return self._json(result)

    @http.route('/ztyres_promotions/cotizador/download/<string:kind>',
                type='http', auth='user', methods=['POST'], csrf=False)
    def cotizador_download(self, kind, **kw):
        """Descarga XLSX del cotizador. `kind` = 'list' | 'order'.
        El body es un JSON con el estado actual del cotizador
        (partner, política, promociones activas, IVA, y — para
        pedido — el carrito). El nombre del archivo lo dictamina
        el modo y el toggle IVA para que el usuario sepa a golpe
        de vista qué está descargando."""
        denied = self._require_cotizador_access()
        if denied:
            return denied
        if not self._require_same_origin():
            return request.make_response('Solicitud no autorizada', [('Content-Type', 'text/plain')], status=403)
        try:
            payload = json.loads(request.httprequest.data or b'{}')
        except ValueError:
            return request.make_response('JSON inválido', [('Content-Type', 'text/plain')], status=400)
        if kind not in ('list', 'order'):
            return request.make_response('kind desconocido', [('Content-Type', 'text/plain')], status=400)
        if request.env.user.has_group('base.group_portal'):
            payload['partner_id'] = request.env.user.partner_id.id
            if kind == 'order':
                cart = self._validate_portal_cart(payload.get('cart') or {})
                if cart is None:
                    return request.make_response('Carrito no autorizado', [('Content-Type', 'text/plain')], status=403)
                payload['cart'] = cart
        try:
            Order = request.env['sale.order'].sudo()
            data = (Order.download_pricelist_xlsx(payload) if kind == 'list'
                    else Order.download_order_xlsx(payload))
        except Exception as e:
            _logger.exception('Error generando descarga %s (cotizador Owl)', kind)
            return request.make_response(str(e), [('Content-Type', 'text/plain')], status=500)

        from datetime import date
        iva_tag = 'ConIVA' if payload.get('show_iva') else 'SinIVA'
        base = 'Lista_de_Precios' if kind == 'list' else 'Pedido'
        filename = f'VTA-FO-03_{base}_{iva_tag}_{date.today().isoformat()}.xlsx'
        return request.make_response(data, headers=[
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', f'attachment; filename="{filename}"'),
            ('Content-Length', str(len(data))),
        ])

    @http.route('/ztyres_promotions/cotizador/stock', type='http',
                auth='user', methods=['POST'], csrf=False)
    def cotizador_stock_refresh(self, **kw):
        denied = self._require_cotizador_access()
        if denied:
            return denied
        if not self._require_same_origin():
            return self._json({'error': 'Solicitud no autorizada'}, 403)
        try:
            payload = json.loads(request.httprequest.data or b'{}')
        except ValueError:
            return self._json({'error': 'JSON inválido en el body'}, 400)
        product_ids = payload.get('product_ids') or []
        try:
            product_ids = [int(x) for x in product_ids]
        except (TypeError, ValueError):
            return self._json({'error': 'product_ids inválidos'}, 400)
        if len(product_ids) > 100:
            return self._json({'error': 'Demasiados productos'}, 400)
        if request.env.user.has_group('base.group_portal'):
            allowed = self._portal_product_ids(product_ids)
            if not set(product_ids).issubset(allowed):
                return self._json({'error': 'Producto no autorizado'}, 403)
        try:
            result = self._get_stock_refresh(product_ids)
        except Exception as e:
            _logger.exception('Error refrescando disponibilidad (cotizador Owl)')
            return self._json({'error': str(e)}, 400)
        return self._json(result)
