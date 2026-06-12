from __future__ import annotations

import gzip
import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


SPANISH_COLUMN_NAMES = {
    "snapshot_date": "fecha_snapshot",
    "extraction_timestamp": "marca_temporal_extraccion",
    "location_id": "id_ubicacion",
    "province": "provincia",
    "postal_code": "codigo_postal",
    "warehouse_code": "codigo_almacen",
    "section_id": "id_seccion",
    "section_name": "seccion",
    "category_id": "id_categoria",
    "category_name": "categoria",
    "product_id": "id_producto",
    "product_name": "producto",
    "brand": "marca",
    "packaging": "formato_envase",
    "sales_unit": "unidad_venta",
    "thumbnail": "url_imagen",
    "imagen": "url_imagen",
    "share_url": "url_producto",
    "price": "precio",
    "unit_price": "precio_referencia",
    "unit_size": "cantidad_unidad",
    "size_format": "formato_cantidad",
    "tax_percentage": "porcentaje_iva",
    "is_new": "es_novedad",
    "is_available": "disponible",
    "raw_product": "producto_json",
}


POWERBI_COLUMNS = [
    "fecha_snapshot",
    "marca_temporal_extraccion",
    "id_ubicacion",
    "provincia",
    "codigo_postal",
    "codigo_almacen",
    "id_seccion",
    "seccion",
    "id_categoria",
    "categoria",
    "id_producto",
    "producto",
    "slug",
    "marca",
    "formato_envase",
    "unidad_venta",
    "url_imagen",
    "url_producto",
    "precio",
    "precio_referencia",
    "cantidad_unidad",
    "formato_cantidad",
    "porcentaje_iva",
    "es_novedad",
    "disponible",
]

POWERBI_PRODUCT_COLUMNS = [
    "id_producto",
    "producto",
    "slug",
    "marca",
    "formato_envase",
    "unidad_venta",
    "url_imagen",
    "url_producto",
    "id_seccion",
    "seccion",
    "id_categoria",
    "categoria",
    "porcentaje_iva",
]

POWERBI_LOCATION_COLUMNS = [
    "id_ubicacion",
    "provincia",
    "codigo_postal",
    "codigo_almacen",
]

POWERBI_DAILY_PRICE_COLUMNS = [
    "fecha_snapshot",
    "marca_temporal_extraccion",
    "id_producto",
    "id_ubicacion",
    "precio",
    "precio_referencia",
    "cantidad_unidad",
    "formato_cantidad",
    "es_novedad",
    "disponible",
]


def write_raw_json(
    payload: dict[str, Any],
    *,
    data_dir: Path,
    snapshot_date: date,
    location_id: str,
    name: str,
) -> Path:
    raw_dir = data_dir / "raw" / snapshot_date.isoformat() / location_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{name}.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False)
    return path


def write_snapshot_parquet(
    rows: list[dict[str, Any]],
    *,
    data_dir: Path,
    snapshot_date: date,
    location_id: str,
) -> Path:
    snapshot_dir = data_dir / "parquet" / "snapshots" / f"snapshot_date={snapshot_date.isoformat()}"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    path = snapshot_dir / f"{location_id}.parquet"

    dataframe = pd.DataFrame(rows)
    if "producto_json" in dataframe.columns:
        dataframe["producto_json"] = dataframe["producto_json"].apply(
            lambda value: json.dumps(value, ensure_ascii=False)
        )

    dataframe.to_parquet(path, index=False)
    return path


def rebuild_consolidated_parquet(*, data_dir: Path) -> Path | None:
    snapshot_root = data_dir / "parquet" / "snapshots"
    files = sorted(snapshot_root.glob("snapshot_date=*/*.parquet"))
    if not files:
        return None

    frames = []
    for path in files:
        print(f"Reading snapshot file: {path}")
        frame = pd.read_parquet(path)
        frame = normalize_column_names(frame)
        frames.append(frame)

    consolidated = pd.concat(frames, ignore_index=True, sort=False)
    consolidated = normalize_column_names(consolidated)

    for column in ["fecha_snapshot", "id_ubicacion", "id_producto"]:
        if column not in consolidated.columns:
            consolidated[column] = None

    consolidated = consolidated.drop_duplicates(
        subset=["fecha_snapshot", "id_ubicacion", "id_producto"],
        keep="last",
    )

    output_path = data_dir / "parquet" / "mercadona_product_snapshots.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    consolidated.to_parquet(output_path, index=False)

    write_powerbi_tables(consolidated, data_dir=data_dir)
    return output_path


