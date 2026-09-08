# Z Helpdesk

Complemento para Odoo 16 Enterprise.

## Funciones

- Completa automáticamente el solicitante interno, contacto y correo.
- Solo los administradores de Helpdesk pueden cambiar esos datos.
- Agrega prioridad del 1 al 10 con diez estrellas y la sincroniza con la prioridad nativa.
- Muestra la prioridad con texto en las tarjetas Kanban.
- Sustituye las estrellas nativas por la prioridad textual en la vista de lista.
- Agrega debajo de la descripción una sección de evidencias para archivos y capturas pegadas.

## Instalación

1. Copiar `z_helpdesk` al `addons_path`.
2. Reiniciar Odoo.
3. Actualizar la lista de aplicaciones.
4. Instalar **Z Helpdesk**.

## Nota

La duración del desarrollo no se fija mediante la prioridad ni el tipo de actividad; se establece individualmente en la fecha límite del ticket o actividad.
# Z Helpdesk

Los usuarios internos con permiso de Helpdesk pueden registrar solicitudes aunque no
pertenezcan a un equipo. En ese caso, el ticket se crea sin equipo ni responsable y
queda pendiente de asignación por un administrador de Servicio de asistencia.
