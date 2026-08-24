from crawler.core.source_parity import compare_source_parity


def test_source_parity_matches_exact_product_ids_and_category_counts():
    local_products = [
        {"product_id": 1, "category_id": 7},
        {"product_id": 2, "category_id": 7},
        {"product_id": 3, "category_id": 9},
    ]
    categories = [
        {"category_id": 7, "product_cnt": 2},
        {"category_id": 9, "product_cnt": 4},
    ]
    source_products = {
        "7": local_products[:2],
        "9": local_products[2:],
    }

    report = compare_source_parity(
        local_products=local_products,
        source_categories=categories,
        source_products_by_category=source_products,
        max_source_count_drift=3,
    )

    assert report.matches is True
    assert report.local_count == report.source_count == 3


def test_source_parity_fails_when_saved_catalog_has_extra_product():
    report = compare_source_parity(
        local_products=[
            {"product_id": 1, "category_id": 7},
            {"product_id": 2, "category_id": 7},
        ],
        source_categories=[{"category_id": 7, "product_cnt": 1}],
        source_products_by_category={"7": [{"product_id": 1, "category_id": 7}]},
    )

    assert report.matches is False
    assert report.product_lists_match is False
    assert report.extra_product_ids == {2}


def test_source_parity_distinguishes_summary_drift_from_product_list_mismatch():
    products = [{"product_id": 1, "category_id": 10}]

    report = compare_source_parity(
        local_products=products,
        source_categories=[{"category_id": 10, "product_cnt": 4}],
        source_products_by_category={"10": products},
        max_source_count_drift=2,
    )

    assert report.matches is False
    assert report.product_lists_match is True
    assert report.source_count_drifts == {"10": -3}