def write_powerbi_csv(dataframe: pd.DataFrame, *, data_dir: Path) -> Path:
    output_path = data_dir / "powerbi" / "mercadona_product_snapshots.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    export = normalize_column_names(dataframe)
    export = export.drop(columns=["iva", "producto_json"], errors="ignore")

    for column in POWERBI_COLUMNS:
        if column not in export.columns:
            export[column] = None

    export = export[POWERBI_COLUMNS]
    export.to_csv(output_path, index=False, encoding="utf-8")
    return output_path


def write_powerbi_tables(dataframe: pd.DataFrame, *, data_dir: Path) -> list[Path]:
    powerbi_dir = data_dir / "powerbi"
    prices_dir = powerbi_dir / "precios_diarios"
    powerbi_dir.mkdir(parents=True, exist_ok=True)
    prices_dir.mkdir(parents=True, exist_ok=True)

    export = normalize_column_names(dataframe)
    export = export.drop(columns=["iva", "producto_json"], errors="ignore")
    if "fecha_snapshot" in export.columns:
        export["fecha_snapshot"] = pd.to_datetime(export["fecha_snapshot"]).dt.strftime("%Y-%m-%d")

    products = _select_powerbi_columns(export, POWERBI_PRODUCT_COLUMNS + ["fecha_snapshot"])
    products = products.dropna(subset=["id_producto"])
    products = products.sort_values(["id_producto", "fecha_snapshot"], na_position="last")
    products = products.drop_duplicates(subset=["id_producto"], keep="last")
    products = products[POWERBI_PRODUCT_COLUMNS]

    locations = _select_powerbi_columns(export, POWERBI_LOCATION_COLUMNS)
    locations = locations.dropna(subset=["id_ubicacion"])
    locations = locations.drop_duplicates(subset=["id_ubicacion"], keep="last")
    locations = locations.sort_values("id_ubicacion")

    prices = _select_powerbi_columns(export, POWERBI_DAILY_PRICE_COLUMNS)
    prices = prices.dropna(subset=["fecha_snapshot", "id_ubicacion", "id_producto"])
    prices = prices.drop_duplicates(
        subset=["fecha_snapshot", "id_ubicacion", "id_producto"],
        keep="last",
    )
    prices = prices.sort_values(["fecha_snapshot", "id_ubicacion", "id_producto"])

    output_paths = [
        powerbi_dir / "productos.csv",
        powerbi_dir / "ubicaciones.csv",
    ]
    products.to_csv(output_paths[0], index=False, encoding="utf-8")
    locations.to_csv(output_paths[1], index=False, encoding="utf-8")

    written_price_files: list[Path] = []
    for snapshot_date, daily_prices in prices.groupby("fecha_snapshot", dropna=False):
        if pd.isna(snapshot_date):
            continue

        filename = f"fecha_snapshot={snapshot_date}.csv"
        output_path = prices_dir / filename
        daily_prices.to_csv(output_path, index=False, encoding="utf-8")
        written_price_files.append(output_path)

    return output_paths + written_price_files


def _select_powerbi_columns(dataframe: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    selected = dataframe.copy()
    for column in columns:
        if column not in selected.columns:
            selected[column] = None

    return selected[columns]


def normalize_column_names(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe = dataframe.rename(columns=SPANISH_COLUMN_NAMES)

    if dataframe.columns.duplicated().any():
        deduped = pd.DataFrame(index=dataframe.index)
        for column in dict.fromkeys(dataframe.columns):
            same_name_columns = dataframe.loc[:, dataframe.columns == column]
            if same_name_columns.shape[1] == 1:
                deduped[column] = same_name_columns.iloc[:, 0]
            else:
                deduped[column] = same_name_columns.bfill(axis=1).iloc[:, 0]
        dataframe = deduped

    return dataframe
