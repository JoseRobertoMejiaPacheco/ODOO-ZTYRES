# -*- coding: utf-8 -*-
{
    'name': 'Purchase Qty Decrease Fix (Rutas Push/Pull)',
    'version': '17.0.1.0.0',
    'summary': 'Evita el error "No se encontró ninguna regla de reabastecimiento" '
               'al reducir la cantidad de una línea de compra por debajo o igual '
               'a lo ya recibido, en rutas con pasos push encadenados (ej. '
               'Proveedor > Tránsito > Almacén).',
    'description': """
Problema que soluciona
=======================
En Odoo, cuando una línea de compra usa una ruta con un tramo "push" encadenado
(por ejemplo: Proveedor -> Tránsito Internacional -> Almacén), reducir la
cantidad pedida a un valor igual o menor a lo ya recibido/facturado puede
generar un "movimiento push negativo" que Odoo intenta resolver invirtiendo
origen y destino del movimiento. Esto dispara una nueva búsqueda de regla de
reabastecimiento que normalmente no existe (no hay ruta de "regreso" al
proveedor), y termina en el error:

    "No se encontró ninguna regla de reabastecimiento [...] en
    'Ubicaciones de Socios/Proveedor'. Verifique la configuración de rutas
    en el producto."

Este módulo intercepta el `write()` de `purchase.order.line` y, únicamente
cuando la nueva cantidad pedida queda por debajo o igual a lo ya recibido,
cancela primero TODA la cadena de movimientos de stock pendientes asociados
a esa línea (siguiendo los movimientos encadenados por push/pull hasta el
final), antes de aplicar el cambio de cantidad. Así no queda nada pendiente
que Odoo necesite "revertir", y el error no se produce.

Notas
=====
- Solo actúa sobre movimientos NO finalizados (no toca los ya hechos ni
  movimientos de otros productos en el mismo picking).
- Solo se activa cuando el pedido está confirmado (estado 'purchase') y la
  nueva cantidad es <= a lo ya recibido.
- Cada vez que se dispara, deja un registro en el log (odoo.log) Y un
  mensaje en el chatter de la orden de compra, indicando qué movimientos
  se cancelaron y por qué.
- Tras cancelar cada movimiento pendiente, su cantidad (product_uom_qty)
  se pone en 0, para que en los traslados no quede una demanda visible
  de algo que ya no se va a mover.
- Es un workaround puntual para este comportamiento; no modifica ningún
  archivo del core de Odoo.
""",
    'category': 'Inventory/Purchase',
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['purchase', 'purchase_stock', 'stock'],
    'installable': True,
    'application': False,
}
