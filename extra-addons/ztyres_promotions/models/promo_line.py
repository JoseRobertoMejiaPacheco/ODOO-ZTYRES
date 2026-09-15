# -*- coding: utf-8 -*-
"""Línea de producto normalizada, común a todos los orígenes.

El cotizador no tiene un sale.order: es una cotización en vivo. Esta
clase es la forma intermedia con la que se arma su preview antes de
traducirla a las líneas falsas que espera el motor de ztyres_promo
(ver `_NcEvalLine` en sale_order.py).

Cada origen (sale.order, el carrito del cotizador, el controlador
externo) tiene su propio adaptador corto — `_promo_lines()` y
`_get_promo_lines_from_cart()`. Si agregas un origen nuevo, escribes
un adaptador nuevo.

Nota: el motor propio del módulo (ztyres_promotions.rule) fue
eliminado; hoy el único motor de promociones es el de ztyres_promo.
"""


class PromoLine:
    """Línea de producto normalizada que entiende el motor de promociones.

    Cualquier objeto con estos 4 atributos funciona (duck typing); esta
    clase es solo una conveniencia para no repetir __init__ en cada
    adaptador y para dejar el contrato documentado en un solo lugar.

    Atributos:
        id: identificador de la línea dentro de la lista que se le pasa
            al motor. No necesita ser un ID real de base de datos — en
            el cotizador externo puede ser simplemente el índice
            (0, 1, 2...) de la línea dentro del payload.
        product_id: registro product.product (se usan sus campos
            .tire, .brand_id, .tier_id, .tire_measure_id,
            .default_code para los filtros de las reglas).
        qty: cantidad de piezas en esta línea.
        price_unit: precio unitario a usar en reglas que suman pesos
            (amount_by, descuentos por monto). Normalmente el precio
            de lista o el precio realmente cotizado/facturado, según
            lo que tenga sentido para el origen.
    """
    __slots__ = ('id', 'product_id', 'qty', 'price_unit')

    def __init__(self, id, product_id, qty, price_unit):
        self.id = id
        self.product_id = product_id
        self.qty = qty
        self.price_unit = price_unit

    def __repr__(self):
        name = self.product_id.display_name if self.product_id else None
        return (f"PromoLine(id={self.id!r}, product_id={name!r}, "
                f"qty={self.qty!r}, price_unit={self.price_unit!r})")
