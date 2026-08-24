"""Pure comparison between a saved catalog and Cocodalin API responses."""

from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Set


@dataclass(frozen=True)
class SourceParityReport:
    matches: bool
    product_lists_match: bool
    local_count: int
    source_count: int
    local_category_counts: Dict[str, int]
    source_category_counts: Dict[str, int]
    reported_category_counts: Dict[str, int]
    missing_product_ids: Set[int]
    extra_product_ids: Set[int]
    source_count_drifts: Dict[str, int]


def _product_ids(products: Iterable[dict]) -> Set[int]:
    return {
        int(product["product_id"]) for product in products if product.get("product_id") is not None
    }


def compare_source_parity(
    *,
    local_products: List[dict],
    source_categories: List[dict],
    source_products_by_category: Mapping[str, List[dict]],
    max_source_count_drift: int = 2,
) -> SourceParityReport:
    """Compare exact product IDs and per-category counts with Cocodalin."""

    local_ids = _product_ids(local_products)
    source_products = [
        product for products in source_products_by_category.values() for product in products
    ]
    source_ids = _product_ids(source_products)

    local_category_counts = dict(
        Counter(
            str(product["category_id"])
            for product in local_products
            if product.get("category_id") is not None
        )
    )
    source_category_counts = {
        str(category_id): len(products)
        for category_id, products in source_products_by_category.items()
    }
    reported_category_counts = {}
    for category in source_categories:
        category_id = category.get("category_id")
        if category_id is None:
            continue
        reported_category_counts[str(category_id)] = int(category.get("product_cnt") or 0)

    source_count_drifts = {
        category_id: source_category_counts.get(category_id, 0) - reported_count
        for category_id, reported_count in reported_category_counts.items()
        if abs(source_category_counts.get(category_id, 0) - reported_count) > max_source_count_drift
    }
    missing_product_ids = source_ids - local_ids
    extra_product_ids = local_ids - source_ids
    category_counts_match = local_category_counts == source_category_counts
    product_lists_match = (
        not missing_product_ids and not extra_product_ids and category_counts_match
    )

    return SourceParityReport(
        matches=product_lists_match and not source_count_drifts,
        product_lists_match=product_lists_match,
        local_count=len(local_ids),
        source_count=len(source_ids),
        local_category_counts=local_category_counts,
        source_category_counts=source_category_counts,
        reported_category_counts=reported_category_counts,
        missing_product_ids=missing_product_ids,
        extra_product_ids=extra_product_ids,
        source_count_drifts=source_count_drifts,
    )
