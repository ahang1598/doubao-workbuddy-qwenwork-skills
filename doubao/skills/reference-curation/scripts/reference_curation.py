#!/usr/bin/env python3
"""Normalize, enrich, verify and render academic references.

The implementation deliberately uses the Python standard library so the skill can run in a
fresh Codex workspace. Network providers return normalized records; they never write directly
over user data.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import html
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import certifi  # type: ignore
except ImportError:  # pragma: no cover - optional dependency in minimal Python installs
    certifi = None


DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.I)
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
REQUIRED_BY_TYPE = {
    "article": ["title", "authors", "year", "venue"],
    "book": ["title", "authors", "year"],
    "thesis": ["title", "authors", "year"],
    "conference": ["title", "authors", "year", "venue"],
    "report": ["title", "year"],
    "web": ["title", "url"],
    "dataset": ["title", "year"],
    "preprint": ["title", "authors", "year"],
    "standard": ["title", "year"],
}
TYPE_ALIASES = {
    "article-journal": "article",
    "journal-article": "article",
    "inproceedings": "conference",
    "proceedings": "conference",
    "conference-paper": "conference",
    "incollection": "book",
    "inbook": "book",
    "phdthesis": "thesis",
    "mastersthesis": "thesis",
    "ph.d. dissertation": "thesis",
    "doctoral dissertation": "thesis",
    "master's thesis": "thesis",
    "masters thesis": "thesis",
    "硕士学位论文": "thesis",
    "博士学位论文": "thesis",
    "techreport": "report",
    "technical report": "report",
    "online": "web",
    "misc": "web",
}
FIELD_NAMES = ("title", "authors", "year", "venue", "volume", "issue", "pages", "doi", "url")
DRAFT_STYLES = ("gbt-article-draft", "apa-article-draft", "mla-article-draft")
ALLOWED_TYPES = set(REQUIRED_BY_TYPE)
ALLOWED_VERIFICATIONS = {"exact", "corroborated", "partial", "conflict", "unresolved", "rejected"}
ALLOWED_LANGUAGES = {"zh", "en", "other", "unknown"}
DRAFT_NOTICE = (
    "<!-- DRAFT ONLY: common journal-article preview; not a complete implementation of "
    "GB/T 7714, APA, or MLA. Verify with an authoritative style engine before submission. -->"
)


class ProviderError(RuntimeError):
    def __init__(self, provider: str, message: str, code: Optional[int] = None):
        super().__init__(message)
        self.provider = provider
        self.code = code


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def text(value: Any) -> Optional[str]:
    if value is None:
        return None
    value = html.unescape(str(value)).strip()
    return value or None


def normalize_doi(value: Any) -> Optional[str]:
    """Normalize a DOI without claiming that it resolves."""
    value = text(value)
    if not value:
        return None
    value = re.sub(r"^\s*(?:doi\s*:\s*)", "", value, flags=re.I)
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.I)
    value = value.strip().strip("<>[]{}\"'")
    value = re.sub(r"[\s\u00a0]+", "", value)
    value = value.rstrip(".,;:。；，、)]}")
    return value.lower() if DOI_RE.match(value) else None


def clean_title(value: Any) -> str:
    value = text(value) or ""
    value = re.sub(r"[\s\u00a0]+", " ", value)
    return value.strip(" \t\r\n.,;:。；，、")


def normalize_title(value: Any) -> str:
    return re.sub(r"[^0-9a-z\u3400-\u9fff]+", "", clean_title(value).lower())


def normalize_type(value: Any) -> str:
    raw = (text(value) or "article").lower()
    return TYPE_ALIASES.get(raw, raw)


def parse_year(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        year = int(value)
        return year if 1000 <= year <= 9999 else None
    match = re.search(r"\b(1[5-9]\d{2}|20\d{2}|21\d{2})\b", str(value))
    return int(match.group(1)) if match else None


def parse_date_parts(value: Any) -> Optional[int]:
    if not isinstance(value, dict):
        return parse_year(value)
    parts = value.get("date-parts") or value.get("dateParts")
    if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
        return parse_year(parts[0][0])
    return parse_year(value.get("year"))


def normalize_author(value: Any) -> Dict[str, Optional[str]]:
    if isinstance(value, dict):
        raw = text(value.get("raw") or value.get("name") or value.get("literal"))
        family = text(value.get("family") or value.get("familyName"))
        given = text(value.get("given") or value.get("givenName"))
        if not raw:
            raw = " ".join(part for part in (given, family) if part) or None
        return {"family": family, "given": given, "raw": raw}
    raw = text(value)
    if not raw:
        return {"family": None, "given": None, "raw": None}
    if "," in raw:
        family, given = (part.strip() for part in raw.split(",", 1))
        return {"family": family or None, "given": given or None, "raw": raw}
    return {"family": None, "given": None, "raw": raw}


def normalize_authors(value: Any) -> List[Dict[str, Optional[str]]]:
    if value is None:
        return []
    if isinstance(value, str):
        # BibTeX convention; a Chinese author name containing "and" is exceedingly unlikely,
        # but preserve the raw item rather than trying to infer a family/given split.
        values = [part.strip() for part in re.split(r"\s+and\s+|\s*;\s*|\s*；\s*", value) if part.strip()]
    elif isinstance(value, (list, tuple)):
        values = list(value)
    else:
        values = [value]
    normalized = []
    for item in values:
        author = normalize_author(item)
        if author.get("raw"):
            normalized.append(author)
    return normalized


def is_chinese_record(record: Dict[str, Any]) -> bool:
    if str(record.get("language") or "").lower() in {"zh", "zh-cn", "中文", "chinese"}:
        return True
    return bool(CJK_RE.search(" ".join(str(record.get(field) or "") for field in ("title", "venue"))))


def normalize_record(raw: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
    record = dict(raw or {})
    record["id"] = text(record.get("id")) or f"ref-{index + 1:04d}"
    record["type"] = normalize_type(record.get("type"))
    record["title"] = clean_title(record.get("title")) or None
    record["authors"] = normalize_authors(record.get("authors") or record.get("author"))
    record["year"] = parse_year(record.get("year") or record.get("published"))
    for field in ("venue", "volume", "issue", "pages", "url"):
        record[field] = text(record.get(field))
    record["doi"] = normalize_doi(record.get("doi") or record.get("DOI"))
    language = text(record.get("language"))
    record["language"] = language.lower() if language else ("zh" if is_chinese_record(record) else "unknown")
    record["source_evidence"] = list(record.get("source_evidence") or [])
    record["conflicts"] = list(record.get("conflicts") or [])
    record["warnings"] = list(record.get("warnings") or [])
    record["candidates"] = list(record.get("candidates") or [])
    record["verification"] = text(record.get("verification")) or "unresolved"
    record["missing_fields"] = missing_fields(record)
    return record


def missing_fields(record: Dict[str, Any]) -> List[str]:
    required = REQUIRED_BY_TYPE.get(record.get("type"), REQUIRED_BY_TYPE["article"])
    missing: List[str] = []
    for field in required:
        value = record.get(field)
        if field == "authors":
            if not value:
                missing.append(field)
        elif value is None or value == "":
            missing.append(field)
    # DOI is not required for every source, but it is important to surface it when absent.
    if record.get("type") in {"article", "conference", "thesis", "report", "dataset", "preprint"} and not record.get("doi"):
        missing.append("doi")
    return list(dict.fromkeys(missing))


def schema_issues(record: Dict[str, Any]) -> List[Dict[str, str]]:
    """Validate the deterministic contract in assets/reference-record.schema.json."""
    issues: List[Dict[str, str]] = []
    if not isinstance(record, dict):
        return [{"field": "$", "issue": "not_object"}]
    for field in ("id", "type", "title", "authors", "language", "verification", "missing_fields"):
        if field not in record:
            issues.append({"field": field, "issue": "required"})
    if not isinstance(record.get("id"), str) or not record.get("id", "").strip():
        issues.append({"field": "id", "issue": "nonempty_string_required"})
    if record.get("type") not in ALLOWED_TYPES:
        issues.append({"field": "type", "issue": "invalid_enum"})
    if record.get("language") not in ALLOWED_LANGUAGES:
        issues.append({"field": "language", "issue": "invalid_enum"})
    if record.get("verification") not in ALLOWED_VERIFICATIONS:
        issues.append({"field": "verification", "issue": "invalid_enum"})
    if record.get("title") is not None and not isinstance(record.get("title"), str):
        issues.append({"field": "title", "issue": "string_or_null_required"})
    if not isinstance(record.get("authors"), list):
        issues.append({"field": "authors", "issue": "array_required"})
    else:
        for index, author in enumerate(record["authors"]):
            if not isinstance(author, dict):
                issues.append({"field": f"authors[{index}]", "issue": "object_required"})
    if record.get("year") is not None and (not isinstance(record.get("year"), int) or isinstance(record.get("year"), bool)):
        issues.append({"field": "year", "issue": "integer_or_null_required"})
    for field in ("venue", "volume", "issue", "pages", "doi", "url"):
        if record.get(field) is not None and not isinstance(record.get(field), str):
            issues.append({"field": field, "issue": "string_or_null_required"})
    for field in ("source_evidence", "missing_fields", "conflicts", "warnings"):
        if field in record and not isinstance(record.get(field), list):
            issues.append({"field": field, "issue": "array_required"})
    return issues


def parse_bibtex(text_value: str) -> List[Dict[str, Any]]:
    """Parse common BibTeX entries without evaluating macros or executing TeX."""
    entries: List[Dict[str, Any]] = []
    start_re = re.compile(r"@([A-Za-z]+)\s*([{(])")
    cursor = 0
    while True:
        match = start_re.search(text_value, cursor)
        if not match:
            break
        opening = match.end() - 1
        closing = "}" if text_value[opening] == "{" else ")"
        depth = 0
        in_quote = False
        escaped = False
        end = None
        for pos in range(opening, len(text_value)):
            char = text_value[pos]
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"':
                in_quote = not in_quote
            if in_quote:
                continue
            if char == text_value[opening]:
                depth += 1
            elif char == closing:
                depth -= 1
                if depth == 0:
                    end = pos
                    break
        if end is None:
            break
        body = text_value[match.end():end]
        comma = body.find(",")
        if comma < 0:
            cursor = end + 1
            continue
        key = body[:comma].strip()
        fields = _parse_bib_fields(body[comma + 1:])
        # Keep the BibTeX entry type separate: a legitimate `type = {...}` field must not
        # overwrite `@phdthesis`, `@mastersthesis`, or another entry kind.
        item: Dict[str, Any] = {"id": key, "_bibtex_type": match.group(1).lower()}
        item.update(fields)
        entries.append(_bib_to_record(item))
        cursor = end + 1
    return entries


def _parse_bib_fields(body: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    pos = 0
    while pos < len(body):
        match = re.search(r"([A-Za-z][A-Za-z0-9_-]*)\s*=\s*", body[pos:])
        if not match:
            break
        name = match.group(1).lower()
        value_start = pos + match.end()
        if value_start >= len(body):
            break
        if body[value_start] == "{":
            depth = 1
            end = value_start + 1
            while end < len(body) and depth:
                if body[end] == "{" and (end == 0 or body[end - 1] != "\\"):
                    depth += 1
                elif body[end] == "}" and (end == 0 or body[end - 1] != "\\"):
                    depth -= 1
                end += 1
            value = body[value_start + 1:end - 1]
        elif body[value_start] == '"':
            end = value_start + 1
            while end < len(body):
                if body[end] == '"' and body[end - 1] != "\\":
                    break
                end += 1
            value = body[value_start + 1:end]
            end += 1
        else:
            end = body.find(",", value_start)
            if end < 0:
                end = len(body)
            value = body[value_start:end]
        fields[name] = value.strip()
        pos = body.find(",", end) + 1 if body.find(",", end) >= 0 else len(body)
    return fields


def _bib_to_record(item: Dict[str, Any]) -> Dict[str, Any]:
    entry_type = normalize_type(item.get("_bibtex_type") or item.get("type"))
    original = {key: value for key, value in item.items() if key != "_bibtex_type"}
    original["bibtex_entry_type"] = text(item.get("_bibtex_type")) or entry_type
    return {
        "id": item.get("id"),
        "type": entry_type,
        "title": item.get("title"),
        "authors": item.get("author"),
        "year": item.get("year"),
        "venue": (
            item.get("journal")
            or item.get("booktitle")
            or item.get("school")
            or item.get("institution")
            or item.get("publisher")
        ),
        "volume": item.get("volume"),
        "issue": item.get("number") or item.get("issue"),
        "pages": item.get("pages"),
        "doi": item.get("doi"),
        "url": item.get("url"),
        "language": item.get("language"),
        "original": original,
    }


def load_records(path: str, normalize: bool = True) -> List[Dict[str, Any]]:
    source = Path(path)
    raw = source.read_text(encoding="utf-8")
    if source.suffix.lower() in {".bib", ".bibtex"}:
        values = parse_bibtex(raw)
    else:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                values = parsed.get("references") or parsed.get("items") or [parsed]
            else:
                values = parsed
        except json.JSONDecodeError:
            values = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if not isinstance(values, list):
        raise ValueError("输入必须是 JSON 数组、JSONL、BibTeX 或包含 references/items 的 JSON 对象")
    items = [item for item in values if isinstance(item, dict)]
    return [normalize_record(item, index) for index, item in enumerate(items)] if normalize else items


def write_records(path: str, records: Sequence[Dict[str, Any]], json_array: bool = False) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        if json_array or destination.suffix.lower() == ".json":
            json.dump(list(records), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        else:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def _json_request(method: str, url: str, params: Optional[Dict[str, Any]] = None,
                  body: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None,
                  timeout: int = 20, retries: int = 2) -> Any:
    if params:
        url = f"{url}{'&' if '?' in url else '?'}{urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})}"
    request_headers = {"Accept": "application/json", "User-Agent": "reference-curation/0.1"}
    request_headers.update(headers or {})
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    ca_file = os.environ.get("SSL_CERT_FILE") or (certifi.where() if certifi else None)
    ssl_context = ssl.create_default_context(cafile=ca_file) if ca_file else ssl.create_default_context()
    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(url, data=payload, headers=request_headers, method=method)
            with urllib.request.urlopen(request, timeout=timeout, context=ssl_context) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = ProviderError("http", f"HTTP {exc.code} for {url}", exc.code)
            if exc.code not in {408, 425, 429} and exc.code < 500:
                break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
        if attempt < retries:
            time.sleep(min(2 ** attempt, 4))
    raise last_error or RuntimeError(f"request failed: {url}")


def _date_year(value: Any) -> Optional[int]:
    if isinstance(value, dict):
        return parse_date_parts(value)
    return parse_year(value)


def _first(value: Any) -> Any:
    return value[0] if isinstance(value, list) and value else value


def crossref_record(message: Dict[str, Any], provider: str = "crossref") -> Dict[str, Any]:
    authors = []
    for author in message.get("author") or []:
        if not isinstance(author, dict):
            continue
        authors.append(normalize_author(author))
    title = _first(message.get("title"))
    return {
        "type": "article" if str(message.get("type") or "").startswith("journal") else (message.get("type") or "article"),
        "title": clean_title(title),
        "authors": authors,
        "year": _date_year(message.get("published-print")) or _date_year(message.get("published-online")) or _date_year(message.get("published")) or _date_year(message.get("issued")),
        "venue": text(_first(message.get("container-title"))),
        "volume": text(message.get("volume")),
        "issue": text(message.get("issue")),
        "pages": text(message.get("page")),
        "doi": normalize_doi(message.get("DOI")),
        "url": text(message.get("URL")),
        "language": text(message.get("language")),
        "_provider": provider,
    }


def datacite_record(attributes: Dict[str, Any], provider: str = "datacite") -> Dict[str, Any]:
    authors = []
    for creator in attributes.get("creators") or []:
        if isinstance(creator, dict):
            authors.append(normalize_author(creator.get("name") and {"name": creator.get("name"), **creator} or creator))
    titles = attributes.get("titles") or []
    title = _first(titles)
    if isinstance(title, dict):
        title = title.get("title")
    return {
        "type": "dataset" if str((attributes.get("types") or {}).get("resourceTypeGeneral") or "").lower() == "dataset" else "article",
        "title": clean_title(title),
        "authors": authors,
        "year": parse_year(attributes.get("publicationYear")) or _date_year(_first(attributes.get("dates"))),
        "venue": text(attributes.get("containerTitle") or attributes.get("publisher")),
        "volume": text(attributes.get("volume")),
        "issue": text(attributes.get("issue")),
        "pages": text(attributes.get("page")),
        "doi": normalize_doi(attributes.get("doi")),
        "url": text(attributes.get("url")),
        "_provider": provider,
    }


def openalex_record(item: Dict[str, Any]) -> Dict[str, Any]:
    location = item.get("primary_location") or {}
    source = location.get("source") or {}
    biblio = item.get("biblio") or {}
    authors = []
    for authorship in item.get("authorships") or []:
        author = (authorship or {}).get("author") or {}
        if author.get("display_name"):
            authors.append(normalize_author({"name": author.get("display_name")}))
    return {
        "type": "article",
        "title": clean_title(item.get("title")),
        "authors": authors,
        "year": parse_year(item.get("publication_year")),
        "venue": text(source.get("display_name")),
        "volume": text(biblio.get("volume")),
        "issue": text(biblio.get("issue")),
        "pages": (f"{biblio.get('first_page')}-{biblio.get('last_page')}" if biblio.get("first_page") and biblio.get("last_page") else text(biblio.get("first_page"))),
        "doi": normalize_doi(item.get("doi") or location.get("doi")),
        "url": text(item.get("id") or location.get("landing_page_url")),
        "_provider": "openalex",
    }


def _qinyan_items(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "results", "items", "papers", "records"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = _qinyan_items(value)
            if nested:
                return nested
    return [payload]


def _qinyan_author(value: Any) -> Any:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("name") or value.get("display_name") or value
    return value


def qinyan_record(item: Dict[str, Any]) -> Dict[str, Any]:
    nested = item.get("paper") if isinstance(item.get("paper"), dict) else item
    authors = nested.get("authors") or nested.get("author") or nested.get("creators") or []
    if isinstance(authors, str):
        authors = [authors]
    return {
        "type": "article",
        "title": clean_title(nested.get("title") or nested.get("title_zh") or nested.get("name")),
        "authors": normalize_authors([_qinyan_author(value) for value in authors]),
        "year": parse_year(nested.get("year") or nested.get("publication_year") or nested.get("publish_year")),
        "venue": text(nested.get("journal") or nested.get("venue") or nested.get("source") or nested.get("container_title")),
        "volume": text(nested.get("volume")),
        "issue": text(nested.get("issue") or nested.get("number")),
        "pages": text(nested.get("pages") or nested.get("page")),
        "doi": normalize_doi(nested.get("doi") or nested.get("DOI")),
        "url": text(nested.get("url") or nested.get("link")),
        "language": "zh",
        "_provider": "qinyan-wanfang",
    }


def title_similarity(left: Any, right: Any) -> float:
    a, b = normalize_title(left), normalize_title(right)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def author_similarity(left: Sequence[Dict[str, Any]], right: Sequence[Dict[str, Any]]) -> float:
    def tokens(values: Sequence[Dict[str, Any]]) -> set[str]:
        result = set()
        for author in values:
            raw = normalize_title(author.get("raw") or " ".join(filter(None, (author.get("family"), author.get("given")))))
            if raw:
                result.add(raw)
        return result
    a, b = tokens(left or []), tokens(right or [])
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, min(len(a), len(b)))


def candidate_score(base: Dict[str, Any], candidate: Dict[str, Any]) -> float:
    title = title_similarity(base.get("title"), candidate.get("title"))
    authors = author_similarity(base.get("authors") or [], candidate.get("authors") or [])
    byear, cyear = parse_year(base.get("year")), parse_year(candidate.get("year"))
    year = 1.0 if byear and cyear and abs(byear - cyear) <= 1 else (0.4 if not byear or not cyear else 0.0)
    return round(title * 0.7 + authors * 0.2 + year * 0.1, 4)


def _evidence(provider: str, locator: str, score: Optional[float] = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {"provider": provider, "locator": locator, "retrieved_at": utc_now()}
    if score is not None:
        result["match_score"] = score
    return result


def _same_value(field: str, left: Any, right: Any) -> bool:
    if field == "doi":
        return normalize_doi(left) == normalize_doi(right)
    if field == "year":
        return parse_year(left) == parse_year(right)
    if field == "title":
        return title_similarity(left, right) >= 0.96
    if field == "authors":
        return author_similarity(left or [], right or []) >= 0.75
    return re.sub(r"\s+", " ", str(left or "")).strip().lower() == re.sub(r"\s+", " ", str(right or "")).strip().lower()


def merge_record(base: Dict[str, Any], incoming: Dict[str, Any], provider: str, score: Optional[float] = None) -> None:
    for field in FIELD_NAMES:
        value = incoming.get(field)
        if field == "authors":
            value = normalize_authors(value)
        elif field == "doi":
            value = normalize_doi(value)
        elif field == "year":
            value = parse_year(value)
        elif field == "title":
            value = clean_title(value) or None
        else:
            value = text(value)
        if not value:
            continue
        if not base.get(field):
            base[field] = value
        elif not _same_value(field, base[field], value):
            base.setdefault("conflicts", []).append({
                "field": field,
                "existing": base[field],
                "incoming": value,
                "provider": provider,
            })
    evidence = incoming.get("_evidence") or _evidence(provider, incoming.get("_locator") or provider, score)
    base.setdefault("source_evidence", []).append(evidence)


class Provider:
    name = "provider"

    def exact(self, doi: str) -> Optional[Dict[str, Any]]:
        return None

    def search(self, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []


class CrossrefProvider(Provider):
    name = "crossref"

    def __init__(self, client: "HttpClient"):
        self.client = client

    def exact(self, doi: str) -> Optional[Dict[str, Any]]:
        url = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}"
        try:
            payload = self.client.get(url, headers={"Accept": "application/json"})
        except Exception as exc:
            raise ProviderError(self.name, str(exc), getattr(exc, "code", None)) from exc
        message = payload.get("message") if isinstance(payload, dict) else None
        return crossref_record(message, self.name) if isinstance(message, dict) else None

    def search(self, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        query = " ".join(part for part in (record.get("title"), first_author_text(record), str(record.get("year") or "")) if part)
        if not query:
            return []
        try:
            payload = self.client.get("https://api.crossref.org/works", params={"query.bibliographic": query, "rows": 5})
        except Exception as exc:
            raise ProviderError(self.name, str(exc), getattr(exc, "code", None)) from exc
        items = ((payload or {}).get("message") or {}).get("items") or []
        return [crossref_record(item, self.name) for item in items if isinstance(item, dict)]


class DataCiteProvider(Provider):
    name = "datacite"

    def __init__(self, client: "HttpClient"):
        self.client = client

    def exact(self, doi: str) -> Optional[Dict[str, Any]]:
        url = f"https://api.datacite.org/dois/{urllib.parse.quote(doi, safe='')}"
        try:
            payload = self.client.get(url)
        except Exception as exc:
            raise ProviderError(self.name, str(exc), getattr(exc, "code", None)) from exc
        data = (payload or {}).get("data") or {}
        attributes = data.get("attributes") if isinstance(data, dict) else None
        if not isinstance(attributes, dict):
            return None
        attributes = dict(attributes)
        attributes.setdefault("doi", data.get("id"))
        return datacite_record(attributes, self.name)


class OpenAlexProvider(Provider):
    name = "openalex"

    def __init__(self, client: "HttpClient"):
        self.client = client

    def search(self, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        query = " ".join(part for part in (record.get("title"), first_author_text(record)) if part)
        if not query:
            return []
        try:
            payload = self.client.get("https://api.openalex.org/works", params={"search": query, "per-page": 5})
        except Exception as exc:
            raise ProviderError(self.name, str(exc), getattr(exc, "code", None)) from exc
        items = (payload or {}).get("results") or []
        return [openalex_record(item) for item in items if isinstance(item, dict)]


class QinyanProvider(Provider):
    name = "qinyan-wanfang"

    def __init__(self, client: "HttpClient", api_key: str, source: str = "wanfang", base_url: str = "https://api.qinyanai.com"):
        self.client, self.api_key, self.source, self.base_url = client, api_key, source, base_url.rstrip("/")

    def search(self, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        query = " ".join(part for part in (record.get("title"), first_author_text(record), str(record.get("year") or "")) if part)
        if not query:
            return []
        url = f"{self.base_url}/v1/paper-search/{urllib.parse.quote(self.source, safe='')}"
        try:
            payload = self.client.post(url, {"query": query, "max_results": 5}, headers={"Authorization": f"Bearer {self.api_key}"})
        except Exception as exc:
            raise ProviderError(self.name, str(exc), getattr(exc, "code", None)) from exc
        return [qinyan_record(item) for item in _qinyan_items(payload)]


class HttpClient:
    def __init__(self, timeout: int = 20, retries: int = 2, mailto: Optional[str] = None):
        self.timeout, self.retries, self.mailto = timeout, retries, mailto

    def get(self, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Any:
        merged = dict(headers or {})
        if self.mailto and "api.crossref.org" in url:
            params = dict(params or {})
            params.setdefault("mailto", self.mailto)
        return _json_request("GET", url, params=params, headers=merged, timeout=self.timeout, retries=self.retries)

    def post(self, url: str, body: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Any:
        return _json_request("POST", url, body=body, headers=headers, timeout=self.timeout, retries=self.retries)


def first_author_text(record: Dict[str, Any]) -> Optional[str]:
    authors = record.get("authors") or []
    if not authors:
        return None
    author = authors[0]
    return text(author.get("raw") or author.get("family") or author.get("given")) if isinstance(author, dict) else text(author)


def _provider_candidates(record: Dict[str, Any], client: HttpClient, qinyan_key: Optional[str], qinyan_source: str,
                         qinyan_base: str) -> Tuple[List[Provider], bool]:
    chinese = is_chinese_record(record)
    qinyan_used = bool(chinese and qinyan_key)
    providers: List[Provider] = []
    if chinese and qinyan_key:
        providers.append(QinyanProvider(client, qinyan_key, qinyan_source, qinyan_base))
    providers.extend([CrossrefProvider(client), OpenAlexProvider(client)])
    return providers, qinyan_used


def enrich_record(record: Dict[str, Any], client: HttpClient, qinyan_key: Optional[str], qinyan_source: str,
                  qinyan_base: str = "https://api.qinyanai.com", require_chinese_provider: bool = False,
                  offline: bool = False) -> Dict[str, Any]:
    record = normalize_record(record)
    chinese = is_chinese_record(record)
    qinyan_available = bool(chinese and qinyan_key)
    exact_verified = False
    search_verified = False
    provider_errors: List[Dict[str, Any]] = []
    qinyan_accepted_count = 0
    qinyan_failed = False

    if offline:
        record.setdefault("warnings", []).append("offline_unverified")
        if chinese:
            record.setdefault("warnings", []).append("chinese_provider_missing")
            if require_chinese_provider:
                record.setdefault("warnings", []).append("chinese_provider_required")
        record["missing_fields"] = missing_fields(record)
        return record

    providers, _ = _provider_candidates(record, client, qinyan_key, qinyan_source, qinyan_base)
    crossref = next((provider for provider in providers if isinstance(provider, CrossrefProvider)), None)
    datacite = DataCiteProvider(client)

    doi = normalize_doi(record.get("doi"))
    if doi:
        record["doi"] = doi
        for provider in ([crossref, datacite] if crossref else [datacite]):
            try:
                result = provider.exact(doi) if provider else None
                if result:
                    incoming_doi = normalize_doi(result.get("doi"))
                    if incoming_doi == doi:
                        result["_evidence"] = _evidence(provider.name, f"doi:{doi}")
                        merge_record(record, result, provider.name)
                        exact_verified = True
                        break
            except ProviderError as exc:
                provider_errors.append({"provider": exc.provider, "code": exc.code, "message": str(exc)})
    else:
        all_candidates: List[Tuple[float, str, Dict[str, Any]]] = []
        for provider in providers:
            try:
                provider_results = provider.search(record)
                for candidate in provider_results:
                    score = candidate_score(record, candidate)
                    threshold = 0.72 if provider.name == "qinyan-wanfang" and chinese else 0.78
                    if score >= threshold:
                        candidate["_evidence"] = _evidence(provider.name, f"search:{provider.name}", score)
                        all_candidates.append((score, provider.name, candidate))
                        if provider.name == "qinyan-wanfang":
                            qinyan_accepted_count += 1
                    else:
                        record.setdefault("candidates", []).append({"provider": provider.name, "title": candidate.get("title"), "score": score})
            except ProviderError as exc:
                provider_errors.append({"provider": exc.provider, "code": exc.code, "message": str(exc)})
                if exc.provider == "qinyan-wanfang":
                    qinyan_failed = True
        if all_candidates:
            all_candidates.sort(key=lambda item: (item[0], 1 if chinese and item[1] == "qinyan-wanfang" else 0), reverse=True)
            score, provider_name, best = all_candidates[0]
            merge_record(record, best, provider_name, score)
            search_verified = True

    # A DOI found through a title search is always re-checked via an exact endpoint.
    if record.get("doi") and not exact_verified:
        for provider in ([crossref, datacite] if crossref else [datacite]):
            try:
                result = provider.exact(record["doi"]) if provider else None
                if result and normalize_doi(result.get("doi")) == record["doi"]:
                    result["_evidence"] = _evidence(provider.name, f"doi:{record['doi']}")
                    merge_record(record, result, provider.name)
                    exact_verified = True
                    break
            except ProviderError as exc:
                provider_errors.append({"provider": exc.provider, "code": exc.code, "message": str(exc)})

    if chinese and not qinyan_available:
        record.setdefault("warnings", []).append("chinese_provider_missing")
    elif chinese and not doi and qinyan_failed:
        record.setdefault("warnings", []).append("chinese_provider_unavailable")
    elif chinese and not doi and qinyan_available and qinyan_accepted_count == 0:
        record.setdefault("warnings", []).append("chinese_provider_no_match")
    if require_chinese_provider and chinese and not qinyan_available:
        record.setdefault("warnings", []).append("chinese_provider_required")
    if provider_errors:
        record["provider_errors"] = provider_errors

    if record.get("conflicts"):
        record["verification"] = "conflict"
    elif exact_verified:
        record["verification"] = "exact"
    elif search_verified:
        record["verification"] = "corroborated"
    elif record.get("source_evidence"):
        record["verification"] = "partial"
    else:
        record["verification"] = "unresolved"
    record["missing_fields"] = missing_fields(record)
    return record


def _author_label(author: Dict[str, Any], style: str) -> str:
    raw = text(author.get("raw"))
    family, given = text(author.get("family")), text(author.get("given"))
    if raw and not family and not given:
        return raw
    is_cjk_name = bool(CJK_RE.search(f"{family or ''}{given or ''}")) and not bool(re.search(r"[A-Za-z]", f"{family or ''}{given or ''}"))
    if style.startswith("gbt"):
        if is_cjk_name:
            return f"{family or ''}{given or ''}" or raw or "[缺失]"
        initials = _given_initials(given, periods=False)
        return " ".join(part for part in ((family or "").upper(), initials) if part) or raw or "[缺失]"
    if style == "apa-article-draft":
        if is_cjk_name:
            return f"{family or ''}{given or ''}" or raw or "[缺失]"
        initials = _given_initials(given, periods=True)
        return ", ".join(part for part in (family, initials) if part) or raw or "[缺失]"
    if is_cjk_name:
        return f"{family or ''}{given or ''}" or raw or "[缺失]"
    return ", ".join(part for part in (family, given) if part) or raw or "[缺失]"


def _given_initials(given: Optional[str], periods: bool) -> str:
    initials = []
    for token in re.split(r"[\s-]+", given or ""):
        letters = re.findall(r"[^\W\d_]", token, flags=re.UNICODE)
        if letters:
            initials.append(letters[0].upper() + ("." if periods else ""))
    return " ".join(initials)


def _authors(record: Dict[str, Any], style: str) -> str:
    values = [_author_label(author, style) for author in record.get("authors") or []]
    if not values:
        return "[缺失]"
    if style == "mla-article-draft":
        if len(values) == 1:
            return values[0]
        return values[0] + ", et al"
    if style == "apa-article-draft":
        if len(values) > 20:
            return ", ".join(values[:19]) + ", ... " + values[-1]
        if len(values) == 1:
            return values[0]
        if len(values) == 2:
            return " & ".join(values)
        return ", ".join(values[:-1]) + ", & " + values[-1]
    return ", ".join(values)


def _missing(value: Any) -> str:
    return str(value) if value not in (None, "", []) else "[缺失]"


def render_record(record: Dict[str, Any], style: str, number: int) -> str:
    if style not in DRAFT_STYLES:
        raise ValueError(f"不支持的草稿样式: {style}")
    if record.get("type") != "article":
        record_id = record.get("id") or f"ref-{number:04d}"
        return f"[需样式引擎] {record_id}: type={record.get('type') or 'unknown'} 不支持内置期刊条目草稿。"

    title, year, venue = _missing(record.get("title")), _missing(record.get("year")), _missing(record.get("venue"))
    authors = _authors(record, style)
    volume, issue, pages = _missing(record.get("volume")), _missing(record.get("issue")), _missing(record.get("pages"))
    doi = normalize_doi(record.get("doi"))
    doi_text = f" https://doi.org/{doi}" if doi else " [缺失 DOI]"
    if style == "gbt-article-draft":
        volume_issue = f"{volume}({issue})" if record.get("volume") and record.get("issue") else volume if record.get("volume") else issue if record.get("issue") else "[缺失卷期]"
        return f"[{number}] {authors}. {title}[J]. {venue}, {year}, {volume_issue}: {pages}." + (f" DOI: {doi}." if doi else " DOI: [缺失].")
    if style == "apa-article-draft":
        volume_issue = volume + (f"({record.get('issue')})" if record.get("issue") else "") if record.get("volume") else "[缺失卷期]"
        return f"{authors} ({year}). {title}. {venue}, {volume_issue}, {pages}." + (doi_text + "." if doi else "")
    if style == "mla-article-draft":
        volume_issue = f"vol. {volume}, no. {issue}" if record.get("volume") and record.get("issue") else f"vol. {volume}" if record.get("volume") else f"no. {issue}" if record.get("issue") else "[缺失卷期]"
        return f"{authors}. \"{title}.\" {venue}, {volume_issue}, {year}, pp. {pages}." + (doi_text + "." if doi else "")
    raise AssertionError("unreachable draft style")


def render_records(records: Sequence[Dict[str, Any]], style: str) -> str:
    entries = [render_record(normalize_record(record, index), style, index + 1) for index, record in enumerate(records)]
    return "\n\n".join([DRAFT_NOTICE, *entries]) + "\n"


def enrich(args: argparse.Namespace) -> int:
    records = load_records(args.input)
    # Credentials are process-environment/platform injected only; never accept a
    # secret as a command-line argument where shell history and process listings
    # could expose it.
    key = os.environ.get("QINYAN_API_KEY")
    qinyan_base = args.qinyan_base or os.environ.get("QINYAN_API_BASE", "https://api.qinyanai.com")
    client = HttpClient(timeout=args.timeout, retries=args.retries, mailto=args.mailto)
    offline = args.offline or not args.online
    result = [enrich_record(record, client, key, args.qinyan_source, qinyan_base, args.require_chinese_provider, offline) for record in records]
    write_records(args.output, result, args.json_array)
    summary = {
        "records": len(result),
        "exact": sum(item.get("verification") == "exact" for item in result),
        "corroborated": sum(item.get("verification") == "corroborated" for item in result),
        "partial": sum(item.get("verification") == "partial" for item in result),
        "conflict": sum(item.get("verification") == "conflict" for item in result),
        "unresolved": sum(item.get("verification") == "unresolved" for item in result),
        "chinese_provider_missing": sum("chinese_provider_missing" in item.get("warnings", []) for item in result),
        "chinese_provider_unavailable": sum(any(code in item.get("warnings", []) for code in ("chinese_provider_unavailable", "chinese_provider_no_match")) for item in result),
    }
    print(json.dumps(summary, ensure_ascii=False))
    if args.require_chinese_provider and (summary["chinese_provider_missing"] or summary["chinese_provider_unavailable"]):
        return 2
    return 0


def render(args: argparse.Namespace) -> int:
    records = load_records(args.input)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_records(records, args.style), encoding="utf-8")
    unsupported = [record["id"] for record in records if record.get("type") != "article"]
    needs_review = [
        record["id"] for record in records
        if record.get("verification") not in {"exact", "corroborated"} or record.get("missing_fields")
    ]
    summary = {
        "draft_only": True,
        "records": len(records),
        "unsupported_type_ids": unsupported,
        "needs_review_ids": needs_review,
        "authoritative_style_engine_required": True,
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 2 if unsupported or needs_review else 0


def verify(args: argparse.Namespace) -> int:
    records = load_records(args.input, normalize=False)
    failures = []
    seen_doi: Dict[str, str] = {}
    for record in records:
        record_schema_issues = schema_issues(record)
        for schema_issue in record_schema_issues:
            failures.append({"id": record.get("id"), "issue": "schema", "field": schema_issue["field"], "schema_issue": schema_issue["issue"]})
        if record_schema_issues:
            continue
        doi = normalize_doi(record.get("doi"))
        if doi and doi in seen_doi:
            failures.append({"id": record["id"], "issue": "duplicate_doi", "other": seen_doi[doi]})
        elif doi:
            seen_doi[doi] = record["id"]
        if record.get("verification") in {"unresolved", "conflict"} or record.get("missing_fields"):
            failures.append({"id": record["id"], "issue": "needs_review", "missing_fields": record.get("missing_fields", []), "verification": record.get("verification")})
    payload = {"records": len(records), "failures": failures, "ok": not failures}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not failures else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reference curation: offline-first normalization, optional metadata enrichment and citation draft preview")
    sub = parser.add_subparsers(dest="command", required=True)
    enrich_parser = sub.add_parser("enrich", help="normalize and enrich references")
    enrich_parser.add_argument("--input", required=True)
    enrich_parser.add_argument("--output", required=True)
    enrich_parser.add_argument("--qinyan-source", default="wanfang")
    enrich_parser.add_argument("--qinyan-base", help="机构代理或 MCP gateway 的 Qinyan-compatible base URL")
    enrich_parser.add_argument("--require-chinese-provider", action="store_true")
    enrich_parser.add_argument("--mailto", help="polite-pool email for Crossref")
    enrich_parser.add_argument("--timeout", type=int, default=20)
    enrich_parser.add_argument("--retries", type=int, default=2)
    network_group = enrich_parser.add_mutually_exclusive_group()
    network_group.add_argument("--online", action="store_true", help="send DOI/title metadata to configured providers after user authorization")
    network_group.add_argument("--offline", action="store_true", help="explicitly keep all processing local (the default)")
    enrich_parser.add_argument("--json-array", action="store_true")
    enrich_parser.set_defaults(func=enrich)

    render_parser = sub.add_parser("render", help="render a non-authoritative journal-article citation draft")
    render_parser.add_argument("--input", required=True)
    render_parser.add_argument("--output", required=True)
    render_parser.add_argument("--style", required=True, choices=DRAFT_STYLES)
    render_parser.set_defaults(func=render)

    verify_parser = sub.add_parser("verify", help="check duplicates, unresolved records and missing fields")
    verify_parser.add_argument("--input", required=True)
    verify_parser.set_defaults(func=verify)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return args.func(args)
    except (OSError, ValueError, ProviderError) as exc:
        print(f"reference-curation: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
