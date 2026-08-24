"""get_logo.py — fetch a brand / website logo for pptx-0630.

Unlike :mod:`get_image` (which *generates* photos via mulerouter), a logo is
a **deterministic asset** that already exists on the target's own servers.
This module fetches it directly, with no third-party logo broker — so it
works from networks where Clearbit / Google s2 favicons / Brandfetch are
unreachable.

Resolution chain (per domain):

1. **cache hit** — sha1(domain|size) → reuse local file.
2. **site <link> icons** — fetch ``https://<domain>/`` HTML, parse
   ``<link rel="icon|shortcut icon|apple-touch-icon|mask-icon">``, pick the
   highest-resolution candidate, download it from the site's own host.
   Apple-touch-icons are typically 180×180+ PNGs — good enough for a slide.
3. **/favicon.ico** — when the page exposes no usable <link>, try the
   conventional ``https://<domain>/favicon.ico``.
4. **domestic favicon API** — ``https://api.iowen.cn/favicon/<domain>.png``
   (一为 favicon; mainland-hosted, reachable from China, returns a cached
   ~256px PNG). Last-resort fallback when the site can't be reached directly.
5. **failure** — raise :class:`LogoFetchError` (importable) or emit
   structured JSON + non-zero exit (CLI). The caller decides whether to
   degrade to a plain text brand name (do NOT fake a logo from shapes).

Two entry points mirror get_image.py:

CLI single::

    python scripts/get_logo.py --domain stripe.com --out assets/logos/stripe.png

CLI batch::

    python scripts/get_logo.py --batch domains.jsonl [--concurrency 4]
    # domains.jsonl: one JSON object per line:
    #   {"domain":"stripe.com","out":"assets/logos/stripe.png"}

Importable::

    from scripts.get_logo import fetch_logo, fetch_logos, LogoFetchError
    path = fetch_logo("stripe.com", out_dir="assets/logos")
    results = fetch_logos([
        {"domain": "stripe.com", "out": "assets/logos/stripe.png"},
        {"domain": "notion.so"},
    ], concurrency=4)
    # results: [{"ok":True,"path":...,"source":"site|favicon-ico|iowen"} | {"ok":False,"reason":...}, ...]

Exit codes (CLI):

- ``0`` — success (any source delivered)
- ``1`` — fetch failed (no source returned a usable file)
- ``5`` — sandbox blocks network (probe failed; agent should request escalation)
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import shutil
import socket
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Optional


# ---------- config -----------------------------------------------------------

_UA = "Mozilla/5.0 (pptx-0630 logo-fetch)"
_IOWEN_API = "https://api.iowen.cn/favicon/{domain}.png"

# Network probe targets — distinguish "sandbox blocks egress" from "the site
# itself is down". We probe a domestic host (always reachable from CN) plus a
# generic one. Cached once per process.
_NETWORK_PROBES = (
    ("api.iowen.cn", 443),
    ("www.baidu.com", 443),
)

# <link rel> values we treat as icons, ranked: a dedicated PNG icon beats the
# legacy .ico, and apple-touch-icon is usually the largest bitmap available.
_ICON_RELS = ("apple-touch-icon", "apple-touch-icon-precomposed", "icon", "shortcut icon", "mask-icon")


class LogoFetchError(RuntimeError):
    """Raised by :func:`fetch_logo` when no source could deliver a logo.

    Attributes:
      reason: short machine-friendly reason.
      retryable: True when a retry might succeed (transient network blip).
    """

    def __init__(self, reason: str, *, retryable: bool = False):
        super().__init__(reason)
        self.reason = reason
        self.retryable = retryable


# ---------- helpers ----------------------------------------------------------


def _normalize_domain(raw: str) -> str:
    """Accept a bare domain or a full URL; return the bare host (no scheme/path)."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    if "//" in raw:
        raw = urllib.parse.urlparse(raw).netloc or raw.split("//", 1)[1]
    raw = raw.split("/", 1)[0].strip().lower()
    # strip a leading "www." for the cache slug / iowen lookup; keep otherwise
    return raw


def _slug(domain: str, size: int) -> str:
    h = hashlib.sha1(f"{domain}|{size}".encode()).hexdigest()[:10]
    safe = re.sub(r"[^a-z0-9]+", "-", domain.lower()).strip("-") or "logo"
    return f"{safe}-{h}"


