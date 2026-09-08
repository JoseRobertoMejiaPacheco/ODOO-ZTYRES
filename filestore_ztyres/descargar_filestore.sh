#!/usr/bin/env bash

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
FILESTORE="${1:-/var/lib/odoo/.local/share/Odoo/filestore/ZTYRES}"
SALIDA_DIR="${2:-$SCRIPT_DIR}"

if [[ ! -d "$FILESTORE" ]]; then
    echo "ERROR: No existe el filestore: $FILESTORE" >&2
    exit 1
fi

ARCHIVO_SALIDA="$SALIDA_DIR/archivos_filestore_ZTYRES_$(date +%Y%m%d_%H%M%S).tar.gz"
DIRECTORIO_TEMPORAL="$(mktemp -d "$SCRIPT_DIR/.filestore_temporal.XXXXXX")"
trap 'rm -rf -- "$DIRECTORIO_TEMPORAL"' EXIT

ARCHIVOS=(
    "7d/7d491f0c640169793527b37932c246f99e4a1f5b"
    "36/363d3747bca68a4eef55368cc4cc25af67b9a12f"
    "c4/c438d6fa28de80d6a2c0274cf08f0f217ed31620"
    "a3/a3222e988bfe4da02d167aae4ef9c52d2da1ab9c"
    "c8/c8e0f6d0070441c88065f6ade60e8673dd56cead"
    "e6/e61618221d00246407e6df5a0327703d0badbe12"
    "5c/5c4535ae06831f8d4ead0b9f6ab64bd34634b241"
    "3e/3e39254981aba7b8c70c789842cca09efaaedda8"
    "52/52816367a0e446d7aab18adff47affe9ace9e17e"
    "d3/d35f3170c2282b327f60a72234bfe4618927e581"
    "b3/b3e0452172769d722f1d013b42fb4a3936f5c28a"
    "29/299ebf54a1329f6c6dd535fab260d98b3b12843c"
    "66/6609e190e6057ff2211907fc082a2efbfdebfd4f"
    "19/190018f5712ac7a9d85098daafb901a03b8b4bc0"
    "a4/a4e8838313e488eb106029c5803ab183db6d3543"
    "1f/1fcd6567c531052ef1a76add215687635eb5ad9d"
    "d4/d4a167c930473ba8b70bf77be75259e99e698a72"
    "a6/a65d090d9ce80f03d935dd09601a65fb927c3f40"
    "c2/c24a3d19df056e6a93155be80569ec643773bce4"
    "33/331989d9217a0395773187b282737abbb4e2999f"
    "af/aff5118f474867075855b729f18c36659726b900"
    "bc/bcce52efa0ea1e053bd6d5ad46971ad45ddd513f"
)

ENCONTRADOS=0
FALTANTES=0

for RUTA_RELATIVA in "${ARCHIVOS[@]}"; do
    ORIGEN="$FILESTORE/$RUTA_RELATIVA"
    DESTINO="$DIRECTORIO_TEMPORAL/$RUTA_RELATIVA"
    if [[ -f "$ORIGEN" ]]; then
        mkdir -p -- "$(dirname "$DESTINO")"
        cp -a -- "$ORIGEN" "$DESTINO"
        echo "OK: $RUTA_RELATIVA"
        ENCONTRADOS=$((ENCONTRADOS + 1))
    else
        echo "FALTA: $RUTA_RELATIVA"
        FALTANTES=$((FALTANTES + 1))
    fi
done

if [[ "$ENCONTRADOS" -eq 0 ]]; then
    echo "ERROR: No se encontró ninguno de los archivos." >&2
    exit 2
fi

tar -C "$DIRECTORIO_TEMPORAL" -czf "$ARCHIVO_SALIDA" .
printf '\nEncontrados: %s | Faltantes: %s\nRESULTADO=%s\n' "$ENCONTRADOS" "$FALTANTES" "$ARCHIVO_SALIDA"
