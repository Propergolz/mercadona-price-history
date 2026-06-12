# Power BI

## Recomendacion

Power BI no debe guardar el historico. En este proyecto, GitHub Actions captura y guarda datos; Power BI solo lee el historico.

La exportacion para Power BI esta normalizada en tres tablas:

```text
data/powerbi/productos.csv
data/powerbi/ubicaciones.csv
data/powerbi/precios_diarios/fecha_snapshot=YYYY-MM-DD.csv
```

Esta estructura sustituye al CSV plano antiguo `mercadona_product_snapshots.csv`, que crecia demasiado y termino chocando con el limite practico de GitHub para archivos grandes.

## Modelo recomendado

Usa un modelo en estrella:

- `FactSnapshots`: precios diarios.
- `DimProducto`: productos.
- `DimUbicacion`: provincias/codigos postales.
- `DimFecha`: calendario DAX.
- `DimCategoria`: opcional, creada desde `DimProducto` si quieres separar seccion/categoria.

Relaciones:

```text
FactSnapshots[id_producto]  -> DimProducto[id_producto]
FactSnapshots[id_ubicacion] -> DimUbicacion[id_ubicacion]
FactSnapshots[fecha_snapshot] -> DimFecha[Date]
```

## Archivos raw de GitHub

Productos:

```text
https://raw.githubusercontent.com/Propergolz/mercadona-price-history/main/data/powerbi/productos.csv
```

Ubicaciones:

```text
https://raw.githubusercontent.com/Propergolz/mercadona-price-history/main/data/powerbi/ubicaciones.csv
```

Precios diarios:

Los precios estan particionados por fecha dentro de:

```text
data/powerbi/precios_diarios/
```

Para leerlos desde Power BI Service sin gateway, usa la API publica de GitHub para listar los archivos y despues combina los CSV.

## Consulta M para precios diarios

```powerquery
let
    Source = Json.Document(
        Web.Contents(
            "https://api.github.com/repos/Propergolz/mercadona-price-history/contents/data/powerbi/precios_diarios?ref=main"
        )
    ),
    Files = Table.FromList(Source, Splitter.SplitByNothing(), null, null, ExtraValues.Error),
    Expanded = Table.ExpandRecordColumn(
        Files,
        "Column1",
        {"name", "download_url"},
        {"name", "download_url"}
    ),
    CsvFiles = Table.SelectRows(Expanded, each Text.EndsWith([name], ".csv")),
    WithContent = Table.AddColumn(
        CsvFiles,
        "content",
        each Csv.Document(
            Web.Contents([download_url]),
            [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
        )
    ),
    Promoted = Table.TransformColumns(
        WithContent,
        {"content", each Table.PromoteHeaders(_, [PromoteAllScalars=true])}
    ),
    Combined = Table.Combine(Promoted[content])
in
    Combined
```

## Consulta M para productos

```powerquery
let
    Source = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/Propergolz/mercadona-price-history/main/data/powerbi/productos.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
in
    PromotedHeaders
```

## Consulta M para ubicaciones

```powerquery
let
    Source = Csv.Document(
        Web.Contents("https://raw.githubusercontent.com/Propergolz/mercadona-price-history/main/data/powerbi/ubicaciones.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
in
    PromotedHeaders
```

## Paginas recomendadas

1. Resumen ejecutivo: evolucion media, productos con cambios y provincias.
2. Productos: buscador de producto, historico y cambios.
3. Categorias: inflacion media por seccion/categoria.
4. Provincias: comparativa territorial.
5. Altas y bajas: productos nuevos o desaparecidos.
