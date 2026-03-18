#!/usr/bin/env python3
# ruff: noqa: E402
"""Run a manual 3-image transform smoke test against the current dataset."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crawler.transform.config import (
    DEFAULT_MODEL,
    DEFAULT_PROMPT_VERSION,
    DEFAULT_PROVIDER,
    DEFAULT_TRANSFORM_PROMPT,
    XAI_INPUT_IMAGE_COST_USD,
    XAI_OUTPUT_IMAGE_COST_USD,
    estimate_edit_cost_usd,
    format_usd,
)
from crawler.transform.smoke import collect_candidates, select_candidates
from crawler.transform.xai import XAIImageTransformer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the xAI image transform smoke test")
    parser.add_argument(
        "--products-path",
        default="data/current/products.json",
        help="Path to the products.json snapshot to sample from",
    )
    parser.add_argument(
        "--artifact-dir",
        default="artifacts/image-transform-smoke",
        help="Directory where smoke-test artifacts will be written",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=3,
        help="Number of distinct image hashes to sample",
    )
    parser.add_argument(
        "--seed",
        default=None,
        help="Optional deterministic seed for random sample selection",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="xAI image model to use",
    )
    parser.add_argument(
        "--prompt-version",
        default=DEFAULT_PROMPT_VERSION,
        help="Prompt version label written into the smoke-test summary",
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_TRANSFORM_PROMPT,
        help="Prompt used for image editing",
    )
    return parser.parse_args()


def _write_summary_files(artifact_dir: Path, payload: dict) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    markdown = render_summary_markdown(payload)
    (artifact_dir / "summary.md").write_text(markdown + "\n", encoding="utf-8")

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as handle:
            handle.write(markdown + "\n")


def render_summary_markdown(payload: dict) -> str:
    lines = [
        "## Image Transform Smoke Test",
        "",
        f"- Status: `{payload['status']}`",
        f"- Provider: `{payload['provider']}`",
        f"- Model: `{payload['model']}`",
        f"- Prompt version: `{payload['prompt_version']}`",
        f"- Products path: `{payload['products_path']}`",
        f"- Snapshot version: `{payload['snapshot_version']}`",
        f"- Selection seed: `{payload['selection_seed']}`",
        f"- Eligible unique image hashes: `{payload['eligible_unique_hashes']}`",
        f"- Requested sample count: `{payload['requested_sample_count']}`",
        f"- Estimated per edit cost: `{payload['pricing']['estimated_per_edit_usd']}`",
        f"- Estimated total cost: `{payload['pricing']['estimated_total_usd']}`",
    ]

    error = payload.get("error")
    if error:
        lines.extend(["", f"- Error: `{error}`"])

    samples = payload.get("samples", [])
    if samples:
        lines.extend(
            [
                "",
                "| # | product_id | image_hash | status | after |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for idx, sample in enumerate(samples, start=1):
            lines.append(
                "| {idx} | {product_id} | `{image_hash}` | `{status}` | `{after_path}` |".format(
                    idx=idx,
                    product_id=sample["product_id"],
                    image_hash=sample["image_hash"][:12],
                    status=sample["status"],
                    after_path=sample.get("artifact_after_path", "-"),
                )
            )

    return "\n".join(lines)


def _build_base_payload(
    args: argparse.Namespace,
    products_path: Path,
    candidates: list,
    seed: str,
) -> dict:
    snapshot_version = products_path.parent.resolve().name
    return {
        "status": "running",
        "provider": DEFAULT_PROVIDER,
        "model": args.model,
        "prompt_version": args.prompt_version,
        "prompt": args.prompt,
        "products_path": str(products_path),
        "snapshot_version": snapshot_version,
        "selection_seed": seed,
        "requested_sample_count": args.count,
        "eligible_unique_hashes": len(candidates),
        "pricing": {
            "input_image_usd": format_usd(XAI_INPUT_IMAGE_COST_USD),
            "output_image_usd": format_usd(XAI_OUTPUT_IMAGE_COST_USD),
            "estimated_per_edit_usd": format_usd(estimate_edit_cost_usd(1)),
            "estimated_total_usd": format_usd(estimate_edit_cost_usd(args.count)),
        },
        "started_at": datetime.now(timezone.utc).isoformat(),
        "samples": [],
    }


def run() -> int:
    args = parse_args()
    artifact_dir = Path(args.artifact_dir)
    before_dir = artifact_dir / "before"
    after_dir = artifact_dir / "after"
    before_dir.mkdir(parents=True, exist_ok=True)
    after_dir.mkdir(parents=True, exist_ok=True)

    products_path = Path(args.products_path)
    selection_seed = (
        args.seed
        or os.environ.get("GITHUB_RUN_ID")
        or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    )

    payload: dict = {
        "status": "failed",
        "provider": DEFAULT_PROVIDER,
        "model": args.model,
        "prompt_version": args.prompt_version,
        "products_path": str(products_path),
        "snapshot_version": "unknown",
        "selection_seed": selection_seed,
        "requested_sample_count": args.count,
        "eligible_unique_hashes": 0,
        "pricing": {
            "input_image_usd": format_usd(XAI_INPUT_IMAGE_COST_USD),
            "output_image_usd": format_usd(XAI_OUTPUT_IMAGE_COST_USD),
            "estimated_per_edit_usd": format_usd(estimate_edit_cost_usd(1)),
            "estimated_total_usd": format_usd(estimate_edit_cost_usd(args.count)),
        },
        "started_at": datetime.now(timezone.utc).isoformat(),
        "samples": [],
    }

    try:
        candidates = collect_candidates(products_path)
        payload = _build_base_payload(args, products_path, candidates, str(selection_seed))
        samples = select_candidates(candidates, count=args.count, seed=selection_seed)
        transformer = XAIImageTransformer(model=args.model)

        failure_count = 0

        for idx, sample in enumerate(samples, start=1):
            source_filename = (
                f"{idx:02d}-{sample.product_id}-{sample.image_hash[:12]}"
                f"{sample.absolute_image_path.suffix.lower() or '.jpg'}"
            )
            before_artifact_path = before_dir / source_filename
            shutil.copy2(sample.absolute_image_path, before_artifact_path)

            sample_payload = {
                "product_id": sample.product_id,
                "product_name": sample.product_name,
                "image_hash": sample.image_hash,
                "image_status": sample.image_status,
                "local_image_path": sample.local_image_path,
                "source_absolute_path": str(sample.absolute_image_path),
                "artifact_before_path": str(before_artifact_path.relative_to(artifact_dir)),
                "artifact_after_path": None,
                "status": "pending",
            }

            try:
                result = transformer.edit_image(sample.absolute_image_path, args.prompt)
                output_filename = (
                    f"{idx:02d}-{sample.product_id}-{sample.image_hash[:12]}"
                    f"{result.file_extension}"
                )
                after_artifact_path = after_dir / output_filename
                after_artifact_path.write_bytes(result.image_bytes)

                sample_payload.update(
                    {
                        "status": "success",
                        "provider": result.provider,
                        "model": result.model,
                        "result_url": result.result_url,
                        "media_type": result.media_type,
                        "estimated_cost_usd": format_usd(result.estimated_cost_usd),
                        "artifact_after_path": str(after_artifact_path.relative_to(artifact_dir)),
                    }
                )
            except Exception as exc:
                failure_count += 1
                sample_payload.update(
                    {
                        "status": "failed",
                        "error": str(exc),
                    }
                )

            payload["samples"].append(sample_payload)

        payload["completed_at"] = datetime.now(timezone.utc).isoformat()
        payload["status"] = "failed" if failure_count else "success"
        payload["failed_samples"] = failure_count
    except Exception as exc:
        payload["status"] = "failed"
        payload["completed_at"] = datetime.now(timezone.utc).isoformat()
        payload["error"] = str(exc)
    finally:
        _write_summary_files(artifact_dir, payload)

    return 1 if payload["status"] != "success" else 0


if __name__ == "__main__":
    raise SystemExit(run())
