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
        "fecha_snapshot": snapshot_date.isoformat(),
        "marca_temporal_extraccion": extraction_timestamp.astimezone(UTC).isoformat(),
        "id_ubicacion": location_id,
        "provincia": province,
        "codigo_postal": postal_code,
        "codigo_almacen": warehouse_code,
        "id_seccion": section_id,
        "seccion": section_name,
        "id_categoria": category_id,
        "categoria": category_name,
        "id_producto": str(product.get("id")),
        "producto": product.get("display_name") or product.get("name"),
        "slug": product.get("slug"),
        "marca": product.get("brand"),
        "formato_envase": product.get("packaging"),
        "unidad_venta": build_sales_unit(product),
        "url_imagen": product.get("thumbnail"),
        "url_producto": product.get("share_url"),
        "precio": _to_float(price.get("unit_price")),
        "precio_referencia": _to_float(price.get("bulk_price")),
        "cantidad_unidad": price.get("unit_size"),
        "formato_cantidad": price.get("size_format"),
        "porcentaje_iva": _to_float(price.get("tax_percentage")),
        "es_novedad": product.get("is_new"),
        "disponible": product.get("published", True),
        "producto_json": product,
    }


def build_sales_unit(product: dict[str, Any]) -> str | None:
    price = product.get("price_instructions") or {}
    packaging = product.get("packaging")
    is_pack = price.get("is_pack") is True
    total_units = price.get("total_units")
    pack_size = price.get("pack_size")
    unit_name = price.get("unit_name")
    unit_size = price.get("unit_size")
    size_format = price.get("size_format")

    if is_pack:
        unit_label = unit_name or "ud."
        if total_units and pack_size and size_format:
            return (
                f"{_format_number(total_units)} {unit_label} "
                f"x {_format_number(pack_size)} {size_format}"
            )
        if total_units and unit_label:
            return f"{_format_number(total_units)} {unit_label}"

    if packaging and unit_size and size_format:
        return f"{packaging} {_format_number(unit_size)} {size_format}"
    if unit_size and size_format:
        return f"{_format_number(unit_size)} {size_format}"
    if packaging:
        return str(packaging)
    if total_units and unit_name:
        return f"{_format_number(total_units)} {unit_name}"
    return None


def unique_product_ids(products: Iterable[dict[str, Any]]) -> list[str]:
    return sorted({str(product["id"]) for product in products if product.get("id") is not None})


def _looks_like_product(value: dict[str, Any]) -> bool:
    return "price_instructions" in value and ("display_name" in value or "name" in value)


def _format_number(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)

    if number.is_integer():
        return str(int(number))
    return f"{number:g}".replace(".", ",")


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
