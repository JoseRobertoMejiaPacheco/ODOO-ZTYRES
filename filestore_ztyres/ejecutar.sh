#!/usr/bin/env bash

set -euo pipefail

CONTENEDOR="odoo16_ee_ztyres_web"
DIRECTORIO_INTERNO="/var/lib/odoo/scripts_filestore_ztyres"
RUTA_INTERNA="$DIRECTORIO_INTERNO/descargar_filestore.sh"

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker no está disponible." >&2
    exit 1
fi

if ! docker inspect "$CONTENEDOR" >/dev/null 2>&1; then
    echo "ERROR: No existe el contenedor $CONTENEDOR." >&2
    exit 1
fi

if [[ "$(docker inspect -f '{{.State.Running}}' "$CONTENEDOR")" != "true" ]]; then
    echo "ERROR: El contenedor $CONTENEDOR no está ejecutándose." >&2
    exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DIRECTORIO_SALIDA="${1:-$SCRIPT_DIR}"
mkdir -p -- "$DIRECTORIO_SALIDA"

docker exec -u odoo "$CONTENEDOR" mkdir -p "$DIRECTORIO_INTERNO"
docker cp "$SCRIPT_DIR/descargar_filestore.sh" "$CONTENEDOR:$RUTA_INTERNA"

SALIDA="$(docker exec -u odoo "$CONTENEDOR" bash "$RUTA_INTERNA")"
printf '%s\n' "$SALIDA"

ARCHIVO_INTERNO="$(printf '%s\n' "$SALIDA" | sed -n 's/^RESULTADO=//p' | tail -n 1)"
if [[ -z "$ARCHIVO_INTERNO" ]]; then
    echo "ERROR: No se pudo determinar el archivo generado." >&2
    exit 2
fi

NOMBRE_ARCHIVO="$(basename -- "$ARCHIVO_INTERNO")"
docker cp "$CONTENEDOR:$ARCHIVO_INTERNO" "$DIRECTORIO_SALIDA/$NOMBRE_ARCHIVO"

echo
echo "Listo: $DIRECTORIO_SALIDA/$NOMBRE_ARCHIVO"
echo "El filestore no fue modificado."
