"""Candidate discovery and selection for smoke-test runs."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ELIGIBLE_IMAGE_STATUSES = {"downloaded", "cached"}


@dataclass(frozen=True)
class TransformCandidate:
    """Representative product selected for a distinct source image hash."""

    product_id: int
    product_name: str
    image_hash: str
    image_status: str
    local_image_path: str
    absolute_image_path: Path
    version: str


def collect_candidates(products_path: Path) -> list[TransformCandidate]:
    """Collect one representative candidate per distinct image hash."""
    products = json.loads(products_path.read_text(encoding="utf-8"))
    snapshot_dir = products_path.parent
    version = snapshot_dir.resolve().name

    candidates: list[TransformCandidate] = []
    seen_hashes: set[str] = set()

    for product in products:
        image_status = product.get("image_status")
        image_hash = product.get("image_hash")
        local_image_path = product.get("local_image_path")

        if image_status not in ELIGIBLE_IMAGE_STATUSES:
            continue
        if not image_hash or not local_image_path:
            continue

        absolute_image_path = (snapshot_dir / local_image_path).resolve()
        if not absolute_image_path.exists():
            continue
        if image_hash in seen_hashes:
            continue

        seen_hashes.add(image_hash)
        candidates.append(
            TransformCandidate(
                product_id=int(product["product_id"]),
                product_name=product.get("product_name", ""),
                image_hash=image_hash,
                image_status=image_status,
                local_image_path=local_image_path,
                absolute_image_path=absolute_image_path,
                version=version,
            )
        )

    candidates.sort(key=lambda item: (item.image_hash, item.product_id))
    return candidates


def select_candidates(
    candidates: Iterable[TransformCandidate],
    count: int = 3,
    seed: str | int | None = None,
) -> list[TransformCandidate]:
    """Select a deterministic random sample from the eligible candidates."""
    population = list(candidates)

    if count <= 0:
        raise ValueError("count must be > 0")
    if len(population) < count:
        raise ValueError(
            f"not enough eligible candidates: required={count}, available={len(population)}"
        )

    rng = random.Random(seed)
    return rng.sample(population, count)
