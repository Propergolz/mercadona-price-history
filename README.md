# Mercadona Price History

Proyecto para capturar snapshots diarios del catalogo de Mercadona y analizarlos en Power BI.

La API de Mercadona ofrece datos actuales, no historico. Este proyecto crea ese historico guardando una foto diaria de productos, precios y disponibilidad.

## Estado inicial

- Provincias: Madrid, Barcelona, Valencia, Alicante y Sevilla.
- Frecuencia prevista: diaria.
- Formato analitico: Parquet y CSV normalizado para Power BI.
- Automatizacion: GitHub Actions.
- Coste previsto del prototipo: 0 EUR adicionales, usando GitHub Free y tu licencia actual de Power BI.

## Columna unidad_venta

La exportacion de Power BI incluye `unidad_venta`, una descripcion normalizada de como se vende el producto.

Ejemplos:

- `8 ud. x 0,125 kg`
- `6 botellines x 0,25 l`
- `Botella 1 l`
- `0,25 kg`

## Estructura

```text
.
|-- .github/workflows/daily-capture.yml
|-- data/
|   |-- parquet/
|   |   |-- snapshots/
|   |   `-- mercadona_product_snapshots.parquet
|   |-- powerbi/
|   |   |-- productos.csv
|   |   |-- ubicaciones.csv
|   |   `-- precios_diarios/
|   |       |-- fecha_snapshot=2026-06-12.csv
|   |       `-- ...
|   `-- raw/
|-- docs/
|-- scripts/capture_daily_snapshot.py
`-- src/mercadona_history/
```

## Exportacion para Power BI

La exportacion de Power BI esta normalizada para evitar un CSV historico gigante:

- `data/powerbi/productos.csv`: una fila por producto.
- `data/powerbi/ubicaciones.csv`: una fila por provincia/codigo postal.
- `data/powerbi/precios_diarios/fecha_snapshot=YYYY-MM-DD.csv`: precios, disponibilidad y novedades del dia.

El archivo antiguo `data/powerbi/mercadona_product_snapshots.csv` queda retirado porque superaba el limite practico de GitHub para archivos grandes.
