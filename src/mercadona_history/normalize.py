from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime
from typing import Any


def flatten_categories(categories_payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for section in categories_payload.get("results", []):
        section_id = section.get("id")
        section_name = section.get("name")
        for category in section.get("categories", []):
            rows.append(
                {
                    "section_id": section_id,
                    "section_name": section_name,
                    "category_id": category.get("id"),
                    "category_name": category.get("name"),
                    "category_order": category.get("order"),
                    "category_published": category.get("published"),
                }
            )
    return rows


def extract_products_from_category(category_payload: dict[str, Any]) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    seen: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            product_id = value.get("id")
            if _looks_like_product(value) and product_id is not None:
                product_key = str(product_id)
                if product_key not in seen:
                    seen.add(product_key)
                    products.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(category_payload)
    return products


def product_snapshot_row(
    product: dict[str, Any],
    *,
    snapshot_date: date,
    extraction_timestamp: datetime,
    location_id: str,
    province: str,
    postal_code: str,
    warehouse_code: str | None,
    category_id: int | None,
    category_name: str | None,
    section_id: int | None,
    section_name: str | None,
) -> dict[str, Any]:
    price = product.get("price_instructions") or {}
    return {
        "snapshot_date": snapshot_date.isoformat(),
        "extraction_timestamp": extraction_timestamp.astimezone(UTC).isoformat(),
        "location_id": location_id,
        "province": province,
        "postal_code": postal_code,
        "warehouse_code": warehouse_code,
        "section_id": section_id,
        "section_name": section_name,
        "category_id": category_id,
        "category_name": category_name,
        "product_id": str(product.get("id")),
        "product_name": product.get("display_name") or product.get("name"),
        "slug": product.get("slug"),
        "brand": product.get("brand"),
        "packaging": product.get("packaging"),
        "thumbnail": _nested(product, ["thumbnail"]),
        "share_url": product.get("share_url"),
        "price": _to_float(price.get("unit_price")),
        "unit_price": _to_float(price.get("bulk_price")),
        "unit_size": price.get("unit_size"),
        "size_format": price.get("size_format"),
        "iva": price.get("iva"),
        "is_new": product.get("is_new"),
        "is_available": product.get("published", True),
        "raw_product": product,
    }


def unique_product_ids(products: Iterable[dict[str, Any]]) -> list[str]:
    return sorted({str(product["id"]) for product in products if product.get("id") is not None})


def _looks_like_product(value: dict[str, Any]) -> bool:
    return "price_instructions" in value and ("display_name" in value or "name" in value)


def _nested(value: dict[str, Any], keys: list[str]) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

