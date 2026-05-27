from __future__ import annotations

import gzip
import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


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
    dataframe["raw_product"] = dataframe["raw_product"].apply(
        lambda value: json.dumps(value, ensure_ascii=False)
    )
    dataframe.to_parquet(path, index=False)
    return path


def rebuild_consolidated_parquet(*, data_dir: Path) -> Path | None:
    snapshot_root = data_dir / "parquet" / "snapshots"
    files = sorted(snapshot_root.glob("snapshot_date=*/*.parquet"))
    if not files:
        return None

    frames = [pd.read_parquet(path) for path in files]
    consolidated = pd.concat(frames, ignore_index=True)
    consolidated = consolidated.drop_duplicates(
        subset=["snapshot_date", "location_id", "product_id"],
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

    export = dataframe.drop(columns=["raw_product"], errors="ignore")
    export.to_csv(output_path, index=False, encoding="utf-8")
    return output_path