def _download(url: str, out: Path, *, referer: Optional[str] = None) -> bool:
    out.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": _UA, "Accept": "image/*,*/*"}
    if referer:
        headers["Referer"] = referer
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r, open(out, "wb") as f:
            shutil.copyfileobj(r, f)
        # Reject tiny / empty responses (error pages, 1px trackers).
        return out.exists() and out.stat().st_size > 512
    except Exception as e:
        print(f"[get_logo] download failed {url}: {e}", file=sys.stderr)
        if out.exists() and out.stat().st_size <= 512:
            out.unlink(missing_ok=True)
        return False


def _fetch_html(url: str) -> Optional[str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "text/html,*/*"})
        with urllib.request.urlopen(req, timeout=20) as r:
            charset = r.headers.get_content_charset() or "utf-8"
            raw = r.read(512 * 1024)  # only the head matters; cap at 512KB
        return raw.decode(charset, errors="replace")
    except Exception as e:
        print(f"[get_logo] html fetch failed {url}: {e}", file=sys.stderr)
        return None


# ---------- network probe (sandbox detection) --------------------------------


_NETWORK_OK: Optional[bool] = None


def _check_network(timeout: float = 2.5) -> bool:
    """Quick TCP probe. Cached per-process. True = at least one host reachable."""
    global _NETWORK_OK
    if _NETWORK_OK is not None:
        return _NETWORK_OK
    for host, port in _NETWORK_PROBES:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                _NETWORK_OK = True
                return True
        except (OSError, socket.timeout):
            continue
    _NETWORK_OK = False
    return False


# ---------- <link> icon parsing ----------------------------------------------


class _IconLinkParser(HTMLParser):
    """Collect ``<link rel=icon ...>`` candidates from a page <head>."""

    def __init__(self) -> None:
        super().__init__()
        self.icons: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag.lower() != "link":
            return
        a = {k.lower(): (v or "") for k, v in attrs}
        rel = a.get("rel", "").lower()
        if not any(r in rel for r in ("icon", "mask-icon")):
            return
        href = a.get("href", "").strip()
        if not href:
            return
        self.icons.append({"rel": rel, "href": href, "sizes": a.get("sizes", "").lower()})


def _icon_score(icon: dict[str, str]) -> tuple[int, int]:
    """Rank icon candidates: prefer apple-touch (large bitmap), then bigger
    declared ``sizes``, then non-.ico raster over legacy .ico."""
    rel = icon["rel"]
    rel_rank = 0
    for i, r in enumerate(_ICON_RELS):
        if r in rel:
            rel_rank = len(_ICON_RELS) - i
            break
    px = 0
    m = re.search(r"(\d+)x(\d+)", icon.get("sizes", ""))
    if m:
        px = int(m.group(1))
    elif icon.get("sizes") == "any":
        px = 1  # vector; usable but unranked by pixels
    return (px, rel_rank)


def _site_icon_url(domain: str) -> Optional[str]:
    """Parse the homepage and return the best absolute icon URL, or None."""
    base = f"https://{domain}/"
    html = _fetch_html(base)
    if not html:
        return None
    parser = _IconLinkParser()
    try:
        parser.feed(html)
    except Exception:
        pass
    if not parser.icons:
        return None
    best = max(parser.icons, key=_icon_score)
    return urllib.parse.urljoin(base, best["href"])


# ---------- public single API ------------------------------------------------


def fetch_logo(
    domain: str,
    *,
    out_dir: str | os.PathLike = "assets/logos",
    out_name: Optional[str] = None,
    size: int = 256,
) -> str:
    """Resolve a domain to a local logo file. Returns the absolute path.

    Order: cache → site <link> icons → /favicon.ico → iowen favicon API.
    Raises :class:`LogoFetchError` when nothing worked; callers SHOULD catch
    and degrade to a plain text brand name (never fake a logo from shapes).
    """
    domain = _normalize_domain(domain)
    if not domain or "." not in domain:
        raise LogoFetchError(f"invalid domain {domain!r}")

    out_dir_path = Path(out_dir).resolve()
    out_dir_path.mkdir(parents=True, exist_ok=True)
    filename = out_name or f"{_slug(domain, size)}.png"
    out_path = out_dir_path / filename

    if out_path.exists() and out_path.stat().st_size > 512:
        return str(out_path)

    if not _check_network():
        raise LogoFetchError("sandbox_blocks_network", retryable=False)

    referer = f"https://{domain}/"

    # 2. site <link> icons
    icon_url = _site_icon_url(domain)
    if icon_url and _download(icon_url, out_path, referer=referer):
        return str(out_path)

    # 3. conventional /favicon.ico
    if _download(f"https://{domain}/favicon.ico", out_path, referer=referer):
        return str(out_path)

    # 4. domestic favicon API fallback
    if _download(_IOWEN_API.format(domain=domain), out_path):
        return str(out_path)

    raise LogoFetchError("no logo source returned a usable file", retryable=True)


