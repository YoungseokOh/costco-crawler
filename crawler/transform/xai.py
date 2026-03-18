"""Minimal xAI image-edit client for smoke tests."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path

import requests

from crawler.transform.config import (
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    estimate_edit_cost_usd,
)

DEFAULT_XAI_BASE_URL = "https://api.x.ai/v1"
EXTENSIONS_BY_MEDIA_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class XAIImageTransformerError(RuntimeError):
    """Raised when an xAI image edit request fails."""


@dataclass(frozen=True)
class TransformResult:
    """Image-edit output returned by the provider."""

    image_bytes: bytes
    media_type: str
    result_url: str | None
    estimated_cost_usd: float
    provider: str = DEFAULT_PROVIDER
    model: str = DEFAULT_MODEL

    @property
    def file_extension(self) -> str:
        return EXTENSIONS_BY_MEDIA_TYPE.get(self.media_type, ".png")


class XAIImageTransformer:
    """Thin wrapper around xAI's JSON image-edit API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        base_url: str | None = None,
        timeout_seconds: int = 120,
        download_timeout_seconds: int = 120,
        session: requests.Session | None = None,
    ):
        self.api_key = api_key or os.environ.get("XAI_API_KEY")
        if not self.api_key:
            raise ValueError("XAI_API_KEY is required")

        self.model = model
        self.base_url = (base_url or os.environ.get("XAI_BASE_URL") or DEFAULT_XAI_BASE_URL).rstrip(
            "/"
        )
        self.timeout_seconds = timeout_seconds
        self.download_timeout_seconds = download_timeout_seconds
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    def edit_image(self, source_path: Path, prompt: str) -> TransformResult:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "image": {
                "url": self._build_data_uri(source_path),
                "type": "image_url",
            },
        }

        response = self.session.post(
            f"{self.base_url}/images/edits",
            json=payload,
            timeout=self.timeout_seconds,
        )
        self._raise_for_status(response, "image edit")

        try:
            body = response.json()
        except json.JSONDecodeError as exc:
            raise XAIImageTransformerError("xAI returned invalid JSON for image edit") from exc

        data = body.get("data")
        if not isinstance(data, list) or not data:
            raise XAIImageTransformerError("xAI response did not include data[0]")

        first_result = data[0]
        if not isinstance(first_result, dict):
            raise XAIImageTransformerError("xAI response data[0] was not an object")

        if "b64_json" in first_result:
            try:
                image_bytes = base64.b64decode(first_result["b64_json"])
            except (ValueError, TypeError) as exc:
                raise XAIImageTransformerError("xAI returned invalid base64 image data") from exc

            return TransformResult(
                image_bytes=image_bytes,
                media_type="image/png",
                result_url=None,
                estimated_cost_usd=estimate_edit_cost_usd(1),
                model=self.model,
            )

        result_url = first_result.get("url")
        if not result_url:
            raise XAIImageTransformerError("xAI response did not include an output image URL")

        download = self.session.get(result_url, timeout=self.download_timeout_seconds)
        self._raise_for_status(download, "image download")

        media_type = download.headers.get("Content-Type", "image/png").split(";", 1)[0].strip()
        if not media_type:
            media_type = "image/png"

        return TransformResult(
            image_bytes=download.content,
            media_type=media_type,
            result_url=result_url,
            estimated_cost_usd=estimate_edit_cost_usd(1),
            model=self.model,
        )

    @staticmethod
    def _build_data_uri(source_path: Path) -> str:
        mime_type, _ = mimetypes.guess_type(source_path.name)
        if not mime_type:
            mime_type = "image/jpeg"

        encoded = base64.b64encode(source_path.read_bytes()).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"

    @staticmethod
    def _raise_for_status(response: requests.Response, operation: str) -> None:
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            message = response.text.strip().replace("\n", " ")
            if len(message) > 500:
                message = message[:500] + "..."
            raise XAIImageTransformerError(
                f"xAI {operation} failed with HTTP {response.status_code}: {message}"
            ) from exc
