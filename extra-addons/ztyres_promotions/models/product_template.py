# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # -----------------------------------------------------------------
    # Versión EN BLOQUE de sale_dot.sale.order.line.
    # get_catalog_price_for_product() / get_free_qty_and_dot_range_for_
    # product(): mismo resultado exacto que esos dos métodos (mismas
    # listas de precios válidas, mismo filtro de stock.quant, mismo
    # rango_fechas — de hecho se reutiliza _get_valid_pricelists() y
    # rango_fechas() de sale_dot directo, no se reinventan), pero
    # resolviendo TODOS los productos con 2 consultas en vez de 2 por
    # producto. Con miles de productos, eso es la diferencia entre
    # ~20 segundos y menos de 1.
    # -----------------------------------------------------------------
    def _batch_price_and_stock(self, variants):
        sol_model = self.env['sale.order.line']
        out = {v.id: {'price': 0.0, 'free_qty': 0.0, 'dot_range': 'N/A'} for v in variants}
        if not variants:
            return out

        # ---- Precio: igual que get_catalog_price_for_product, pero
        # para TODOS los templates de una vez. Mismas listas de
        # precios válidas (_get_valid_pricelists(), sin tocar) y el
        # mismo criterio de "el fixed_price más bajo, ignorando los
        # que están en 0" — si ninguno califica, se cae a lst_price,
        # igual que el original.
        tmpl_ids = variants.mapped('product_tmpl_id').ids
        valid_pricelists = sol_model._get_valid_pricelists()
        pricelist_items = self.env['product.pricelist.item'].search([
            ('product_tmpl_id', 'in', tmpl_ids),
            ('pricelist_id', 'in', valid_pricelists),
        ])
        min_price_by_tmpl = {}
        for item in pricelist_items:
            if not item.fixed_price:
                continue
            tid = item.product_tmpl_id.id
            if tid not in min_price_by_tmpl or item.fixed_price < min_price_by_tmpl[tid]:
                min_price_by_tmpl[tid] = item.fixed_price

        # ---- Stock + DOT: igual que get_free_qty_and_dot_range_for_
        # product, pero para TODAS las variantes de una vez. Mismo
        # filtro (cantidad > 0, ubicación interna), mismo cálculo
        # (quantity - reserved_quantity), y rango_fechas() de
        # sale_dot se reutiliza tal cual para el formateo del rango
        # de años — eso es puro Python, no pega a la base de datos,
        # así que llamarlo por producto (no en bloque) no cuesta nada.
        quants = self.env['stock.quant'].search([
            ('product_id', 'in', variants.ids),
            ('quantity', '>', 0),
            ('location_id.usage', '=', 'internal'),
        ])
        qty_by_variant = defaultdict(float)
        lots_by_variant = defaultdict(list)
        for q in quants:
            qty_by_variant[q.product_id.id] += (q.quantity - q.reserved_quantity)
            if q.lot_id:
                lots_by_variant[q.product_id.id].append(q.lot_id.name)

        for v in variants:
            tmpl_price = min_price_by_tmpl.get(v.product_tmpl_id.id)
            out[v.id] = {
                'price': tmpl_price if tmpl_price else v.lst_price,
                'free_qty': qty_by_variant.get(v.id, 0.0),
                'dot_range': sol_model.rango_fechas(lots_by_variant.get(v.id, [])),
            }
        return out

    @api.model
    def get_tire_catalog(self):
        """Valores que el cotizador (HTML/OWL) necesita para armar sus
        líneas: el product_id real (variante, no template) más los
        atributos que las reglas usan para filtrar. Sin esto, el
        cotizador no tiene cómo mandar un product_id válido a
        get_promotions_preview.

        Incluye también el resto de criterios de clasificación de
        ztyres_products (los mismos que soportan attrs/exclude_attrs en
        promo_classification.py) para que el cotizador pueda
        mostrarlos/filtrarlos en su tabla. Esto es solo para la
        experiencia de uso del vendedor — el cálculo de promociones NO
        depende de lo que mande el cotizador en estos campos; siempre
        lee el producto real desde Odoo.

        Sin caché a propósito: cada llamada lee el catálogo, precio y
        disponibilidad directo de la base de datos. Antes esto era
        lento porque get_free_qty_and_dot_range_for_product() /
        get_catalog_price_for_product() (sale_dot) se llamaban una por
        una por cada producto — eso ya se corrigió en
        _batch_price_and_stock() (2 consultas para TODOS los
        productos, no 2 por producto), así que ya no hace falta un
        caché para que esto sea rápido.
        """
        return self._build_tire_catalog()

    def _build_tire_catalog(self):
        products = self.search([('tire', '=', True)])
        variants = products.mapped('product_variant_id').filtered(lambda v: v)
        stock_price = self._batch_price_and_stock(variants)
        out = []
        for p in products:
            variant = p.product_variant_id
            if not variant:
                continue
            info = stock_price.get(variant.id, {})
            catalog_price = info.get('price', 0.0)
            free_qty = info.get('free_qty', 0.0)
            dot_range = info.get('dot_range', 'N/A')

            # Si no hay precio válido o no hay stock libre, el producto
            # no se puede cotizar de verdad — se omite del catálogo
            # externo en vez de mostrarlo con $0.00 o "0 disp.", que
            # solo confunde al vendedor. No afecta el catálogo interno
            # de Odoo, solo lo que ve el cotizador.
            if not catalog_price or not free_qty:
                continue

            out.append({
                'product_id': variant.id,
                # Plantilla del producto — los cupones de ztyres_promo
                # se asignan por product.template, no por variante; el
                # cotizador necesita este id para simular su monto.
                'tmpl_id': p.id,
                # Clave interna del producto (referencia / SKU): lo único,
                # junto con la medida, que se muestra ahora en la lista
                # plana del cotizador. Se cae a la del template si la
                # variante no tiene una propia capturada.
                'code': variant.default_code or p.default_code or '',
                'name': p.display_name,
                'brand': p.brand_id.name or '',
                'tier': p.tier_id.name or '',
                'medida': p.tire_measure_id.name or '',
                'rim': p.tire_measure_id.rim_id.number if p.tire_measure_id else 0,
                'price': catalog_price,
                'free_qty': free_qty,
                'dot_range': dot_range,
                # variant.weight puede venir vacío si nunca se
                # capturó a nivel variante (caso normal: la mayoría de
                # las llantas no tienen variantes con peso distinto al
                # del producto/template) — se cae al peso del
                # template en ese caso.
                'weight': variant.weight or p.weight or 0.0,
                # Resto de criterios de clasificación — ver
                # promo_classification.py para la lista oficial que
                # soportan attrs/exclude_attrs en las reglas.
                'segment': p.segment_id.name or '',
                'type': p.type_id.name or '',
                'manufacturer': p.manufacturer_id.name or '',
                'model': p.model_id.name or '',
                'usage': p.usage_id.name or '',
                'speed': p.speed_id.name or '',
                'treadwear': p.treadwear_id.name or '',
                'original_equipment': p.original_equipment_id.name or '',
                'supplier_segment': p.supplier_segment_id.name or '',
                'e_mark': p.e_mark_id.name or '',
                's_mark': p.s_mark_id.name or '',
                'ccc': p.ccc_id.name or '',
                'face': p.face_id.name or '',
                'layer': p.layer_id.name or '',
                'index_of_load': p.index_of_load_id.name or '',
                'country': p.country_id.name or '',
                'hq': p.hq_id.name or 0,
                # floor_depth_id.name está roto en ztyres_products (el
                # compute asigna record._rec_name en vez de
                # record.name, queda siempre vacío); usamos 'depth'
                # directo, igual que promo_classification.py.
                'floor_depth': p.floor_depth_id.depth or 0,
                'product_nationality': p.product_nationality or '',
            })
        return out

    @api.model
    def get_stock_refresh(self, product_ids):
        """Refresca SOLO disponibilidad/rango de DOT/precio para una
        lista puntual de product_id (variantes) — no reconstruye el
        catálogo completo. Pensado para llamarse justo cuando el
        vendedor ABRE un grupo de medida en el cotizador: el catálogo
        completo se trae una sola vez al cargar la página (rápido,
        liviano: nombres/marca/atributos no cambian solos), pero
        'disponible' SÍ puede cambiar en cualquier momento — otro
        vendedor puede vender o liberar piezas mientras este cotizador
        sigue abierto. Sin este refresh puntual, el vendedor vería un
        número de stock potencialmente viejo hasta recargar toda la
        página.

        No se llama para los 50,000 productos de una sola vez (eso
        sería el mismo problema de origen, solo movido de lugar) —
        solo para los product_id de la medida que se acaba de abrir,
        normalmente unos cuantos.
        """
        variants = self.env['product.product'].browse(product_ids).exists()
        stock_price = self._batch_price_and_stock(variants)
        return {
            v.id: {
                'free_qty': stock_price[v.id]['free_qty'],
                'dot_range': stock_price[v.id]['dot_range'],
                'price': stock_price[v.id]['price'],
            }
            for v in variants
        }
