#!/usr/bin/env python3
"""Fail unless data/current exactly matches the live Cocodalin product lists."""

import argparse
import json
from pathlib import Path

from crawler.core.config import config
from crawler.core.fetcher import Fetcher
from crawler.core.source_parity import compare_source_parity


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--products",
        type=Path,
        default=Path("data/current/products.json"),
        help="Saved products JSON to compare",
    )
    parser.add_argument(
        "--allow-source-count-drift",
        action="store_true",
        help="Accept saleSummary count drift after direct Cocodalin verification",
    )
    args = parser.parse_args()

    local_products = json.loads(args.products.read_text(encoding="utf-8"))
    fetcher = Fetcher()
    categories = fetcher._request("categories")
    if categories is None:
        print("[ERROR] Cocodalin saleSummary is unavailable")
        return 2

    source_products_by_category = {}
    category_names = {}
    for category in categories:
        category_id = category.get("category_id")
        if category_id is None:
            continue
        products = fetcher._request("products_by_category", category_id=category_id)
        if products is None:
            print(f"[ERROR] Cocodalin productList/{category_id} is unavailable")
            return 2
        key = str(category_id)
        source_products_by_category[key] = products
        category_names[key] = category.get("category_name", key)

    report = compare_source_parity(
        local_products=local_products,
        source_categories=categories,
        source_products_by_category=source_products_by_category,
        max_source_count_drift=int(config.get("catalog_safety.max_source_count_drift", 2)),
    )

    print("category_id\tcategory_name\treported\tsource_actual\tlocal")
    for category in categories:
        key = str(category.get("category_id"))
        print(
            f"{key}\t{category_names.get(key, key)}\t"
            f"{report.reported_category_counts.get(key, 0)}\t"
            f"{report.source_category_counts.get(key, 0)}\t"
            f"{report.local_category_counts.get(key, 0)}"
        )
    print(f"TOTAL\t-\t-\t{report.source_count}\t{report.local_count}")

    if report.matches:
        print("[PASS] Saved catalog exactly matches Cocodalin product IDs and category counts")
        return 0

    if args.allow_source_count_drift and report.product_lists_match:
        print(
            "[PASS] Saved catalog matches every Cocodalin productList; "
            "saleSummary count drift was explicitly accepted"
        )
        if report.source_count_drifts:
            print(f"       Accepted upstream count drift: {report.source_count_drifts}")
        return 0

    print("[FAIL] Saved catalog does not match Cocodalin")
    if report.missing_product_ids:
        print(f"       Missing IDs: {sorted(report.missing_product_ids)}")
    if report.extra_product_ids:
        print(f"       Extra IDs: {sorted(report.extra_product_ids)}")
    if report.source_count_drifts:
        print(f"       Upstream count drift: {report.source_count_drifts}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
