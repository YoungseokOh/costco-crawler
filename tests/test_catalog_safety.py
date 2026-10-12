from datetime import date

import pytest

from crawler.core.catalog_safety import assess_catalog_safety, expired_removal_counts


def test_category_collapse_is_blocked_even_when_total_count_is_stable():
    assessment = assess_catalog_safety(
        previous_total=40,
        current_total=40,
        previous_category_counts={"7": 20, "9": 20},
        current_category_counts={"7": 5, "9": 35},
        reported_category_counts={"7": 5, "9": 35},
        max_total_drop_ratio=0.20,
        max_category_drop_ratio=0.50,
        min_category_baseline=10,
        max_source_count_drift=2,
    )

    assert assessment.blocked is True
    assert assessment.total_drop_ratio == 0.0
    assert assessment.category_drop_ratios == {"7": 0.75}


def test_small_upstream_count_drift_is_allowed():
    assessment = assess_catalog_safety(
        previous_total=193,
        current_total=193,
        previous_category_counts={"10": 31},
        current_category_counts={"10": 31},
        reported_category_counts={"10": 32},
        max_total_drop_ratio=0.20,
        max_category_drop_ratio=0.50,
        min_category_baseline=10,
        max_source_count_drift=2,
    )

    assert assessment.blocked is False
    assert assessment.source_count_drifts == {}


@pytest.mark.parametrize("end,expected", [
    ("2026.10.11", {"7": 1}), ("2026.10.12", {}),
    ("2026.10.13", {}), (None, {}), ("invalid", {}),
])
def test_only_missing_products_expired_before_today_are_exempt(end, expected):
    previous = [{"product_id": 1, "category_id": 7, "to_date": end}]
    assert expired_removal_counts(previous, [], today=date(2026, 10, 12)) == expected
    assert expired_removal_counts(previous, [1], today=date(2026, 10, 12)) == {}


@pytest.mark.parametrize("current,reported,blocked", [(216, 216, False), (100, 100, True), (216, 230, True)])
def test_expiration_exemption_keeps_unexplained_drop_and_source_drift_protected(current, reported, blocked):
    assessment = assess_catalog_safety(
        previous_total=479, current_total=current,
        previous_category_counts={"7": 479}, current_category_counts={"7": current},
        reported_category_counts={"7": reported}, expired_category_counts={"7": 263},
        max_total_drop_ratio=0.20, max_category_drop_ratio=0.50,
        min_category_baseline=10, max_source_count_drift=2,
    )
    assert assessment.blocked is blocked
