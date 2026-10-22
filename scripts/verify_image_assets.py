#!/usr/bin/env python3
"""Reject incomplete image snapshots before publishing or dispatching deployment."""

import json
import sys
from pathlib import Path


def image_errors(data_dir: Path) -> list[str]:
    root = data_dir.resolve()
    products = json.loads((root / "products.json").read_text(encoding="utf-8"))
    errors = []
    for product in products:
        product_id = product.get("product_id")
        local_path = product.get("local_image_path")
        if not isinstance(local_path, str) or not local_path.strip():
            errors.append(f"product {product_id}: missing local_image_path")
            continue
        asset = (root / local_path).resolve()
        if root not in asset.parents or not asset.is_file() or asset.stat().st_size == 0:
            errors.append(
                f"product {product_id}: missing or invalid asset {local_path} "
                f"(image_status={product.get('image_status')})"
            )
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "data/current"
    errors = image_errors(data_dir)
    if errors:
        print(f"[image-assets] ERROR: {len(errors)} incomplete image references", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1
    print("[image-assets] PASS: all product images exist")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
