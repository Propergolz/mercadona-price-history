# Mercadona Price History

Proyecto para capturar snapshots diarios del catalogo de Mercadona y analizarlos en Power BI.

## Columna unidad_venta

La exportacion de Power BI incluye `unidad_venta`, una descripcion normalizada de como se vende el producto.

Ejemplos:

- `8 ud. x 0,125 kg`
- `6 botellines x 0,25 l`
- `Botella 1 l`
- `0,25 kg`

La API de Mercadona ofrece datos actuales, no historico. Este proyecto crea ese historico guardando una foto diaria de productos, precios y disponibilidad.

## Estado inicial

- Provincia piloto: Valencia.
- Codigo postal piloto: `46001`.
- Frecuencia prevista: diaria.
- Formato analitico: Parquet.
- Automatizacion: GitHub Actions.
- Coste previsto del prototipo: 0 EUR adicionales, usando GitHub Free y tu licencia actual de Power BI.

## Estructura

```text
.
├── .github/workflows/daily-capture.yml
├── data/
│   ├── parquet/
│   │   ├── snapshots/
│   │   └── mercadona_product_snapshots.parquet
│   ├── powerbi/
│   │   └── mercadona_product_snapshots.csv
│   └── raw/
├── docs/
├── scripts/capture_daily_snapshot.py
└── src/mercadona_history/
