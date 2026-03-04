import hashlib
import json
from typing import Any, Dict, List

from crawler.core.fetcher import Fetcher


def _notice_hash(notices: List[Dict[str, Any]]) -> str:
    payload = json.dumps(notices, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.md5(payload.encode()).hexdigest()


def _catalog_hash(products: List[Dict[str, Any]]) -> str:
    normalized = []
    for product in products:
        normalized.append(
            {
                "product_id": product["product_id"],
                "sale_price": product.get("sale_price"),
                "normal_price": product.get("normal_price"),
                "discount": product.get("discount"),
                "from_date": product.get("from_date"),
                "to_date": product.get("to_date"),
            }
        )
    normalized.sort(key=lambda item: item["product_id"])
    payload = json.dumps(normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _build_fetcher(monkeypatch, crawl_log: Dict[str, Any]) -> Fetcher:
    monkeypatch.setattr(Fetcher, "_load_crawl_log", lambda self: crawl_log, raising=False)
    return Fetcher()


def _set_request_stub(
    monkeypatch,
    fetcher: Fetcher,
    notices: Any,
    categories: Any,
    products_by_category: Dict[int, Any],
):
    def fake_request(endpoint_key: str, **kwargs):
        if endpoint_key == "notice":
            return notices
        if endpoint_key == "categories":
            return categories
        if endpoint_key == "products_by_category":
            return products_by_category.get(kwargs["category_id"])
        raise AssertionError(f"Unexpected endpoint key: {endpoint_key}")

    monkeypatch.setattr(fetcher, "_request", fake_request)


def test_check_update_false_when_notice_and_catalog_unchanged(monkeypatch):
    notices = [{"id": 1, "notice_title": "3월 1주차"}]
    categories = [{"category_id": 10, "category_name": "A"}]
    products = [
        {
            "product_id": 1,
            "sale_price": 1000,
            "normal_price": 1200,
            "discount": 200,
            "from_date": "2026.03.02",
            "to_date": "2026.03.08",
        },
        {
            "product_id": 2,
            "sale_price": 5000,
            "normal_price": 5900,
            "discount": 900,
            "from_date": "2026.03.02",
            "to_date": "2026.03.08",
        },
    ]
    crawl_log = {
        "last_notice_hash": _notice_hash(notices),
        "last_catalog_hash": _catalog_hash(products),
    }
    fetcher = _build_fetcher(monkeypatch, crawl_log)
    _set_request_stub(monkeypatch, fetcher, notices, categories, {10: products})

    has_update, notice_hash = fetcher.check_update()
    assert has_update is False
    assert notice_hash == crawl_log["last_notice_hash"]
    assert fetcher.last_check_result["reason"] == "notice_unchanged_catalog_unchanged"
    assert fetcher.last_check_result["catalog_count"] == 2


def test_check_update_true_when_notice_unchanged_but_catalog_changed(monkeypatch):
    notices = [{"id": 1, "notice_title": "3월 1주차"}]
    categories = [{"category_id": 10, "category_name": "A"}]
    old_products = [
        {
            "product_id": 1,
            "sale_price": 1000,
            "normal_price": 1200,
            "discount": 200,
            "from_date": "2026.03.02",
            "to_date": "2026.03.08",
        }
    ]
    new_products = [
        {
            "product_id": 1,
            "sale_price": 900,
            "normal_price": 1200,
            "discount": 300,
            "from_date": "2026.03.02",
            "to_date": "2026.03.08",
        }
    ]
    crawl_log = {
        "last_notice_hash": _notice_hash(notices),
        "last_catalog_hash": _catalog_hash(old_products),
    }
    fetcher = _build_fetcher(monkeypatch, crawl_log)
    _set_request_stub(monkeypatch, fetcher, notices, categories, {10: new_products})

    has_update, _ = fetcher.check_update()
    assert has_update is True
    assert fetcher.last_check_result["reason"] == "catalog_changed"
    assert fetcher.last_check_result["notice_changed"] is False
    assert fetcher.last_check_result["catalog_changed"] is True


def test_check_update_true_when_notice_changed(monkeypatch):
    old_notices = [{"id": 1, "notice_title": "2월 4주차"}]
    new_notices = [{"id": 1, "notice_title": "3월 1주차"}]
    categories = [{"category_id": 10, "category_name": "A"}]
    products = [
        {
            "product_id": 1,
            "sale_price": 1000,
            "normal_price": 1200,
            "discount": 200,
            "from_date": "2026.03.02",
            "to_date": "2026.03.08",
        }
    ]
    crawl_log = {
        "last_notice_hash": _notice_hash(old_notices),
        "last_catalog_hash": _catalog_hash(products),
    }
    fetcher = _build_fetcher(monkeypatch, crawl_log)
    _set_request_stub(monkeypatch, fetcher, new_notices, categories, {10: products})

    has_update, _ = fetcher.check_update()
    assert has_update is True
    assert fetcher.last_check_result["reason"] == "notice_changed"
    assert fetcher.last_check_result["notice_changed"] is True
    assert fetcher.last_check_result["catalog_changed"] is False


def test_check_update_bootstraps_when_catalog_hash_missing(monkeypatch):
    notices = [{"id": 1, "notice_title": "3월 1주차"}]
    categories = [{"category_id": 10, "category_name": "A"}]
    products = [
        {
            "product_id": 1,
            "sale_price": 1000,
            "normal_price": 1200,
            "discount": 200,
            "from_date": "2026.03.02",
            "to_date": "2026.03.08",
        }
    ]
    crawl_log = {
        "last_notice_hash": _notice_hash(notices),
    }
    fetcher = _build_fetcher(monkeypatch, crawl_log)
    _set_request_stub(monkeypatch, fetcher, notices, categories, {10: products})

    has_update, _ = fetcher.check_update()
    assert has_update is True
    assert fetcher.last_check_result["reason"] == "catalog_changed"
    assert fetcher.last_check_result["catalog_changed"] is True


def test_check_update_falls_back_when_catalog_unavailable(monkeypatch):
    notices = [{"id": 1, "notice_title": "3월 1주차"}]
    crawl_log = {
        "last_notice_hash": _notice_hash(notices),
        "last_catalog_hash": "anything",
    }
    fetcher = _build_fetcher(monkeypatch, crawl_log)
    _set_request_stub(monkeypatch, fetcher, notices, None, {})

    has_update, _ = fetcher.check_update()
    assert has_update is False
    assert fetcher.last_check_result["reason"] == "notice_unchanged_catalog_unavailable"


def test_check_update_false_when_notice_unavailable(monkeypatch):
    fetcher = _build_fetcher(monkeypatch, {})
    _set_request_stub(monkeypatch, fetcher, None, [], {})

    has_update, notice_hash = fetcher.check_update()
    assert has_update is False
    assert notice_hash is None
    assert fetcher.last_check_result["reason"] == "notice_unavailable"


def test_check_update_records_catalog_count_change_ratio(monkeypatch):
    notices = [{"id": 1, "notice_title": "3월 1주차"}]
    categories = [{"category_id": 10, "category_name": "A"}]
    old_products = [
        {
            "product_id": 1,
            "sale_price": 1000,
            "normal_price": 1200,
            "discount": 200,
            "from_date": "2026.03.02",
            "to_date": "2026.03.08",
        }
    ]
    new_products = [
        {
            "product_id": 1,
            "sale_price": 1000,
            "normal_price": 1200,
            "discount": 200,
            "from_date": "2026.03.02",
            "to_date": "2026.03.08",
        },
        {
            "product_id": 2,
            "sale_price": 5000,
            "normal_price": 5900,
            "discount": 900,
            "from_date": "2026.03.02",
            "to_date": "2026.03.08",
        },
    ]
    crawl_log = {
        "last_notice_hash": _notice_hash(notices),
        "last_catalog_hash": _catalog_hash(old_products),
        "last_catalog_count": 1,
    }
    fetcher = _build_fetcher(monkeypatch, crawl_log)
    _set_request_stub(monkeypatch, fetcher, notices, categories, {10: new_products})

    has_update, _ = fetcher.check_update()
    assert has_update is True
    assert fetcher.last_check_result["catalog_count_change_ratio"] == 1.0
