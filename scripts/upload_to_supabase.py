from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))


def main() -> None:
    args = parse_args()
    database_url = os.environ.get("SUPABASE_DB_URL")
    if not database_url:
        raise SystemExit("Missing SUPABASE_DB_URL environment variable.")

    import psycopg

    snapshot_date = date.fromisoformat(args.snapshot_date)
    data_dir = ROOT / "data"

    locations = load_locations()
    products = load_products_from_raw(data_dir=data_dir, snapshot_date=snapshot_date)
    prices = load_daily_prices(data_dir=data_dir, snapshot_date=snapshot_date)

    if args.limit_products:
        allowed_products = {row["id_producto"] for row in products[: args.limit_products]}
        products = products[: args.limit_products]
        prices = [row for row in prices if row["id_producto"] in allowed_products]

    with psycopg.connect(database_url) as connection:
        create_schema(connection)
        upsert_locations(connection, locations)
        upsert_products(connection, products)
        upsert_prices(connection, prices)

    print(f"Uploaded locations: {len(locations)}")
    print(f"Uploaded products: {len(products)}")
    print(f"Uploaded daily prices: {len(prices)}")


def load_locations() -> list[dict[str, Any]]:
    from mercadona_history.config import DEFAULT_LOCATIONS

    rows = []
    for location in DEFAULT_LOCATIONS:
        rows.append(
            {
                "id_ubicacion": location.location_id,
                "provincia": location.province,
                "codigo_postal": location.postal_code,
                "codigo_almacen": None,
            }
        )
    return rows


def load_products_from_raw(*, data_dir: Path, snapshot_date: date) -> list[dict[str, Any]]:
    from mercadona_history.normalize import (
        extract_products_from_category,
        flatten_categories,
        product_snapshot_row,
    )

    raw_root = data_dir / "raw" / snapshot_date.isoformat()
    if not raw_root.exists():
        raise FileNotFoundError(f"Raw directory not found: {raw_root}")

    products_by_id: dict[str, dict[str, Any]] = {}
    extraction_timestamp = datetime.now(UTC)

    for location_dir in sorted(path for path in raw_root.iterdir() if path.is_dir()):
        categories_path = location_dir / "categories.json.gz"
        if not categories_path.exists():
            continue

        categories_payload = read_gzip_json(categories_path)
        categories = flatten_categories(categories_payload)
        categories_by_id = {
            str(category["category_id"]): category for category in categories
        }

        for category_path in sorted(location_dir.glob("category_*.json.gz")):
            category_id = category_path.stem.replace("category_", "")
            category = categories_by_id.get(category_id, {})
            category_payload = read_gzip_json(category_path)

            for product in extract_products_from_category(category_payload):
                row = product_snapshot_row(
                    product,
                    snapshot_date=snapshot_date,
                    extraction_timestamp=extraction_timestamp,
                    location_id=location_dir.name,
                    province="",
                    postal_code="",
                    warehouse_code=None,
                    category_id=category.get("category_id"),
                    category_name=category.get("category_name"),
                    section_id=category.get("section_id"),
                    section_name=category.get("section_name"),
                )
                product_id = row["id_producto"]
                products_by_id[product_id] = {
                    "id_producto": product_id,
                    "producto": row.get("producto"),
                    "slug": row.get("slug"),
                    "marca": row.get("marca"),
                    "formato_envase": row.get("formato_envase"),
                    "unidad_venta": row.get("unidad_venta"),
                    "url_imagen": row.get("url_imagen"),
                    "url_producto": row.get("url_producto"),
                    "id_seccion": optional_text(row.get("id_seccion")),
                    "seccion": row.get("seccion"),
                    "id_categoria": optional_text(row.get("id_categoria")),
                    "categoria": row.get("categoria"),
                    "porcentaje_iva": row.get("porcentaje_iva"),
                }

    return sorted(products_by_id.values(), key=lambda row: row["id_producto"])


def load_daily_prices(*, data_dir: Path, snapshot_date: date) -> list[dict[str, Any]]:
    path = (
        data_dir
        / "powerbi"
        / "precios_diarios"
        / f"fecha_snapshot={snapshot_date.isoformat()}.csv"
    )
    if not path.exists():
        raise FileNotFoundError(f"Daily prices file not found: {path}")

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return [
            {
                "fecha_snapshot": row["fecha_snapshot"],
                "marca_temporal_extraccion": empty_to_none(row.get("marca_temporal_extraccion")),
                "id_producto": row["id_producto"],
                "id_ubicacion": row["id_ubicacion"],
                "precio": optional_float(row.get("precio")),
                "precio_referencia": optional_float(row.get("precio_referencia")),
                "cantidad_unidad": optional_float(row.get("cantidad_unidad")),
                "formato_cantidad": empty_to_none(row.get("formato_cantidad")),
                "es_novedad": optional_bool(row.get("es_novedad")),
                "disponible": optional_bool(row.get("disponible")),
            }
            for row in reader
        ]


