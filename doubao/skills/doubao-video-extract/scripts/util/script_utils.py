"""Shared helpers for video-extract scripts."""

import json
import re
import shutil
import tempfile
import warnings
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen

warnings.filterwarnings("ignore", message=r"urllib3 v2 only supports OpenSSL.*")
warnings.filterwarnings("ignore", message=r"Support for Python version .* has been deprecated.*")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)


def extract_first_url(input_str: str) -> Optional[str]:
    match = re.search(r"https?://[^\s\"'<>，。；、）)\]]+", input_str.strip())
    if not match:
        return None
    return match.group(0).rstrip(".,;，。；、")


def normalize_share_input(input_str: str) -> str:
    return extract_first_url(input_str) or input_str.strip()


def resolve_redirect_url(url: str, timeout: int = 15) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as response:
        return response.geturl()


def resolve_short_video_url(input_str: str) -> str:
    value = normalize_share_input(input_str)
    parsed = urlparse(value)
    host = parsed.netloc.lower()
    target_values = parse_qs(parsed.query).get("target", [])
    if target_values:
        return resolve_short_video_url(unquote(target_values[0]))

    short_hosts = (
        "v.douyin.com",
        "www.iesdouyin.com",
        "b23.tv",
        "v.kuaishou.com",
        "u.kuaishou.com",
    )
    if parsed.scheme in {"http", "https"} and any(h in host for h in short_hosts):
        return resolve_redirect_url(value)
    return value


def check_executable(name: str) -> dict[str, Any]:
    path = shutil.which(name)
    return {"name": name, "available": bool(path), "path": path}


def ensure_writable_dir(path: Path, fallback_name: str = "downloads") -> Path:
    target = path.expanduser().resolve()
    try:
        target.mkdir(parents=True, exist_ok=True)
        test_file = target / ".write-test"
        test_file.write_text("", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        return target
    except Exception:
        fallback = Path.home() / ".cache" / "video-extract" / fallback_name
        try:
            fallback.mkdir(parents=True, exist_ok=True)
            test_file = fallback / ".write-test"
            test_file.write_text("", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            return fallback.resolve()
        except Exception:
            temp_dir = Path(tempfile.mkdtemp(prefix="video-extract-"))
            return temp_dir.resolve()


def success(data: dict[str, Any]) -> dict[str, Any]:
    return {"success": True, "data": data}


def failure(exc: Exception, solution: str = "") -> dict[str, Any]:
    return {
        "success": False,
        "error": str(exc),
        "solution": solution,
    }


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
