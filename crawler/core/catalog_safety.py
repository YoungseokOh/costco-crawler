"""Catalog safety checks used before crawler data can be published."""

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
) -> CatalogSafetyAssessment:
    """Block suspicious shrinkage or disagreement inside the upstream source.

    ``saleSummary.product_cnt`` is allowed to differ slightly from the actual
    ``productList`` response. Large disagreements are treated as an incomplete
    upstream snapshot and must never be published automatically.
    """

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
