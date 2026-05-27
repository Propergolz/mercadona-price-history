# Mercadona Price History

Proyecto para capturar snapshots diarios del catálogo de Mercadona y analizarlos en Power BI.

La API de Mercadona ofrece datos actuales, no histórico. Este proyecto crea ese histórico guardando una foto diaria de productos, precios y disponibilidad.

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
│   └── raw/
├── docs/
├── scripts/capture_daily_snapshot.py
└── src/mercadona_history/
```

## Primera ejecucion local

Instala Python 3.11 o superior y ejecuta:

```powershell
cd C:\Users\sergi\Documents\mercadona-price-history
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\capture_daily_snapshot.py --max-categories 2
```

`--max-categories 2` sirve para probar rapido. Para capturar todo el catalogo:

```powershell
python scripts\capture_daily_snapshot.py
```

## Salidas principales

- `data/raw/YYYY-MM-DD/<location_id>/`: respuestas JSON comprimidas.
- `data/parquet/snapshots/snapshot_date=YYYY-MM-DD/<location_id>.parquet`: snapshot diario.
- `data/parquet/mercadona_product_snapshots.parquet`: historico consolidado para Power BI.

## Automatizacion diaria

El workflow `.github/workflows/daily-capture.yml` ejecuta la captura cada dia y commitea los nuevos archivos de datos.

Tambien puede lanzarse manualmente desde GitHub:

`Actions > Daily Mercadona price capture > Run workflow`

## Siguiente ampliacion: 5 provincias

Cuando el piloto de Valencia funcione, edita `src/mercadona_history/config.py` y cambia `DEFAULT_LOCATIONS` por:

```python
DEFAULT_LOCATIONS = [
    Location(location_id="madrid_28001", province="Madrid", postal_code="28001"),
    Location(location_id="barcelona_08001", province="Barcelona", postal_code="08001"),
    Location(location_id="valencia_46001", province="Valencia", postal_code="46001"),
    Location(location_id="alicante_03001", province="Alicante", postal_code="03001"),
    Location(location_id="sevilla_41001", province="Sevilla", postal_code="41001"),
]
```

## Nota responsable

Este proyecto usa endpoints observados de una API no oficial. Mantiene una frecuencia baja, cachea resultados historicos y evita endpoints de cuenta, autenticacion, carrito o datos personales.

