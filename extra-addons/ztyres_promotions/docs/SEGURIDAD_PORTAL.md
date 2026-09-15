# Seguridad del Cotizador para Portal

## Qué cambia

El cotizador que vive dentro de Odoo ya no queda expuesto como `auth='public'`.
Las rutas `/ztyres_promotions/cotizador/*` requieren una sesión de Odoo y solo
aceptan:

- usuarios internos con `ztyres_promotions.group_cotizador_access`;
- usuarios con rol Portal (`base.group_portal`).

La API `/ztyres_promotions/external/*` sigue separada y requiere
`ztyres_promotions.EXTERNAL_API_KEY`.

## Permisos recomendados

### Usuarios Portal

No se debe dar al portal permisos CRUD sobre `product.template`, `product.product`,
`stock.quant`, `ztyres_promo.notas_credito`, `sale.order` ni otros modelos internos
solo para que funcione el cotizador.

El cotizador usa una capa de controlador autenticada y las operaciones de lectura
se ejecutan con `sudo()` después de comprobar la sesión y el rol Portal.

### Usuarios internos

Conservar el permiso existente:

- `Cotizador: acceso a la app de precios`
  - XML ID: `ztyres_promotions.group_cotizador_access`

Este permiso controla la app/menú del backend. No hace falta cambiarlo para los
usuarios Portal.

### ¿Todos los portales o solo algunos?

La versión entregada permite a cualquier usuario con `base.group_portal` entrar al
cotizador. Esto coincide con el requisito de que los usuarios Portal tendrán acceso.
Si posteriormente se necesita que solo ciertos clientes Portal tengan el cotizador,
se recomienda crear un grupo específico `Cotizador Portal` y sustituir la condición
`base.group_portal` por ese grupo, en lugar de conceder permisos CRUD sobre modelos.

## Aislamiento de filtros y promociones seleccionadas

Los filtros, simulaciones de promoción, columnas y preferencia de IVA se guardaban
en `localStorage`. Eso es por navegador, no por cuenta de Odoo, por lo que dos
usuarios que compartieran el mismo equipo podían heredar preferencias del usuario
anterior.

Ahora las claves están aisladas por el UID de Odoo, por ejemplo:

`ztyres_123_sf_filters`

Así, una selección de usuario A no se carga para el usuario B aunque ambos utilicen
el mismo navegador.

El servidor tampoco mantiene un estado global de filtros/promos: cada petición
recibe su propio payload.

## Protección de datos enviados al servidor

Para Portal:

- `partner_id` enviado por el navegador se ignora y se sustituye por el partner de
  la sesión.
- Solo se aceptan variantes pertenecientes a productos de tipo llanta (`tire=True`).
- Se limita el número de líneas/carrito y las cantidades.
- El refresh de stock solo acepta IDs de llantas autorizadas.
- Las descargas de pedido fuerzan el partner de la sesión y validan el carrito.
- Las peticiones POST oficiales llevan el header `X-Ztyres-Cotizador: 1` y se valida
  `Origin`/`Referer` cuando el navegador los proporciona.

## Promociones

La lista de promociones vigentes sigue siendo la configuración comercial vigente de
`ztyres_promo`; no se almacena la selección de un usuario en servidor. Lo que un
usuario activa/desactiva en el simulador queda aislado en su navegador/UID.

Si en el futuro una promoción debe ser visible solo para determinados clientes,
la siguiente mejora debe ser una regla explícita de alcance por partner/cliente en
`ztyres_promo`; no debe resolverse ocultándola solamente con JavaScript.
