#!/usr/bin/env python3
"""Generate one product poster from a local reference image with Seedream 5.0 Pro.

The client uses only the Python standard library. It reads credentials from
ARK_API_KEY or VOLCENGINE_API_KEY, sends the image as a Base64 data URI, and
downloads the returned image immediately because API URLs expire.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL = "doubao-seedream-5-0-pro-260628"
SUPPORTED_EXTENSIONS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".gif": "image/gif",
    ".heic": "image/heic",
    ".heif": "image/heif",
}
MAX_INPUT_BYTES = 30 * 1024 * 1024


class SeedreamError(RuntimeError):
    """Raised for Seedream request or response failures."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate one Seedream 5.0 Pro poster from a local product image."
    )
    parser.add_argument("--image", required=True, help="Absolute path to the product image.")
    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt", help="Prompt text.")
    prompt_group.add_argument("--prompt-file", help="UTF-8 text file containing the prompt.")
    parser.add_argument("--output", required=True, help="Output poster path (.png or .jpg).")
    parser.add_argument(
        "--model",
        default=os.getenv("SEEDREAM_MODEL", DEFAULT_MODEL),
        help=f"Seedream model ID (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("SEEDREAM_BASE_URL", DEFAULT_BASE_URL),
        help=f"Ark API base URL (default: {DEFAULT_BASE_URL}).",
    )
    parser.add_argument(
        "--size",
        default="2K",
        choices=("1K", "2K"),
        help="Seedream 5.0 Pro logical output size.",
    )
    parser.add_argument(
        "--output-format",
        default=None,
        choices=("png", "jpeg"),
        help="API image format; inferred from --output by default.",
    )
    parser.add_argument(
        "--watermark",
        action="store_true",
        help="Add the service's AI-generated watermark.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Retries for 429 and 5xx responses.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Request timeout in seconds.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print a redacted payload summary without calling the API.",
    )
    return parser.parse_args()


def read_prompt(args: argparse.Namespace) -> str:
    if args.prompt is not None:
        prompt = args.prompt
    else:
        prompt_path = Path(args.prompt_file).expanduser().resolve()
        if not prompt_path.is_file():
            raise SeedreamError(f"Prompt file not found: {prompt_path}")
        prompt = prompt_path.read_text(encoding="utf-8")
    prompt = prompt.strip()
    if not prompt:
        raise SeedreamError("Prompt is empty.")
    return prompt


def resolve_image(path_value: str) -> tuple[Path, str]:
    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise SeedreamError(f"Input image not found: {path}")
    size = path.stat().st_size
    if size <= 0:
        raise SeedreamError(f"Input image is empty: {path}")
    if size > MAX_INPUT_BYTES:
        raise SeedreamError(
            f"Input image is {size / 1024 / 1024:.1f} MB; Seedream limit is 30 MB."
        )
    mime = SUPPORTED_EXTENSIONS.get(path.suffix.lower())
    if not mime:
        guessed, _ = mimetypes.guess_type(path.name)
        if guessed not in set(SUPPORTED_EXTENSIONS.values()):
            supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise SeedreamError(
                f"Unsupported input extension '{path.suffix}'. Supported: {supported}"
            )
        mime = guessed
    return path, mime


def infer_output_format(output: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    suffix = output.suffix.lower()
    if suffix == ".png":
        return "png"
    if suffix in {".jpg", ".jpeg"}:
        return "jpeg"
    raise SeedreamError("Output must end in .png, .jpg, or .jpeg, or set --output-format.")


def image_data_uri(path: Path, mime: str) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def endpoint(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/images/generations"):
        return base
    return base + "/images/generations"


def request_json(
    url: str,
    payload: dict[str, Any],
    api_key: str,
    timeout: int,
    max_retries: int,
) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "create-seedream-product-posters/1.0",
    }

    for attempt in range(max_retries + 1):
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
            return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            if exc.code in {401, 403}:
                raise SeedreamError(
                    f"Authentication failed ({exc.code}). Check ARK_API_KEY and model access."
                ) from exc
            retryable = exc.code == 429 or 500 <= exc.code < 600
            if not retryable or attempt >= max_retries:
                raise SeedreamError(
                    f"Seedream request failed ({exc.code}): {error_body[:1000]}"
                ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt >= max_retries:
                raise SeedreamError(f"Seedream request failed: {exc}") from exc

        delay = min(30.0, (2**attempt) + random.random())
        print(f"Retrying Seedream request in {delay:.1f}s...", file=sys.stderr)
        time.sleep(delay)

    raise SeedreamError("Seedream request exhausted retries.")


def extract_image(result: dict[str, Any], output: Path, timeout: int) -> None:
    data = result.get("data")
    if not isinstance(data, list) or not data:
        error = result.get("error") or result
        raise SeedreamError(f"Response contains no generated image: {error}")

    item = data[0]
    if not isinstance(item, dict):
        raise SeedreamError(f"Unexpected image result: {item!r}")
    if item.get("error"):
        raise SeedreamError(f"Image generation failed: {item['error']}")

    output.parent.mkdir(parents=True, exist_ok=True)
    if item.get("b64_json"):
        try:
            output.write_bytes(base64.b64decode(item["b64_json"], validate=True))
        except Exception as exc:
            raise SeedreamError("Invalid b64_json in response.") from exc
        return

    image_url = item.get("url")
    if not image_url:
        raise SeedreamError(f"Response image has no URL or Base64 data: {item}")

    download_request = urllib.request.Request(
        image_url,
        headers={"User-Agent": "create-seedream-product-posters/1.0"},
    )
    try:
        with urllib.request.urlopen(download_request, timeout=timeout) as response:
            output.write_bytes(response.read())
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SeedreamError(
            "Generation succeeded but downloading the expiring image URL failed."
        ) from exc


def main() -> int:
    args = parse_args()
    try:
        prompt = read_prompt(args)
        image_path, mime = resolve_image(args.image)
        output = Path(args.output).expanduser().resolve()
        output_format = infer_output_format(output, args.output_format)

        summary = {
            "endpoint": endpoint(args.base_url),
            "model": args.model,
            "prompt_characters": len(prompt),
            "image_path": str(image_path),
            "image_mime": mime,
            "image_bytes": image_path.stat().st_size,
            "size": args.size,
            "output_format": output_format,
            "watermark": args.watermark,
            "output": str(output),
        }
        if args.dry_run:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0

        api_key = os.getenv("ARK_API_KEY") or os.getenv("VOLCENGINE_API_KEY")
        if not api_key:
            raise SeedreamError(
                "No API key found. Set ARK_API_KEY or VOLCENGINE_API_KEY in the environment."
            )

        payload = {
            "model": args.model,
            "prompt": prompt,
            "image": image_data_uri(image_path, mime),
            "size": args.size,
            "output_format": output_format,
            "response_format": "url",
            "watermark": args.watermark,
        }
        print(
            f"Generating with {args.model} at {args.size}; "
            f"reference={image_path.name}; prompt={len(prompt)} chars.",
            file=sys.stderr,
        )
        result = request_json(
            endpoint(args.base_url),
            payload,
            api_key,
            args.timeout,
            args.max_retries,
        )
        extract_image(result, output, args.timeout)
        print(str(output))
        return 0
    except SeedreamError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
