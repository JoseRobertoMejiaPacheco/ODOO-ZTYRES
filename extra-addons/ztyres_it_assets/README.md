# ZTYRES IT Assets - Odoo 16

Módulo para controlar equipo de TI, celulares, accesorios, asignaciones,
servicios/historial y mantenimientos.

Compatible con Odoo 16.

Incluye:
- Equipos laptop y escritorio.
- Datos de hardware, red y sistema operativo.
- Programas y sistemas utilizados.
- Accesorios.
- Celulares con IMEI y línea telefónica.
- Asignaciones a usuarios.
- Historial de servicios.
- Mantenimientos con calendario.
- Próximo mantenimiento automático al marcar uno como realizado.
- Actividades de aviso para mantenimientos próximos.
- Catálogos de marcas, programas, accesorios y estados.
- **Formato Z-FO-TI-01 «Asignación y resguardo de equipo de cómputo» en Excel**, lleno
  automáticamente (botón «Imprimir resguardo (Excel)» en el equipo y en la asignación).

La versión 3 usa sintaxis de vistas compatible con Odoo 16 (`attrs`) y
no utiliza expresiones `invisible="..."` propias de versiones posteriores.

## Formato de resguardo (Excel)

El botón **Imprimir resguardo (Excel)** aparece en el formulario de *Equipo* y en el de
*Asignación*. Rellena la plantilla original (`report/ASIGNACION_Y_RESGUARDO_DE_EQUIPO_DE_COMPUTO.xlsx`)
sin alterar su diseño. Desde la asignación se usan sus datos; desde el equipo se usa la
asignación vigente (o la más reciente).

| Formato | Origen |
|---|---|
| Nombre / Área / Puesto / Fecha de asignación | Asignación (si falta, el equipo) |
| Tipo de equipo | Equipo → Tipo de equipo |
| Condición física | Asignación → Condición física (vacío = Nuevo si es la 1.ª asignación, Reasignado si no) |
| Marca, Modelo, # de serie, Procesador | Equipo |
| Sistema operativo | Equipo → Sistema operativo + Versión |
| Almacenamiento | Equipo → Almacenamiento + Tipo de disco |
| Edo. / % de batería | Equipo (No aplica → N/A) |
| Accesorios entregados | Accesorios ligados al equipo (por nombre del tipo; lo no reconocido va en «Otro») |
| Observaciones | Asignación → Observaciones (si falta, las del equipo) |
| Devolución | Solo se llena si la asignación tiene fecha «Hasta»; usa Motivo / Estado / Observaciones de devolución |

Las firmas se dejan en blanco para firmar a mano.
Al actualizar el módulo hay que hacer `-u ztyres_it_assets` (hay campos nuevos en la asignación).