def create_schema(connection: Any) -> None:
    statements = [
        """
        create table if not exists dim_ubicacion (
            id_ubicacion text primary key,
            provincia text,
            codigo_postal text,
            codigo_almacen text
        )
        """,
        """
        create table if not exists dim_producto (
            id_producto text primary key,
            producto text,
            slug text,
            marca text,
            formato_envase text,
            unidad_venta text,
            url_imagen text,
            url_producto text,
            id_seccion text,
            seccion text,
            id_categoria text,
            categoria text,
            porcentaje_iva numeric
        )
        """,
        """
        create table if not exists fact_precio_diario (
            fecha_snapshot date not null,
            id_producto text not null references dim_producto(id_producto),
            id_ubicacion text not null references dim_ubicacion(id_ubicacion),
            marca_temporal_extraccion timestamptz,
            precio numeric,
            precio_referencia numeric,
            cantidad_unidad numeric,
            formato_cantidad text,
            es_novedad boolean,
            disponible boolean,
            primary key (fecha_snapshot, id_producto, id_ubicacion)
        )
        """,
    ]
    with connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)


def upsert_locations(connection: Any, rows: list[dict[str, Any]]) -> None:
    sql = """
        insert into dim_ubicacion (
            id_ubicacion, provincia, codigo_postal, codigo_almacen
        )
        values (
            %(id_ubicacion)s, %(provincia)s, %(codigo_postal)s, %(codigo_almacen)s
        )
        on conflict (id_ubicacion) do update set
            provincia = excluded.provincia,
            codigo_postal = excluded.codigo_postal,
            codigo_almacen = excluded.codigo_almacen
    """
    with connection.cursor() as cursor:
        cursor.executemany(sql, rows)


def upsert_products(connection: Any, rows: list[dict[str, Any]]) -> None:
    sql = """
        insert into dim_producto (
            id_producto, producto, slug, marca, formato_envase, unidad_venta,
            url_imagen, url_producto, id_seccion, seccion, id_categoria,
            categoria, porcentaje_iva
        )
        values (
            %(id_producto)s, %(producto)s, %(slug)s, %(marca)s,
            %(formato_envase)s, %(unidad_venta)s, %(url_imagen)s,
            %(url_producto)s, %(id_seccion)s, %(seccion)s,
            %(id_categoria)s, %(categoria)s, %(porcentaje_iva)s
        )
        on conflict (id_producto) do update set
            producto = excluded.producto,
            slug = excluded.slug,
            marca = excluded.marca,
            formato_envase = excluded.formato_envase,
            unidad_venta = excluded.unidad_venta,
            url_imagen = excluded.url_imagen,
            url_producto = excluded.url_producto,
            id_seccion = excluded.id_seccion,
            seccion = excluded.seccion,
            id_categoria = excluded.id_categoria,
            categoria = excluded.categoria,
            porcentaje_iva = excluded.porcentaje_iva
    """
    with connection.cursor() as cursor:
        cursor.executemany(sql, rows)


def upsert_prices(connection: Any, rows: list[dict[str, Any]]) -> None:
    sql = """
        insert into fact_precio_diario (
            fecha_snapshot, marca_temporal_extraccion, id_producto, id_ubicacion,
            precio, precio_referencia, cantidad_unidad, formato_cantidad,
            es_novedad, disponible
        )
        values (
            %(fecha_snapshot)s, %(marca_temporal_extraccion)s,
            %(id_producto)s, %(id_ubicacion)s, %(precio)s,
            %(precio_referencia)s, %(cantidad_unidad)s,
            %(formato_cantidad)s, %(es_novedad)s, %(disponible)s
        )
        on conflict (fecha_snapshot, id_producto, id_ubicacion) do update set
            marca_temporal_extraccion = excluded.marca_temporal_extraccion,
            precio = excluded.precio,
            precio_referencia = excluded.precio_referencia,
            cantidad_unidad = excluded.cantidad_unidad,
            formato_cantidad = excluded.formato_cantidad,
            es_novedad = excluded.es_novedad,
            disponible = excluded.disponible
    """
    with connection.cursor() as cursor:
        cursor.executemany(sql, rows)


def read_gzip_json(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as file:
        return json.load(file)


def empty_to_none(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    return value


def optional_bool(value: str | None) -> bool | None:
    if value in (None, ""):
        return None
    return value.lower() == "true"


def optional_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def optional_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload Mercadona snapshots to Supabase.")
    parser.add_argument("--snapshot-date", required=True, help="Date to upload, YYYY-MM-DD.")
    parser.add_argument(
        "--limit-products",
        type=int,
        help="Demo helper: upload only the first N products and their prices.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
