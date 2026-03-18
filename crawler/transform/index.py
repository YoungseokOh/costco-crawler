"""Persistent transform index for future backfill and incremental runs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from crawler import MASTER_DIR

INDEX_FILENAME = "image_transform_index.json"


@dataclass(eq=True)
class TransformRecord:
    """Single transformed asset record keyed by source image hash."""

    source_hash: str
    provider: str
    model: str
    prompt_version: str
    status: str
    transformed_master_path: str | None = None
    created_at: str | None = None
    last_error: str | None = None


class TransformIndex:
    """Read and write the image transform registry."""

    def __init__(self, path: Path | None = None):
        self.path = path or (MASTER_DIR / INDEX_FILENAME)

    def load(self) -> dict[str, TransformRecord]:
        if not self.path.exists():
            return {}

        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return {
            source_hash: TransformRecord(**record)
            for source_hash, record in payload.items()
        }

    def save(self, records: Mapping[str, TransformRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            source_hash: asdict(record)
            for source_hash, record in sorted(records.items())
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
