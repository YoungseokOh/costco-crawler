from crawler.core.catalog_safety import assess_catalog_safety


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
