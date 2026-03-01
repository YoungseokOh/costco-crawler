#!/usr/bin/env python3
"""Validate products.json schema for release safety."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_FIELDS: dict[str, type] = {
    "product_id": int,
    "product_name": str,
    "sale_price": int,
}

OPTIONAL_FIELDS: dict[str, tuple[type, ...]] = {
    "category_id": (int, str, type(None)),
    "category_name": (str, type(None)),
    "normal_price": (int, type(None)),
    "discount": (int, type(None)),
    "from_date": (str, type(None)),
    "to_date": (str, type(None)),
    "image_url": (str, type(None)),
    "local_image_path": (str, type(None)),
    "like_cnt": (int, type(None)),
}


def _type_name(tp: object) -> str:
    if isinstance(tp, tuple):
        return " | ".join(t.__name__ for t in tp)
    return tp.__name__


def validate(path: Path) -> int:
    if not path.exists():
        print(f"[schema] ERROR: file not found: {path}")
        return 1

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[schema] ERROR: invalid JSON: {exc}")
        return 1

    if not isinstance(data, list):
        print("[schema] ERROR: root must be an array")
        return 1

    if not data:
        print("[schema] ERROR: products list is empty")
        return 1

    errors: list[str] = []

    for idx, item in enumerate(data):
        row = f"item[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{row}: must be object, got {type(item).__name__}")
            continue

        for key, expected in REQUIRED_FIELDS.items():
            if key not in item:
                errors.append(f"{row}: missing required field `{key}`")
                continue
            if not isinstance(item[key], expected):
                errors.append(
                    f"{row}.{key}: expected {_type_name(expected)}, got {type(item[key]).__name__}"
                )

        for key, expected in OPTIONAL_FIELDS.items():
            if key in item and not isinstance(item[key], expected):
                errors.append(
                    f"{row}.{key}: expected {_type_name(expected)}, got {type(item[key]).__name__}"
                )

        if isinstance(item.get("product_name"), str) and not item["product_name"].strip():
            errors.append(f"{row}.product_name: must not be empty")

        if isinstance(item.get("sale_price"), int) and item["sale_price"] < 0:
            errors.append(f"{row}.sale_price: must be >= 0")

        if isinstance(item.get("normal_price"), int) and item["normal_price"] < 0:
            errors.append(f"{row}.normal_price: must be >= 0")

    if errors:
        print(f"[schema] ERROR: found {len(errors)} issue(s)")
        for msg in errors[:50]:
            print(f" - {msg}")
        if len(errors) > 50:
            print(f" - ... {len(errors) - 50} more")
        return 1

    print(f"[schema] OK: {len(data)} products validated")
    return 0


def main() -> int:
    default_path = Path("data/current/products.json")
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path
    return validate(path)


if __name__ == "__main__":
    raise SystemExit(main())
