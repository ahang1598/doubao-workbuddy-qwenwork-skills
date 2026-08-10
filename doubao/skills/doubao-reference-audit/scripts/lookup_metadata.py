#!/usr/bin/env python3
"""Retrieve Crossref metadata candidates without making audit judgments."""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import difflib
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_BASE = "https://api.crossref.org"
SKIP_TYPES = {"arxiv", "code", "dataset", "preprint", "repository", "software", "web", "webpage", "website"}
RETRYABLE_HTTP = {429, 500, 502, 503, 504}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_doi(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text, flags=re.I)
    text = re.sub(r"^doi\s*:\s*", "", text, flags=re.I)
    return text.strip().rstrip(".,;").lower()


def normalize_text(value: Any) -> str:
    text = html.unescape(str(value or "")).lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def first_value(value: Any) -> Any:
    return value[0] if isinstance(value, list) and value else value


def extract_year(item: dict[str, Any]) -> int | None:
    for field in ("issued", "published-print", "published-online", "posted"):
        parts = item.get(field, {}).get("date-parts", [])
        if parts and parts[0]:
            try:
                return int(parts[0][0])
            except (TypeError, ValueError):
                pass
    return None


def extract_authors(item: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "given": str(author.get("given", "")),
            "family": str(author.get("family", "")),
            "orcid": str(author.get("ORCID", "")),
        }
        for author in (item.get("author", []) or [])
    ]


def candidate_from_item(item: dict[str, Any], query_text: str) -> dict[str, Any]:
    title = str(first_value(item.get("title")) or "")
    left, right = normalize_text(query_text), normalize_text(title)
    similarity = round(difflib.SequenceMatcher(None, left, right).ratio(), 4) if left and right else None
    return {
        "title": title,
        "authors": extract_authors(item),
        "year": extract_year(item),
        "container_title": str(first_value(item.get("container-title")) or ""),
        "publisher": item.get("publisher"),
        "type": item.get("type"),
        "volume": item.get("volume"),
        "issue": item.get("issue"),
        "page": item.get("page"),
        "article_number": item.get("article-number"),
        "doi": item.get("DOI"),
        "url": item.get("URL"),
        "crossref_score": item.get("score"),
        "title_similarity": similarity,
        "update_to": item.get("update-to", []),
        "relation": item.get("relation", {}),
    }


def request_json(url: str, timeout: float, retries: int, user_agent: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": user_agent})
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in RETRYABLE_HTTP or attempt >= retries:
                raise
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt >= retries:
                raise
        time.sleep(2**attempt)
    if last_error:
        raise last_error
    raise RuntimeError("Crossref request failed without an error")


def build_query(entry: dict[str, Any], rows: int, mailto: str) -> dict[str, str]:
    doi = normalize_doi(entry.get("doi"))
    if doi:
        params = {"mailto": mailto} if mailto else {}
        suffix = f"?{urllib.parse.urlencode(params)}" if params else ""
        return {
            "key": f"doi:{doi}",
            "query_type": "doi",
            "query": doi,
            "url": f"{API_BASE}/works/{urllib.parse.quote(doi, safe='')}{suffix}",
        }
    raw = str(entry.get("raw") or entry.get("reference") or entry.get("citation") or "")
    title = str(entry.get("title") or "")
    author = str(entry.get("author") or entry.get("first_author") or "")
    year = str(entry.get("year") or "")
    if title:
        params: dict[str, Any] = {"query.title": title, "rows": rows}
        if author:
            params["query.author"] = author
        query = title
        query_type = "title"
        identity = "|".join((normalize_text(title), normalize_text(author), normalize_text(year)))
        key = f"title:{hashlib.sha256(identity.encode('utf-8')).hexdigest()}"
    else:
        query = raw
        params = {"query.bibliographic": query, "rows": rows}
        query_type = "bibliographic"
        key = f"bib:{hashlib.sha256(normalize_text(query).encode('utf-8')).hexdigest()}"
    if mailto:
        params["mailto"] = mailto
    return {
        "key": key,
        "query_type": query_type,
        "query": query,
        "match_text": title or query,
        "url": f"{API_BASE}/works?{urllib.parse.urlencode(params)}",
    }


def safe_request_url(url: str) -> str:
    """Remove contact email parameters before persisting request provenance."""
    parts = urllib.parse.urlsplit(url)
    query = [(key, value) for key, value in urllib.parse.parse_qsl(parts.query) if key.lower() != "mailto"]
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(query), parts.fragment))

