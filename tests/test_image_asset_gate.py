import json

from scripts.verify_image_assets import image_errors


def test_missing_image_reports_product_and_upstream_failure(tmp_path):
    (tmp_path / "products.json").write_text(json.dumps([{
        "product_id": 12133,
        "local_image_path": "images/products/12133.jpg",
        "image_status": "failed:403",
    }]))
    errors = image_errors(tmp_path)
    assert len(errors) == 1
    assert "12133" in errors[0]
    assert "failed:403" in errors[0]


def test_present_asset_passes_and_empty_asset_fails(tmp_path):
    (tmp_path / "products.json").write_text(json.dumps([{
        "product_id": 1, "local_image_path": "1.jpg",
    }]))
    asset = tmp_path / "1.jpg"
    asset.write_bytes(b"image bytes")
    assert image_errors(tmp_path) == []
    asset.write_bytes(b"")
    assert len(image_errors(tmp_path)) == 1


def test_external_symlink_is_rejected(tmp_path):
    root = tmp_path / "snapshot"
    root.mkdir()
    (tmp_path / "outside.jpg").write_bytes(b"image bytes")
    (root / "1.jpg").symlink_to(tmp_path / "outside.jpg")
    (root / "products.json").write_text(json.dumps([{
        "product_id": 1, "local_image_path": "1.jpg",
    }]))
    assert len(image_errors(root)) == 1