# ---------- public batch API -------------------------------------------------


def fetch_logos(
    jobs: list[dict[str, Any]],
    *,
    concurrency: int = 4,
    size: int = 256,
) -> list[dict[str, Any]]:
    """Fetch multiple logos in parallel. Mirrors get_image.fetch_many.

    Each job dict accepts: ``domain`` (required), ``out`` (full path; default
    ``assets/logos/<slug>.png``), ``size`` (default 256).

    Returns a list of result dicts (one per input, same order):
      ``{"ok": True, "path": "...", "source": "site|favicon-ico|iowen|cache"}``
      ``{"ok": False, "reason": "...", "retryable": bool, "domain": "..."}``
    """
    if not jobs:
        return []

    def _one(job: dict[str, Any]) -> dict[str, Any]:
        domain = _normalize_domain(job.get("domain", ""))
        out = job.get("out") or job.get("out_path")
        out_dir = "assets/logos"
        out_name = None
        if out:
            out_p = Path(out)
            out_dir = str(out_p.parent)
            out_name = out_p.name
        existed_before = bool(out and Path(out).exists())
        try:
            path = fetch_logo(
                domain, out_dir=out_dir, out_name=out_name, size=job.get("size", size)
            )
            return {"ok": True, "path": path, "source": "cache" if existed_before else "fetched", "domain": domain}
        except LogoFetchError as e:
            return {"ok": False, "reason": e.reason, "retryable": e.retryable, "domain": domain}

    results: list[Optional[dict[str, Any]]] = [None] * len(jobs)
    with cf.ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
        futs = {ex.submit(_one, job): idx for idx, job in enumerate(jobs)}
        for fut in cf.as_completed(futs):
            results[futs[fut]] = fut.result()
    return [r for r in results if r is not None]


# ---------- CLI --------------------------------------------------------------


def _cli_single(args: argparse.Namespace) -> int:
    out = Path(args.out).resolve() if args.out else None
    try:
        path = fetch_logo(
            args.domain,
            out_dir=str(out.parent) if out else "assets/logos",
            out_name=out.name if out else None,
            size=args.size,
        )
        print(json.dumps({"ok": True, "path": path}, ensure_ascii=False))
        return 0
    except LogoFetchError as e:
        print(json.dumps({"ok": False, "reason": e.reason, "retryable": e.retryable}, ensure_ascii=False))
        return 5 if e.reason == "sandbox_blocks_network" else 1


def _cli_batch(args: argparse.Namespace) -> int:
    jobs: list[dict[str, Any]] = []
    with open(args.batch) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                jobs.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"[get_logo] skipping bad line: {e}", file=sys.stderr)
    if not jobs:
        print(json.dumps({"ok": False, "reason": "no jobs"}))
        return 1
    results = fetch_logos(jobs, concurrency=args.concurrency, size=args.size)
    n_ok = sum(1 for r in results if r.get("ok"))
    out = {"ok": n_ok > 0, "succeeded": n_ok, "failed": len(results) - n_ok, "results": results}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if n_ok == len(results) else 1


def _cli() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--domain", help="single mode: domain or URL, e.g. stripe.com")
    p.add_argument("--out", help="single mode: output file path (.png)")
    p.add_argument("--size", type=int, default=256, help="preferred logo size hint (default: 256)")
    p.add_argument("--batch", help="batch mode: JSONL file, one {domain,out} per line")
    p.add_argument("--concurrency", type=int, default=4, help="batch mode: parallel workers (default: 4)")
    args = p.parse_args()

    if args.batch:
        return _cli_batch(args)
    if args.domain:
        return _cli_single(args)
    p.error("either --domain or --batch is required")
    return 1


if __name__ == "__main__":
    sys.exit(_cli())
