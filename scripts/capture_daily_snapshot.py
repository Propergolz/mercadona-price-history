from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))


def main() -> None:
    args = parse_args()

    from mercadona_history.client import MercadonaClient
    from mercadona_history.config import DEFAULT_LOCATIONS, Location
    from mercadona_history.storage import rebuild_consolidated_parquet

    snapshot_date = date.fromisoformat(args.snapshot_date) if args.snapshot_date else date.today()
    data_dir = ROOT / "data"
    client = MercadonaClient(delay_seconds=args.delay_seconds)

    locations = DEFAULT_LOCATIONS
    if args.postal_code:
        locations = [
            Location(
                location_id=args.location_id or f"custom_{args.postal_code}",
                province=args.province or "Custom",
                postal_code=args.postal_code,
            )
        ]

    total_rows = 0
    for location in locations:
        rows = capture_location(
            client=client,
            location=location,
            snapshot_date=snapshot_date,
            data_dir=data_dir,
            max_categories=args.max_categories,
        )
        total_rows += len(rows)

    consolidated_path = rebuild_consolidated_parquet(data_dir=data_dir)
    print(f"Captured {total_rows} product snapshot rows.")
    if consolidated_path:
        print(f"Consolidated Parquet: {consolidated_path}")


def capture_location(
    *,
    client: MercadonaClient,
    location: Location,
    snapshot_date: date,
    data_dir: Path,
    max_categories: int | None,
) -> list[dict]:
    from mercadona_history.normalize import (
        extract_products_from_category,
        flatten_categories,
        product_snapshot_row,
    )
    from mercadona_history.storage import write_raw_json, write_snapshot_parquet

    extraction_timestamp = datetime.now(UTC)
    warehouse = client.change_postal_code(location.postal_code)
    warehouse_code = warehouse["warehouse_code"]
    print(
        f"Capturing {location.province} ({location.postal_code})"
        f" with warehouse={warehouse_code}"
    )

    categories_payload = client.get_categories(warehouse_code=warehouse_code)
    write_raw_json(
        categories_payload,
        data_dir=data_dir,
        snapshot_date=snapshot_date,
        location_id=location.location_id,
        name="categories",
    )

    categories = flatten_categories(categories_payload)
    if max_categories is not None:
        categories = categories[:max_categories]

    rows: list[dict] = []
    for index, category in enumerate(categories, start=1):
        category_id = category["category_id"]
        print(f"[{index}/{len(categories)}] Category {category_id}: {category['category_name']}")
        category_payload = client.get_category(category_id, warehouse_code=warehouse_code)
        write_raw_json(
            category_payload,
            data_dir=data_dir,
            snapshot_date=snapshot_date,
            location_id=location.location_id,
            name=f"category_{category_id}",
        )

        products = extract_products_from_category(category_payload)
        for product in products:
            rows.append(
                product_snapshot_row(
                    product,
                    snapshot_date=snapshot_date,
                    extraction_timestamp=extraction_timestamp,
                    location_id=location.location_id,
                    province=location.province,
                    postal_code=location.postal_code,
                    warehouse_code=warehouse_code,
                    category_id=category.get("category_id"),
                    category_name=category.get("category_name"),
                    section_id=category.get("section_id"),
                    section_name=category.get("section_name"),
                )
            )

    deduped_rows = dedupe_snapshot_rows(rows)
    output_path = write_snapshot_parquet(
        deduped_rows,
        data_dir=data_dir,
        snapshot_date=snapshot_date,
        location_id=location.location_id,
    )
    print(f"Wrote {len(deduped_rows)} rows to {output_path}")
    return deduped_rows


def dedupe_snapshot_rows(rows: list[dict]) -> list[dict]:
    deduped: dict[tuple[str, str, str], dict] = {}
    for row in rows:
        key = (row["fecha_snapshot"], row["id_ubicacion"], row["id_producto"])
        deduped.setdefault(key, row)
    return list(deduped.values())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture a daily Mercadona price snapshot.")
    parser.add_argument("--snapshot-date", help="Date to store, YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--postal-code", help="Override postal code for an ad hoc capture.")
    parser.add_argument("--province", help="Province name for an ad hoc capture.")
    parser.add_argument("--location-id", help="Stable location id for an ad hoc capture.")
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=0.4,
        help="Polite delay between API calls.",
    )
    parser.add_argument(
        "--max-categories",
        type=int,
        help="Development helper: capture only the first N categories.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
