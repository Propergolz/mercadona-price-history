from __future__ import annotations

import gzip
import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


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

    frames = [normalize_column_names(pd.read_parquet(path)) for path in files]
    consolidated = pd.concat(frames, ignore_index=True)
    consolidated = consolidated.drop_duplicates(
        subset=["fecha_snapshot", "id_ubicacion", "id_producto"],
        keep="last",
    )

    output_path = data_dir / "parquet" / "mercadona_product_snapshots.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    consolidated.to_parquet(output_path, index=False)
    write_powerbi_csv(consolidated, data_dir=data_dir)
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


def normalize_column_names(dataframe: pd.DataFrame) -> pd.DataFrame:
    return dataframe.rename(columns=SPANISH_COLUMN_NAMES)
