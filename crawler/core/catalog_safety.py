"""Catalog safety checks used before crawler data can be published."""

from collections import Counter
from datetime import date, datetime
from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Tuple


@dataclass(frozen=True)
class CatalogSafetyAssessment:
    """Result of comparing a live catalog with the last published snapshot."""

    blocked: bool
    reasons: Tuple[str, ...]
    total_drop_ratio: Optional[float]
    category_drop_ratios: Dict[str, float]
    source_count_drifts: Dict[str, int]


def expired_removal_counts(previous_products, current_product_ids, *, today: date) -> Dict[str, int]:
    """Only missing rows with a proven past end date explain a natural drop.

    The end date is inclusive. Unknown dates remain in the protected baseline.
    """
    live_ids = {str(product_id) for product_id in current_product_ids}
    counts = Counter()
    seen = set()
    for product in previous_products:
        product_id = product.get("product_id")
        category_id = product.get("category_id")
        if product_id is None or category_id is None:
            continue
        key = str(product_id)
        if key in live_ids or key in seen:
            continue
        seen.add(key)
        try:
            end = datetime.strptime(product.get("to_date", ""), "%Y.%m.%d").date()
        except (TypeError, ValueError):
            continue
        if end < today:
            counts[str(category_id)] += 1
    return dict(counts)


def _drop_ratio(previous: int, current: int) -> float:
    if previous <= 0 or current >= previous:
        return 0.0
    return (previous - current) / previous


def assess_catalog_safety(
    *,
    previous_total: Optional[int],
    current_total: int,
    previous_category_counts: Mapping[str, int],
    current_category_counts: Mapping[str, int],
    reported_category_counts: Mapping[str, int],
    max_total_drop_ratio: float,
    max_category_drop_ratio: float,
    min_category_baseline: int,
    max_source_count_drift: int,
    expired_category_counts: Optional[Mapping[str, int]] = None,
) -> CatalogSafetyAssessment:
    """Block suspicious shrinkage or disagreement inside the upstream source.

    ``saleSummary.product_cnt`` is allowed to differ slightly from the actual
    ``productList`` response. Large disagreements are treated as an incomplete
    upstream snapshot and must never be published automatically.
    """

    expired_counts = expired_category_counts or {}
    if previous_total is not None:
        previous_total = max(0, previous_total - sum(expired_counts.values()))

    reasons = []
    total_drop_ratio: Optional[float] = None
    if previous_total is not None and previous_total > 0:
        total_drop_ratio = _drop_ratio(previous_total, current_total)
        if total_drop_ratio >= max_total_drop_ratio:
            reasons.append(
                f"total_catalog_drop:{previous_total}->{current_total}({total_drop_ratio:.3f})"
            )

    category_drop_ratios: Dict[str, float] = {}
    for category_id, previous_count in previous_category_counts.items():
        if previous_count < min_category_baseline:
            continue
        previous_count = max(0, previous_count - expired_counts.get(category_id, 0))
        current_count = int(current_category_counts.get(category_id, 0))
        ratio = _drop_ratio(previous_count, current_count)
        if ratio >= max_category_drop_ratio:
            category_drop_ratios[category_id] = ratio
            reasons.append(
                "category_catalog_drop:"
                f"{category_id}:{previous_count}->{current_count}({ratio:.3f})"
            )

    source_count_drifts: Dict[str, int] = {}
    for category_id, reported_count in reported_category_counts.items():
        actual_count = int(current_category_counts.get(category_id, 0))
        drift = actual_count - reported_count
        if abs(drift) > max_source_count_drift:
            source_count_drifts[category_id] = drift
            reasons.append(
                "upstream_count_mismatch:"
                f"{category_id}:reported={reported_count},actual={actual_count}"
            )

    return CatalogSafetyAssessment(
        blocked=bool(reasons),
        reasons=tuple(reasons),
        total_drop_ratio=total_drop_ratio,
        category_drop_ratios=category_drop_ratios,
        source_count_drifts=source_count_drifts,
    )
