from crawler.core.version_manager import VersionManager


def test_data_revision_is_stable_when_product_order_changes():
    products = [
        {"product_id": 2, "product_name": "Two", "sale_price": 2000},
        {"product_id": 1, "product_name": "One", "sale_price": 1000},
    ]

    assert VersionManager.get_data_revision(products) == VersionManager.get_data_revision(
        list(reversed(products))
    )


def test_data_revision_changes_when_product_content_changes():
    before = [{"product_id": 1, "product_name": "One", "sale_price": 1000}]
    after = [{"product_id": 1, "product_name": "One", "sale_price": 900}]

    assert VersionManager.get_data_revision(before) != VersionManager.get_data_revision(after)


def test_manifest_keeps_sale_version_separate_from_data_revision(monkeypatch):
    manager = VersionManager()
    monkeypatch.setattr(manager, "list_versions", lambda: [])
    products = [{"product_id": 1, "product_name": "One", "sale_price": 1000}]

    manifest = manager.create_manifest(
        version="2026-08-03",
        products=products,
        categories=[],
        categorized={"new": {1}, "returning": set(), "continuing": set()},
    )

    assert manifest["version"] == "2026-08-03"
    assert manifest["data_revision"].startswith("sha256:")
    assert manifest["checksum"]["products"] == manifest["data_revision"]
