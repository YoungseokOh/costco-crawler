import json
from pathlib import Path

import pytest

from crawler.transform.config import estimate_edit_cost_usd
from crawler.transform.index import TransformIndex, TransformRecord
from crawler.transform.smoke import collect_candidates, select_candidates


def test_collect_candidates_dedupes_hash_and_skips_ineligible_rows(tmp_path: Path):
    snapshot_dir = tmp_path / "snapshot"
    images_dir = snapshot_dir / "images" / "products"
    images_dir.mkdir(parents=True)

    (images_dir / "1.jpg").write_bytes(b"one")
    (images_dir / "2.jpg").write_bytes(b"two")
    (images_dir / "4.jpg").write_bytes(b"four")

    products = [
        {
            "product_id": 1,
            "product_name": "One",
            "local_image_path": "images/products/1.jpg",
            "image_hash": "hash-a",
            "image_status": "downloaded",
        },
        {
            "product_id": 2,
            "product_name": "Two",
            "local_image_path": "images/products/2.jpg",
            "image_hash": "hash-a",
            "image_status": "cached",
        },
        {
            "product_id": 3,
            "product_name": "Missing",
            "local_image_path": "images/products/3.jpg",
            "image_hash": "hash-b",
            "image_status": "downloaded",
        },
        {
            "product_id": 4,
            "product_name": "Four",
            "local_image_path": "images/products/4.jpg",
            "image_hash": "hash-c",
            "image_status": "cached",
        },
        {
            "product_id": 5,
            "product_name": "Failed",
            "local_image_path": "images/products/5.jpg",
            "image_hash": "hash-d",
            "image_status": "failed:404",
        },
    ]

    products_path = snapshot_dir / "products.json"
    products_path.write_text(json.dumps(products, ensure_ascii=False), encoding="utf-8")

    candidates = collect_candidates(products_path)

    assert [candidate.product_id for candidate in candidates] == [1, 4]
    assert [candidate.image_hash for candidate in candidates] == ["hash-a", "hash-c"]


def test_select_candidates_is_deterministic_for_seed(tmp_path: Path):
    snapshot_dir = tmp_path / "2026-03-16"
    images_dir = snapshot_dir / "images" / "products"
    images_dir.mkdir(parents=True)

    products = []
    for idx in range(1, 6):
        image_path = images_dir / f"{idx}.jpg"
        image_path.write_bytes(f"image-{idx}".encode())
        products.append(
            {
                "product_id": idx,
                "product_name": f"Product {idx}",
                "local_image_path": f"images/products/{idx}.jpg",
                "image_hash": f"hash-{idx}",
                "image_status": "downloaded",
            }
        )

    products_path = snapshot_dir / "products.json"
    products_path.write_text(json.dumps(products, ensure_ascii=False), encoding="utf-8")

    candidates = collect_candidates(products_path)
    first = select_candidates(candidates, count=3, seed="seed-123")
    second = select_candidates(candidates, count=3, seed="seed-123")

    assert first == second
    assert len(first) == 3


def test_estimate_edit_cost_uses_current_image_pricing():
    assert estimate_edit_cost_usd(1) == pytest.approx(0.022)
    assert estimate_edit_cost_usd(3) == pytest.approx(0.066)


def test_transform_index_round_trip(tmp_path: Path):
    index_path = tmp_path / "image_transform_index.json"
    index = TransformIndex(index_path)

    records = {
        "hash-a": TransformRecord(
            source_hash="hash-a",
            provider="xai",
            model="grok-imagine-image",
            prompt_version="angle-smoke-v1",
            status="success",
            transformed_master_path="images/transformed/hash-a.png",
            created_at="2026-03-18T00:00:00+00:00",
        )
    }

    index.save(records)
    loaded = index.load()

    assert loaded == records
