import json

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


def test_catalog_revision_ignores_generated_image_and_history_fields():
    before = [
        {
            "product_id": 1,
            "product_name": "One",
            "sale_price": 1000,
            "image_status": "pending",
            "discount_count": 2,
        }
    ]
    after = [
        {
            "product_id": 1,
            "product_name": "One",
            "sale_price": 1000,
            "image_status": "cached",
            "image_hash": "abc",
            "discount_count": 3,
        }
    ]

    assert VersionManager.get_catalog_revision(before) == VersionManager.get_catalog_revision(
        after
    )


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
    assert manifest["storage_version"] == "2026-08-03"
    assert manifest["catalog_revision"].startswith("sha256:")
    assert manifest["data_revision"].startswith("sha256:")
    assert manifest["checksum"]["products"] == manifest["data_revision"]


def test_changed_same_week_catalog_gets_immutable_revision_directory(tmp_path):
    manager = VersionManager()
    manager.versions_dir = tmp_path / "versions"
    manager.versions_dir.mkdir()

    base_dir = manager.versions_dir / "2026-08-17"
    base_dir.mkdir()
    (base_dir / "products.json").write_text("[]", encoding="utf-8")
    (base_dir / "manifest.json").write_text(
        json.dumps({"catalog_revision": "sha256:old"}),
        encoding="utf-8",
    )

    storage_version = manager.get_storage_version_name(
        "2026-08-17",
        "sha256:1234567890abcdef",
    )

    assert storage_version == "2026-08-17--1234567890ab"
    assert (base_dir / "manifest.json").read_text(encoding="utf-8") == json.dumps(
        {"catalog_revision": "sha256:old"}
    )


def test_same_revision_reuses_existing_snapshot_directory(tmp_path):
    manager = VersionManager()
    manager.versions_dir = tmp_path / "versions"
    manager.versions_dir.mkdir()

    base_dir = manager.versions_dir / "2026-08-17"
    base_dir.mkdir()
    revision = "sha256:unchanged"
    (base_dir / "products.json").write_text("[]", encoding="utf-8")
    (base_dir / "manifest.json").write_text(
        json.dumps({"catalog_revision": revision}),
        encoding="utf-8",
    )

    assert manager.get_storage_version_name("2026-08-17", revision) == "2026-08-17"


def test_enrich_products_does_not_increment_existing_sale_version():
    manager = VersionManager()
    products = [{"product_id": 1}]
    history = {
        "1": {
            "first_seen": "2026-08-10",
            "occurrences": [
                {"version": "2026-08-10"},
                {"version": "2026-08-17"},
            ],
        }
    }

    enriched = manager.enrich_products(products, history, "2026-08-17")

    assert enriched[0]["discount_count"] == 2
