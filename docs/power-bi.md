# Power BI

## Recomendacion

Usa Power BI en modo Import sobre `data/parquet/mercadona_product_snapshots.parquet`.

Power BI no debe ser la pieza que guarda historico. En este proyecto, GitHub Actions captura y guarda datos; Power BI solo lee el historico.

## Opcion A: prototipo local

1. Clona o descarga el repositorio.
2. Abre Power BI Desktop.
3. Elige `Obtener datos > Parquet`.
4. Selecciona:

```text
C:\Users\sergi\Documents\mercadona-price-history\data\parquet\mercadona_product_snapshots.parquet
```

Esta opcion es buena para construir el informe, pero el refresco en Power BI Service dependeria de un gateway si el archivo esta en tu PC.

## Opcion B: GitHub raw publico

Si aceptas que el archivo Parquet sea publico, Power BI Service puede refrescarlo desde una URL raw.

Power Query:

```powerquery
let
    Source = Web.Contents("https://raw.githubusercontent.com/OWNER/REPO/main/data/parquet/mercadona_product_snapshots.parquet"),
    Parquet = Parquet.Document(Source)
in
    Parquet
```

Esta es la opcion mas simple para publicar un informe publico sin infraestructura adicional.

## Opcion C: repo privado

Un repo privado es mejor para el codigo, pero complica el refresco automatico en Power BI Service porque Power BI necesita credenciales para leer el archivo.

Se puede hacer con GitHub API y un token de acceso, pero hay que tratar ese token como secreto. Para un informe publicado de forma publica, normalmente no compensa proteger el dataset de origen si el propio informe expone los datos agregados y potencialmente el detalle.

## Medidas DAX sugeridas

Precio medio:

```DAX
Precio Medio = AVERAGE('Snapshots'[price])
```

Variacion absoluta vs snapshot anterior:

```DAX
Variacion Precio =
VAR Producto = SELECTEDVALUE('Snapshots'[product_id])
VAR Ubicacion = SELECTEDVALUE('Snapshots'[location_id])
VAR FechaActual = MAX('Snapshots'[snapshot_date])
VAR PrecioActual = MAX('Snapshots'[price])
VAR FechaAnterior =
    CALCULATE(
        MAX('Snapshots'[snapshot_date]),
        FILTER(
            ALL('Snapshots'),
            'Snapshots'[product_id] = Producto
                && 'Snapshots'[location_id] = Ubicacion
                && 'Snapshots'[snapshot_date] < FechaActual
        )
    )
VAR PrecioAnterior =
    CALCULATE(
        MAX('Snapshots'[price]),
        FILTER(
            ALL('Snapshots'),
            'Snapshots'[product_id] = Producto
                && 'Snapshots'[location_id] = Ubicacion
                && 'Snapshots'[snapshot_date] = FechaAnterior
        )
    )
RETURN
    PrecioActual - PrecioAnterior
```

Variacion porcentual:

```DAX
Variacion % = DIVIDE([Variacion Precio], MAX('Snapshots'[price]) - [Variacion Precio])
```

## Paginas recomendadas

1. Resumen ejecutivo: evolucion media, productos con cambios y provincias.
2. Productos: buscador de producto, historico y cambios.
3. Categorias: inflacion media por seccion/categoria.
4. Provincias: comparativa territorial.
5. Altas y bajas: productos nuevos o desaparecidos.

