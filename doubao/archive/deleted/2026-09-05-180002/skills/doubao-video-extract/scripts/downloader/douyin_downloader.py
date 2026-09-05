#!/usr/bin/env python3
"""Download a Douyin video through the mobile share page.

Usage:
  python3 scripts/downloader/douyin_downloader.py <url_or_id>
  python3 scripts/downloader/douyin_downloader.py <url_or_id> --output-dir /path/to/project/downloads
  python3 scripts/downloader/douyin_downloader.py <url_or_id> --print-url

Output:
  Prints the absolute file path on success, or the resolved MP4 URL with --print-url.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR / "util"))

from script_utils import ensure_writable_dir, failure, normalize_share_input, print_json, resolve_short_video_url, success  # noqa: E402


PathLikeStr = Union[str, os.PathLike[str]]

MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile Safari/604.1"
)


def _resolve_output_dir(output_dir: Optional[PathLikeStr] = None) -> Path:
    configured_dir = output_dir or os.environ.get("VIDEO_SUBTITLE_DOWNLOAD_DIR")
    if configured_dir:
        return ensure_writable_dir(Path(configured_dir), fallback_name="downloads")

    return ensure_writable_dir(Path.cwd() / "downloads", fallback_name="downloads")


def _validate_douyin_video_id(video_id: str) -> None:
    if not re.fullmatch(r"\d{19}", video_id):
        raise ValueError(
            f"Invalid Douyin video ID: {video_id}. Expected a 19-digit numeric ID. "
            "Check for a copied/truncated digit or pass the original share URL."
        )


def _canonicalize_douyin_input(input_str: str) -> tuple[str, str]:
    input_str = resolve_short_video_url(normalize_share_input(input_str))
    parsed_input = urlparse(input_str)
    target_values = parse_qs(parsed_input.query).get("target", [])
    if target_values:
        input_str = resolve_short_video_url(unquote(target_values[0]))

    if input_str.isdigit():
        _validate_douyin_video_id(input_str)
        return f"https://www.douyin.com/video/{input_str}", input_str

    parsed = urlparse(input_str)
    path_match = re.search(r"/(?:video|share/video)/(\d+)", parsed.path)
    if path_match:
        video_id = path_match.group(1)
        _validate_douyin_video_id(video_id)
        return f"https://www.douyin.com/video/{video_id}", video_id

    query = parse_qs(parsed.query)
    for key in ("modal_id", "model_id"):
        for value in query.get(key, []):
            if not value:
                continue
            video_id = value.strip()
            _validate_douyin_video_id(video_id)
            return f"https://www.douyin.com/video/{video_id}", video_id

    return input_str, "video"


def _share_url(video_id: str) -> str:
    _validate_douyin_video_id(video_id)
    return f"https://www.iesdouyin.com/share/video/{video_id}/"


def _headers(referer: Optional[str] = None) -> dict[str, str]:
    headers = {
        "Accept": "*/*",
        "User-Agent": MOBILE_USER_AGENT,
    }
    if referer:
        headers["Referer"] = referer
    return headers


def _fetch_text(url: str, referer: Optional[str] = None) -> str:
    req = Request(url, headers=_headers(referer))
    with urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", "ignore")


def _extract_router_data(page_html: str) -> dict[str, Any]:
    match = re.search(r"<script>window\._ROUTER_DATA\s*=\s*(.*?)</script>", page_html, re.DOTALL)
    if not match:
        raise RuntimeError("Unable to find window._ROUTER_DATA in Douyin share page.")
    return json.loads(match.group(1))


def _find_aweme_item(router_data: dict[str, Any]) -> dict[str, Any]:
    loader_data = router_data.get("loaderData")
    if not isinstance(loader_data, dict):
        raise RuntimeError("Douyin router data does not contain loaderData.")

    for payload in loader_data.values():
        if not isinstance(payload, dict):
            continue
        video_info = payload.get("videoInfoRes")
        if not isinstance(video_info, dict):
            continue
        item_list = video_info.get("item_list")
        if isinstance(item_list, list) and item_list:
            first_item = item_list[0]
            if isinstance(first_item, dict):
                return first_item

    raise RuntimeError("Douyin router data does not contain videoInfoRes.item_list.")


def _extract_play_url_from_item(item: dict[str, Any]) -> str:
    video = item.get("video")
    if not isinstance(video, dict):
        raise RuntimeError("Douyin item does not contain video metadata.")

    play_addr = video.get("play_addr")
    if not isinstance(play_addr, dict):
        raise RuntimeError("Douyin item does not contain video.play_addr.")

    url_list = play_addr.get("url_list")
    if not isinstance(url_list, list) or not url_list:
        raise RuntimeError("Douyin video.play_addr.url_list is empty.")

    return str(url_list[0]).replace("\\/", "/")


def _first_url(node: Any) -> Optional[str]:
    if isinstance(node, dict):
        url_list = node.get("url_list")
        if isinstance(url_list, list) and url_list:
            return str(url_list[0]).replace("\\/", "/")
        uri = node.get("uri")
        if isinstance(uri, str) and uri.startswith(("http://", "https://")):
            return uri.replace("\\/", "/")
    return None


def _extract_item_metadata(item: dict[str, Any]) -> dict[str, Any]:
    author = item.get("author") if isinstance(item.get("author"), dict) else {}
    video = item.get("video") if isinstance(item.get("video"), dict) else {}
    statistics = item.get("statistics") if isinstance(item.get("statistics"), dict) else {}
    return {
        key: value
        for key, value in {
            "aweme_id": item.get("aweme_id"),
            "description": item.get("desc"),
            "create_time": item.get("create_time"),
            "duration": video.get("duration"),
            "cover_url": _first_url(video.get("cover")),
            "dynamic_cover_url": _first_url(video.get("dynamic_cover")),
            "author_nickname": author.get("nickname"),
            "author_uid": author.get("uid"),
            "author_sec_uid": author.get("sec_uid"),
            "statistics": statistics or None,
        }.items()
        if value not in (None, "", {}, [])
    }


def resolve_video_info(input_str: str) -> dict[str, Any]:
    _, video_id = _canonicalize_douyin_input(input_str)
    share_url = _share_url(video_id)
    page_html = _fetch_text(share_url)
    item = _find_aweme_item(_extract_router_data(page_html))
    return {
        "video_url": _extract_play_url_from_item(item),
        "video_id": video_id,
        "page_url": f"https://www.douyin.com/video/{video_id}",
        "share_url": share_url,
        "platform": "douyin",
        "metadata": _extract_item_metadata(item),
    }


def resolve_video_url(input_str: str) -> str:
    return resolve_video_info(input_str)["video_url"]


def _download_file(video_url: str, output_path: Path, referer: Optional[str] = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        dir=str(output_path.parent),
    )
    os.close(tmp_fd)
    tmp_path = Path(tmp_name)

    try:
        req = Request(video_url, headers=_headers(referer))
        with urlopen(req, timeout=60) as response, tmp_path.open("wb") as out_file:
            content_type = (response.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
            if not content_type.startswith("video/"):
                raise RuntimeError(f"Resolved Douyin URL did not return video content: {content_type or 'unknown'}")
            shutil.copyfileobj(response, out_file, length=1024 * 1024)
        tmp_path.replace(output_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    return output_path


def download(input_str: str, output_dir: Optional[PathLikeStr] = None) -> str:
    _, video_id = _canonicalize_douyin_input(input_str)
    info = resolve_video_info(input_str)
    play_url = info["video_url"]

    out_dir = _resolve_output_dir(output_dir)
    output_path = out_dir / f"douyin_{video_id}.mp4"
    saved_path = _download_file(play_url, output_path, referer=_share_url(video_id))

    abs_path = saved_path.resolve()
    if not abs_path.exists() or abs_path.stat().st_size == 0:
        raise FileNotFoundError(f"Downloaded file not found or empty: {abs_path}")

    return str(abs_path)


def check_environment() -> dict[str, object]:
    return {
        "mobile_share_page_download": True,
        "mobile_user_agent": MOBILE_USER_AGENT,
        "supports_share_text": True,
        "supports_short_links": True,
        "supports_modal_id": True,
        "supports_model_id": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download a Douyin video through the mobile share page and print the saved MP4 absolute path."
    )
    parser.add_argument("url_or_id", help="Douyin video URL or numeric video ID")
    parser.add_argument(
        "--output-dir",
        help=(
            "Directory for downloaded files. Defaults to $VIDEO_SUBTITLE_DOWNLOAD_DIR "
            "or ./downloads under the current working directory."
        ),
    )
    parser.add_argument("--print-url", action="store_true", help="Print the resolved play URL instead of downloading.")
    parser.add_argument("--json", action="store_true", help="Print structured JSON output.")
    parser.add_argument("--check", action="store_true", help="Check downloader capabilities and exit.")
    args = parser.parse_args()

    input_str = args.url_or_id.strip()

    try:
        if args.check:
            payload = success(check_environment())
        elif args.print_url:
            payload = success(resolve_video_info(input_str))
        else:
            file_path = download(input_str, output_dir=args.output_dir)
            info = resolve_video_info(input_str)
            payload = success({"file_path": file_path, **{k: v for k, v in info.items() if k != "video_url"}})

        if args.json or args.check or args.print_url:
            print_json(payload)
        else:
            print(payload["data"]["file_path"])
    except Exception as exc:
        payload = failure(
            exc,
            "Open the Douyin link in a browser to confirm it is public, retry later if the share page blocks access, "
            "or manually provide a direct video URL / downloaded MP4 for Lark Minutes.",
        )
        if args.json:
            print_json(payload)
        else:
            print(f"Download failed: {payload['error']}\nNext step: {payload['solution']}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
