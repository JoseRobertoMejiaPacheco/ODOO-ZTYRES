# Banco de pruebas de Excel del cotizador

El test `tests/test_cotizador_xlsx.py` crea promociones y productos ficticios,
genera los dos archivos que ofrece el cotizador y vuelve a abrirlos para
validar:

- descripción natural de las promociones;
- generación de lista de precios y pedido;
- filtros, paneles inmovilizados y configuración horizontal de impresión;
- ausencia de libros corruptos;
- coherencia de la presentación básica en ambos archivos.

## Ejecutar y conservar los dos Excel

```bash
docker exec -e ZTYRES_XLSX_FIXTURES_DIR=/tmp/cotizador_xlsx \
  odoo16_ee_ztyres_web odoo \
  -d ZTYRES -u ztyres_promotions --test-enable --stop-after-init \
  --workers=0 --log-level=test --test-tags=/ztyres_promotions
```

Al terminar, los archivos quedan dentro del contenedor en:

```text
/tmp/cotizador_xlsx/lista_precios_datos_ficticios.xlsx
/tmp/cotizador_xlsx/pedido_datos_ficticios.xlsx
```

Para copiarlos al directorio actual del servidor:

```bash
docker cp odoo16_ee_ztyres_web:/tmp/cotizador_xlsx/. ./cotizador_xlsx/
```
