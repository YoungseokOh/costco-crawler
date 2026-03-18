"""Shared configuration for image transform experiments."""

from __future__ import annotations

DEFAULT_PROVIDER = "xai"
DEFAULT_MODEL = "grok-imagine-image"
DEFAULT_PROMPT_VERSION = "angle-smoke-v1"
DEFAULT_TRANSFORM_PROMPT = (
    "Create a photorealistic studio product image of the exact same retail item from a "
    "different random camera angle. Preserve the package shape, brand name, logos, label "
    "text, colors, materials, and proportions exactly. Keep the full product fully in "
    "frame on a clean white background. Do not add hands, props, shelves, extra products, "
    "or extra text."
)

XAI_INPUT_IMAGE_COST_USD = 0.002
XAI_OUTPUT_IMAGE_COST_USD = 0.02


def estimate_edit_cost_usd(edit_count: int, input_images_per_edit: int = 1) -> float:
    """Estimate xAI image-edit cost using the current per-image pricing."""
    if edit_count < 0:
        raise ValueError("edit_count must be >= 0")
    if input_images_per_edit < 0:
        raise ValueError("input_images_per_edit must be >= 0")

    return edit_count * (
        XAI_OUTPUT_IMAGE_COST_USD + (XAI_INPUT_IMAGE_COST_USD * input_images_per_edit)
    )


def format_usd(amount: float) -> str:
    """Format a USD amount consistently for summaries."""
    return f"${amount:.4f}"