def lookup_query(query: dict[str, str], timeout: float, retries: int, user_agent: str) -> dict[str, Any]:
    try:
        payload = request_json(query["url"], timeout, retries, user_agent)
        message = payload.get("message", {})
        items = [message] if query["query_type"] == "doi" and message else message.get("items", [])
        comparison_text = "" if query["query_type"] == "doi" else query.get("match_text", query["query"])
        candidates = [candidate_from_item(item, comparison_text) for item in items if isinstance(item, dict)]
        return {
            "status": "ok" if candidates else "not_found",
            "query_type": query["query_type"],
            "query": query["query"],
            "request_url": safe_request_url(query["url"]),
            "candidates": candidates,
            "error": None,
        }
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {
                "status": "not_found",
                "query_type": query["query_type"],
                "query": query["query"],
                "request_url": safe_request_url(query["url"]),
                "candidates": [],
                "error": None,
            }
        error = f"HTTP {exc.code}: {exc.reason}"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    return {
        "status": "request_failed",
        "query_type": query["query_type"],
        "query": query["query"],
        "request_url": safe_request_url(query["url"]),
        "candidates": [],
        "error": error,
    }


def read_references(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        data = data.get("references")
    if not isinstance(data, list):
        raise ValueError("Input must be a JSON list or an object with a 'references' list")
    references: list[dict[str, Any]] = []
    for index, item in enumerate(data, 1):
        if not isinstance(item, dict):
            raise ValueError(f"Reference #{index} is not a JSON object")
        entry = dict(item)
        entry.setdefault("id", str(index))
        references.append(entry)
    return references


def read_cache(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict) and isinstance(data.get("entries"), dict):
                return data
        except (OSError, json.JSONDecodeError):
            pass
    return {"version": 1, "entries": {}}


def write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def decorate_result(entry: dict[str, Any], base: dict[str, Any], from_cache: bool) -> dict[str, Any]:
    return {
        "id": str(entry.get("id", "")),
        "raw": entry.get("raw") or entry.get("reference") or entry.get("citation"),
        "input_title": entry.get("title"),
        "input_doi": entry.get("doi"),
        "from_cache": from_cache,
        **copy.deepcopy(base),
    }


def make_document(input_path: Path, results: list[dict[str, Any] | None], cache_path: Path) -> dict[str, Any]:
    completed = [result for result in results if result is not None]
    counts = Counter(str(result.get("status")) for result in completed)
    return {
        "tool": "doubao-reference-audit Crossref metadata lookup",
        "generated_at": utc_now(),
        "input": str(input_path),
        "cache": str(cache_path),
        "summary": {
            "total": len(results),
            "completed": len(completed),
            "pending": len(results) - len(completed),
            "by_status": dict(sorted(counts.items())),
            "network_requests": len({r.get("request_url") for r in completed if not r.get("from_cache") and r.get("request_url")}),
            "cache_hits": sum(1 for r in completed if r.get("from_cache")),
        },
        "results": completed,
        "notice": "Metadata candidates are leads only. The agent must verify the match and semantic support independently.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrieve and cache Crossref metadata candidates.")
    parser.add_argument("input", type=Path, help="UTF-8 JSON reference list")
    parser.add_argument("--output", type=Path, required=True, help="Result JSON path")
    parser.add_argument("--cache", type=Path, help="Task-local cache path")
    parser.add_argument("--mailto", default=os.environ.get("CROSSREF_MAILTO", ""), help="Crossref contact email")
    parser.add_argument("--rows", type=int, default=3, help="Candidates per search (1-5)")
    parser.add_argument("--workers", type=int, default=3, help="Concurrent requests (1-5)")
    parser.add_argument("--timeout", type=float, default=15.0, help="Request timeout seconds")
    parser.add_argument("--retries", type=int, default=1, help="Transient retries (0-3)")
    args = parser.parse_args()

    if not 1 <= args.rows <= 5:
        parser.error("--rows must be between 1 and 5")
    if not 1 <= args.workers <= 5:
        parser.error("--workers must be between 1 and 5")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if not 0 <= args.retries <= 3:
        parser.error("--retries must be between 0 and 3")

    input_path, output_path = args.input.resolve(), args.output.resolve()
    cache_path = args.cache.resolve() if args.cache else output_path.parent / "crossref-cache.json"
    references = read_references(input_path)
    cache = read_cache(cache_path)
    cache_entries: dict[str, Any] = cache["entries"]
    results: list[dict[str, Any] | None] = [None] * len(references)
    pending: dict[str, dict[str, str]] = {}
    positions: dict[str, list[int]] = {}

    for index, entry in enumerate(references):
        doi = normalize_doi(entry.get("doi"))
        entry_type = normalize_text(entry.get("type")).replace(" ", "_")
        raw = entry.get("raw") or entry.get("reference") or entry.get("citation")
        title = entry.get("title")
        if not doi and entry_type in SKIP_TYPES and not entry.get("force_crossref"):
            results[index] = decorate_result(entry, {
                "status": "official_source_preferred", "query_type": "none", "query": None,
                "request_url": None, "candidates": [], "error": None,
                "note": "No DOI supplied; verify this source through its official repository or institution.",
            }, False)
            continue
        if not doi and not normalize_text(raw or title):
            results[index] = decorate_result(entry, {
                "status": "invalid_input", "query_type": "none", "query": None,
                "request_url": None, "candidates": [], "error": "A DOI, raw citation, or title is required",
            }, False)
            continue
        query = build_query(entry, args.rows, args.mailto)
        key = query["key"]
        positions.setdefault(key, []).append(index)
        cached = cache_entries.get(key)
        if isinstance(cached, dict) and isinstance(cached.get("result"), dict):
            results[index] = decorate_result(entry, cached["result"], True)
        else:
            pending.setdefault(key, query)

    user_agent = "DoubaoReferenceAudit/1.0" + (f" (mailto:{args.mailto})" if args.mailto else "")
    if not args.mailto:
        print("Warning: Crossref recommends --mailto or CROSSREF_MAILTO.", file=sys.stderr)

    def persist() -> None:
        cache["updated_at"] = utc_now()
        write_json_atomic(cache_path, cache)
        write_json_atomic(output_path, make_document(input_path, results, cache_path))

    persist()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_key = {
            executor.submit(lookup_query, query, args.timeout, args.retries, user_agent): key
            for key, query in pending.items()
        }
        for future in concurrent.futures.as_completed(future_to_key):
            key = future_to_key[future]
            base = future.result()
            if base["status"] in {"ok", "not_found"}:
                cache_entries[key] = {"saved_at": utc_now(), "result": base}
            for index in positions[key]:
                results[index] = decorate_result(references[index], base, False)
            persist()
            print(f"[{sum(r is not None for r in results)}/{len(results)}] {key} -> {base['status']}", file=sys.stderr)

    persist()
    summary = make_document(input_path, results, cache_path)["summary"]
    print(json.dumps(summary, ensure_ascii=False))
    return 2 if summary["by_status"].get("request_failed", 0) else (0 if summary["pending"] == 0 else 1)


if __name__ == "__main__":
    raise SystemExit(main())
