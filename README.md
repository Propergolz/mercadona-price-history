# Mercadona Price History

Proyecto para capturar snapshots diarios del catalogo de Mercadona y analizarlos en Power BI.

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
