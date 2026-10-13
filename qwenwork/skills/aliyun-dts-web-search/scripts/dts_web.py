#!/usr/bin/env python3
"""Command-line interface for Alibaba Cloud DTS-AI WebSearch and WebFetch."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
from pathlib import Path
import re
import sys
import time
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
import uuid

_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import dts_api_key_configuration  # noqa: E402  (provided with this script)


ENDPOINT = "https://dtsai.cn-beijing.aliyuncs.com"
VERSION = "2026-04-01"
REGION = "cn-beijing"
MAX_FETCH_PAGES = 5
MIN_CONTENT_CHARS = 500
HTTP_TIMEOUT_SECONDS = 30
TRANSIENT_HTTP = {408, 425, 429, 500, 502, 503, 504}
# Strip only deterministic tracking parameters. Generic-looking keys such as
# "source", "ver", or "new" can be functional and must not be removed.
TRACKING_KEYS = {"spm"}
TRACKING_PREFIXES = ("utm_",)


class DtsError(RuntimeError):
    """A transport, protocol, or DTS-AI API error."""


class ValidationError(DtsError):
    """A local input or environment prerequisite check failure."""


def require_environment() -> str:
    try:
        api_key = dts_api_key_configuration.resolve_api_key()
    except dts_api_key_configuration.CredentialError as exc:
        raise ValidationError(str(exc)) from exc
    if not api_key:
        raise ValidationError(
            "DTS_AI_API_KEY is not configured. Run 'setup' to open the local browser, "
            "or set it in the current environment and retry."
        )
    return api_key


def _integer_or_zero(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def parse_json_lenient(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8", errors="replace"), strict=False)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DtsError(f"DTS-AI returned unparseable JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise DtsError("DTS-AI returned a non-object JSON response")
    return value


def request(action: str, payload: dict[str, Any], retries: int = 2) -> dict[str, Any]:
    """POST one DTS-AI action with the API key sent only as an in-process header."""
    api_key = require_environment()
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    last_error = "unknown error"

    for attempt in range(retries + 1):
        nonce = str(uuid.uuid4())
        url = f"{ENDPOINT}?Action={action}&Version={VERSION}&SignatureNonce={nonce}"
        http_request = Request(
            url,
            data=body,
            headers={
                "X-Acs-ApiKey": api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        raw = b""
        transport_http = 0
        transport_error: Optional[BaseException] = None

        try:
            with urlopen(http_request, timeout=HTTP_TIMEOUT_SECONDS) as reply:
                transport_http = reply.getcode()
                raw = reply.read()
        except HTTPError as exc:
            transport_http = exc.code
            raw = exc.read()
        except (URLError, TimeoutError, OSError) as exc:
            transport_error = exc

        if transport_error is not None:
            last_error = f"{action} transport error: {transport_error}"
            transient = True
        else:
            try:
                response = parse_json_lenient(raw)
            except DtsError as exc:
                last_error = str(exc)
                transient = transport_http in TRANSIENT_HTTP
            else:
                api_http = _integer_or_zero(
                    response.get("HttpStatusCode") or transport_http
                )
                if (
                    response.get("Success") is True
                    and transport_http == 200
                    and api_http == 200
                ):
                    return response
                code = response.get("ErrorCode") or "UnknownApiError"
                message = response.get("ErrorMessage") or "no details"
                request_id = response.get("RequestId") or "unknown"
                last_error = (
                    f"{code}: {message} "
                    f"(HTTP {transport_http or api_http}, RequestId={request_id})"
                )
                transient = transport_http in TRANSIENT_HTTP or api_http in TRANSIENT_HTTP

        if not transient or attempt == retries:
            raise DtsError(last_error)
        time.sleep(1 + attempt)

    raise DtsError(last_error)


def unwrap_redirect(url: str) -> str:
    """Extract targets from common search and CAPTCHA URLs without following them."""
    current = url.strip()
    for _ in range(2):
        parsed = urlsplit(current)
        params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        target = params.get("target_url")
        if not target:
            break
        candidate = unquote(target)
        if not candidate.startswith(("http://", "https://")):
            break
        current = candidate
    return current


def normalize_url(url: str) -> str:
    parsed = urlsplit(unwrap_redirect(url))
    scheme = parsed.scheme.lower() or "https"
    if scheme not in {"http", "https"}:
        raise DtsError(f"Unsupported URL scheme: {scheme}")
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise DtsError("URL must include a hostname")
    try:
        port = parsed.port
    except ValueError as exc:
        raise DtsError("URL contains an invalid port") from exc
    netloc = hostname
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{hostname}:{port}"
    kept = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered in TRACKING_KEYS or lowered.startswith(TRACKING_PREFIXES):
            continue
        kept.append((key, value))
    query = urlencode(kept, doseq=True)
    return urlunsplit((scheme, netloc, parsed.path or "/", query, ""))


def prepare_fetch_url(url: str) -> str:
    """Validate a fetch target without rewriting its path or query.

    Normalization is for deduplication and display only. The URL actually
    sent to WebFetch keeps every query parameter, because generic-looking keys
    can be functional and stripping them may change the fetched content.
    """
    candidate = unwrap_redirect(url)
    parsed = urlsplit(candidate)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise DtsError(f"Unsupported URL scheme: {scheme or '(none)'}")
    if not parsed.hostname:
        raise DtsError("URL must include a hostname")
    try:
        parsed.port
    except ValueError as exc:
        raise DtsError("URL contains an invalid port") from exc
    return candidate


def safe_output_url(url: str) -> str:
    try:
        return normalize_url(url)
    except (DtsError, ValueError):
        return "(invalid URL)"


def clean_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(ch for ch in text if ch in "\n\t" or ch.isprintable())
    lines: list[str] = []
    previous = None
    blank = False
    for raw_line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if not line:
            if lines and not blank:
                lines.append("")
            blank = True
            continue
        blank = False
        if line == previous:
            continue
        lines.append(line)
        previous = line
    return "\n".join(lines).strip()


def is_garbled(text: str) -> bool:
    sample = text[:20000]
    if not sample:
        return True
    replacement_ratio = sample.count("\ufffd") / len(sample)
    readable = sum(ch.isprintable() or ch in "\n\r\t" for ch in sample) / len(sample)
    return replacement_ratio > 0.01 or readable < 0.85


def looks_like_error_page(title: str) -> bool:
    """Heuristic: the page title indicates an HTTP error page, not content.

    Title-only matching can flag a correctly written article about error pages, so the
    caller only marks the result with a quality flag instead of failing.
    """
    if not title:
        return False
    folded = title.casefold()
    if "404" in folded or "not found" in folded:
        return True
    return any(
        marker in title
        for marker in (
            "\u9875\u9762\u4e0d\u5b58\u5728",  # page does not exist
            "\u9875\u9762\u672a\u627e\u5230",  # page not found
            "\u9519\u8bef\u9875",  # error page
        )
    )


def parse_keywords(value: Optional[str]) -> list[str]:
    if not value:
        return []
    keywords = []
    seen = set()
    for item in re.split(r"[,\uFF0C]", value):
        keyword = item.strip()
        key = keyword.casefold()
        if keyword and key not in seen:
            keywords.append(keyword)
            seen.add(key)
    return keywords


def keyword_in_text(keyword: str, folded_text: str) -> bool:
    """Perform a case-insensitive match; a numeric keyword must stand alone.

    A pure-digit keyword such as "18" must not match inside a longer number
    like "2018", which otherwise inflates coverage with spurious year hits.
    """
    needle = keyword.casefold()
    if needle.isdigit():
        return re.search(rf"(?<!\d){re.escape(needle)}(?!\d)", folded_text) is not None
    return needle in folded_text


def keyword_coverage(text: str, keywords: list[str]) -> tuple[list[str], list[str], float]:
    folded = text.casefold()
    matched = [keyword for keyword in keywords if keyword_in_text(keyword, folded)]
    missing = [keyword for keyword in keywords if not keyword_in_text(keyword, folded)]
    coverage = len(matched) / len(keywords) if keywords else 1.0
    return matched, missing, coverage


def merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[list[int]] = []
    for start, end in sorted(ranges):
        if not merged or start > merged[-1][1] + 1:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(start, end) for start, end in merged]


def text_density(lines: list[str]) -> float:
    score = 0.0
    for line in lines:
        compact = line.strip()
        score += min(len(compact), 240) / 80
        if len(compact) < 12:
            score -= 0.4
        if re.search(r"[。！？.!?：:]", compact):
            score += 0.4
    return score


def keyword_extract(
    text: str, keywords: list[str], context: int, max_windows: int = 8
) -> tuple[str, int]:
    lines = text.splitlines()
    lowered = [line.casefold() for line in lines]
    hits = [
        index
        for index, line in enumerate(lowered)
        if any(keyword_in_text(keyword, line) for keyword in keywords)
    ]
    if not hits:
        return "", 0
    candidates = []
    for hit in hits:
        start = max(0, hit - context)
        end = min(len(lines), hit + context + 1)
        window_lines = lines[start:end]
        keyword_variety = sum(
            1
            for keyword in keywords
            if any(keyword_in_text(keyword, line) for line in lowered[start:end])
        )
        score = text_density(window_lines) + keyword_variety * 2
        total_chars = sum(len(line.strip()) for line in window_lines)
        longest_line = max((len(line.strip()) for line in window_lines), default=0)
        rich_text = longest_line >= 60 or total_chars >= 200
        candidates.append((score, start, end, rich_text))
    rich_candidates = [candidate for candidate in candidates if candidate[3]]
    ranked = rich_candidates or candidates
    selected: list[tuple[int, int]] = []
    for _, start, end, _ in sorted(ranked, reverse=True):
        if any(not (end < old_start or start > old_end) for old_start, old_end in selected):
            continue
        selected.append((start, end))
        if len(selected) >= max_windows:
            break
    ranges = merge_ranges(selected)
    chunks = ["\n".join(lines[start:end]).strip() for start, end in ranges]
    return "\n\n...\n\n".join(chunk for chunk in chunks if chunk), len(hits)


def dense_extract(text: str, max_lines: int = 100) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    scores = []
    nav_terms = {"navigation", "\u641c\u7d22...", "home page", "\u8df3\u8f6c\u5230\u4e3b\u8981\u5185\u5bb9", "\u590d\u5236\u9875\u9762"}
    for line in lines:
        compact = line.strip()
        score = min(len(compact), 240) / 80
        if compact.casefold() in nav_terms:
            score -= 4
        if len(compact) < 12:
            score -= 0.5
        if re.search(r"[。！？.!?：:]", compact):
            score += 0.4
        scores.append(score)
    window = min(max_lines, len(lines))
    running = sum(scores[:window])
    best_score = running
    best_start = 0
    for start in range(1, len(lines) - window + 1):
        running += scores[start + window - 1] - scores[start - 1]
        if running > best_score:
            best_score = running
            best_start = start
    return "\n".join(lines[best_start : best_start + window]).strip()


def limit_text(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars].rstrip() + "\n...[truncated]", True


def is_sparse_extract(hits: int, extracted_chars: int, source_chars: int) -> bool:
    """Detect many keyword matches within a small extract.

    This pattern is typical of table or matrix pages
    whose short cell lines are mostly dropped by window selection."""
    return hits >= 10 and source_chars > 0 and extracted_chars < source_chars * 0.25


def normalized_results(response: dict[str, Any]) -> list[dict[str, str]]:
    results = []
    seen = set()
    for item in response.get("SearchResult") or []:
        original = str(item.get("Url") or "").strip()
        if not original:
            continue
        try:
            normalized_url = normalize_url(original)
        except DtsError:
            continue
        key = normalized_url.casefold()
        if key in seen:
            continue
        seen.add(key)
        results.append(
            {
                "title": clean_text(item.get("Title")),
                "url": normalized_url,
                "domain": urlsplit(normalized_url).hostname or "",
                "snippet": clean_text(item.get("Snippet")),
            }
        )
    return results


def fetch_one(
    url: str,
    output_format: str,
    keywords: list[str],
    context: int,
    max_chars: int,
    full: bool,
) -> dict[str, Any]:
    target_url = prepare_fetch_url(url)
    response = request(
        "WebFetch",
        {"RegionId": REGION, "Url": target_url, "OutputFormat": output_format},
    )
    content = clean_text(response.get("Content"))
    if is_garbled(content):
        raise DtsError(f"Fetched content appears empty or garbled: {target_url}")
    title = clean_text(response.get("Title"))
    warnings = []
    quality_flags = []
    if looks_like_error_page(title):
        warnings.append(
            "Page title indicates an error page; do not cite this content as evidence."
        )
        quality_flags.append("error_page")
    hits = 0
    matched_keywords, missing_keywords, coverage = keyword_coverage(content, keywords)
    if full:
        extracted = content
    elif keywords:
        extracted, hits = keyword_extract(content, keywords, context)
        if not extracted:
            extracted = dense_extract(content)
            warnings.append(
                "No requested keywords were found; showing the densest text window."
            )
            quality_flags.append("no_keyword_matches")
    else:
        extracted = dense_extract(content)
    extracted, truncated = limit_text(extracted, max_chars)
    if not full and is_sparse_extract(hits, len(extracted), len(content)):
        warnings.append(
            "Keyword hits are spread across the page but the extract covers a small "
            "share; use --full or --format markdown to inspect structured content."
        )
        quality_flags.append("sparse_extract")
    if response.get("UrlType") == "dynamic_js":
        warnings.append("Page requires JavaScript; fetched content may be incomplete.")
        quality_flags.append("dynamic_js")
    if len(content) < MIN_CONTENT_CHARS:
        warnings.append(
            f"Fetched content is short ({len(content)} characters); extraction may be incomplete."
        )
        quality_flags.append("short_content")
    if keywords and coverage < 0.5:
        warnings.append(
            f"Low keyword coverage ({len(matched_keywords)}/{len(keywords)}); "
            "the page may not answer the research checklist."
        )
        quality_flags.append("low_keyword_coverage")
    elif missing_keywords:
        warnings.append(
            f"Some requested keywords were not found "
            f"({len(matched_keywords)}/{len(keywords)} matched)."
        )
        quality_flags.append("partial_keyword_coverage")
    if truncated:
        warnings.append("Extracted content was truncated at the configured character limit.")
        quality_flags.append("truncated")
    return {
        "title": title,
        "url": safe_output_url(str(response.get("Url") or target_url)),
        "url_type": str(response.get("UrlType") or "unknown"),
        "content_format": str(response.get("ContentFormat") or output_format),
        "keyword_hits": hits,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "keyword_coverage": round(coverage, 3),
        "source_chars": len(content),
        "extracted_chars": len(extracted),
        "quality_flags": quality_flags,
        "truncated": truncated,
        "warning": " ".join(warnings),
        "content": extracted,
    }


def print_search(results: list[dict[str, str]], summary: str) -> None:
    for index, item in enumerate(results, 1):
        print(f"[{index}] {item['title'] or '(untitled)'}")
        print(f"Domain: {item['domain']}")
        print(f"URL: {item['url']}")
        if item["snippet"]:
            print(f"Snippet: {item['snippet']}")
        print()
    print(summary)


def print_fetch(item: dict[str, Any], index: Optional[int] = None) -> None:
    prefix = f"SOURCE {index}: " if index is not None else ""
    print(f"{prefix}{item['title'] or '(untitled)'}")
    print(f"URL: {item['url']}")
    print(f"Type: {item['url_type']} | Format: {item['content_format']}")
    print(
        f"Extracted: {item['extracted_chars']}/{item['source_chars']} chars"
        f" ({item['extracted_chars'] / item['source_chars']:.0%} of page)"
        if item["source_chars"]
        else "Extracted: 0/0 chars"
    )
    if item["matched_keywords"] or item["missing_keywords"]:
        matched = len(item["matched_keywords"])
        total = matched + len(item["missing_keywords"])
        print(f"Keyword coverage: {matched}/{total} ({item['keyword_coverage']:.0%})")
        if item["missing_keywords"]:
            print(f"Missing keywords: {', '.join(item['missing_keywords'])}")
    if item["keyword_hits"]:
        print(f"Keyword hits: {item['keyword_hits']}")
    if item["warning"]:
        print(f"Warning: {item['warning']}")
    print("CONTENT:")
    print(item["content"])


def add_fetch_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=("text", "markdown", "html"), default="text")
    parser.add_argument("--keywords", help="Comma-separated terms used for semantic extraction")
    parser.add_argument("--context-lines", type=int, default=4)
    parser.add_argument("--max-chars", type=int, default=12000)
    parser.add_argument("--full", action="store_true", help="Return content from the beginning")
    parser.add_argument("--json", action="store_true", help="Write normalized JSON")


def search_summary(shown: int, fetched: int) -> str:
    """Append a final line that reports displayed and service result counts."""
    return f"-- {shown} result(s); service returned {fetched}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check", help="Check that DTS_AI_API_KEY is configured")

    setup_parser = subparsers.add_parser(
        "setup",
        help="Open the system browser to configure DTS_AI_API_KEY locally",
    )
    setup_parser.add_argument(
        "--language",
        choices=dts_api_key_configuration.SUPPORTED_LANGUAGES,
        default="en",
        help="local browser page language (default: en)",
    )

    search = subparsers.add_parser("search", help="Search public webpages")
    search.add_argument("query")
    search.add_argument("--max-results", type=int, default=10)
    search.add_argument("--json", action="store_true", help="Write normalized JSON")

    fetch = subparsers.add_parser("fetch", help="Fetch and extract one webpage")
    fetch.add_argument("url")
    add_fetch_options(fetch)

    fetch_many = subparsers.add_parser(
        "fetch-many", help=f"Fetch 2-{MAX_FETCH_PAGES} webpages concurrently"
    )
    fetch_many.add_argument("urls", nargs="+")
    fetch_many.add_argument("--workers", type=int, default=3)
    add_fetch_options(fetch_many)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "check":
            require_environment()
            print("DTS-AI API key configuration check passed.")
            return 0

        if args.command == "setup":
            try:
                dts_api_key_configuration.run_setup(language=args.language)
            except dts_api_key_configuration.SetupError as exc:
                raise ValidationError(str(exc)) from exc
            return 0

        if args.command == "search":
            if not 1 <= args.max_results <= 50:
                raise DtsError("--max-results must be between 1 and 50")
            response = request(
                "WebSearch",
                {"RegionId": REGION, "Query": args.query, "MaxResults": args.max_results},
            )
            fetched = normalized_results(response)
            results = fetched[: args.max_results]
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                print_search(results, search_summary(len(results), len(fetched)))
            return 0

        keywords = parse_keywords(args.keywords)
        if args.context_lines < 0 or args.max_chars < 100:
            raise DtsError("--context-lines must be non-negative and --max-chars at least 100")

        if args.command == "fetch":
            item = fetch_one(
                args.url,
                args.format,
                keywords,
                args.context_lines,
                args.max_chars,
                args.full,
            )
            if args.json:
                print(json.dumps(item, ensure_ascii=False, indent=2))
            else:
                print_fetch(item)
            return 0

        if not 2 <= len(args.urls) <= MAX_FETCH_PAGES:
            raise DtsError(f"fetch-many requires 2 to {MAX_FETCH_PAGES} URLs")
        workers = max(1, min(args.workers, 4, len(args.urls)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(
                    fetch_one,
                    url,
                    args.format,
                    keywords,
                    args.context_lines,
                    args.max_chars,
                    args.full,
                )
                for url in args.urls
            ]
            items = []
            errors = []
            for url, future in zip(args.urls, futures):
                try:
                    items.append(future.result())
                except DtsError as exc:
                    errors.append({"url": safe_output_url(url), "error": str(exc)})
        if args.json:
            print(json.dumps({"results": items, "errors": errors}, ensure_ascii=False, indent=2))
        else:
            for index, item in enumerate(items, 1):
                if index > 1:
                    print("\n---\n")
                print_fetch(item, index)
            for error in errors:
                print(f"\nFAILED: {error['url']}\n{error['error']}", file=sys.stderr)
        return 0 if items else 3
    except KeyboardInterrupt:
        return 130
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except DtsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
