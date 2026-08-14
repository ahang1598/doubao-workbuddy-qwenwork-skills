#!/usr/bin/env python3
"""Verify literature authenticity, quote accuracy, and positive quality signals."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import html
import json
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen


TOOL_VERSION = "1.0.0"
DEFAULT_TIMEOUT = 20
USER_AGENT = "doubao-academic-polish/1.0 (mailto:literature-verification@example.invalid)"
REVERIFY_FLAGS = {"MISSING_URL", "METADATA_ONLY", "NO_AUTHORITY_CREDENTIAL", "DOI_MISMATCH"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_text(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = normalize_space(value).casefold()
    value = re.sub(r"[\W_]+", " ", value)
    return normalize_space(value)


def normalize_doi(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.I)
    value = re.sub(r"^doi:\s*", "", value, flags=re.I)
    return value.strip().lower()


def safe_id(ref: Dict[str, Any], index: int) -> str:
    return str(ref.get("id") or ref.get("doi") or ref.get("title") or f"reference-{index + 1}")[:120]


def title_similarity(a: str, b: str) -> float:
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return difflib.SequenceMatcher(None, na, nb).ratio()


def family_name(name: str) -> str:
    name = normalize_space(name)
    if not name:
        return ""
    if "," in name:
        return normalize_text(name.split(",", 1)[0])
    parts = name.split()
    return normalize_text(parts[-1])


def institutional_author_name(name: str) -> str:
    normalized = normalize_text(name)
    markers = {
        "administration", "agency", "association", "bank", "center", "centers",
        "centre", "committee", "council", "department", "foundation",
        "government", "institute", "ministry", "office", "organization",
        "nations", "society", "university",
    }
    return re.sub(r"^the\s+", "", normalized) if set(normalized.split()) & markers else ""


def first_author_matches(expected: str, candidates: Iterable[str]) -> Tuple[bool, Optional[str]]:
    candidate_list = list(candidates)
    if not candidate_list:
        return False, None
    first_candidate = candidate_list[0]
    expected_institution = institutional_author_name(expected)
    candidate_institution = institutional_author_name(first_candidate)
    if expected_institution or candidate_institution:
        return (
            bool(expected_institution)
            and expected_institution == candidate_institution,
            first_candidate,
        )
    expected_norm = family_name(expected)
    if not expected_norm:
        return False, None
    candidate_norm = family_name(first_candidate)
    return candidate_norm == expected_norm, first_candidate


def clean_abstract(value: str) -> str:
    if not value:
        return ""
    value = html.unescape(value)
    value = re.sub(r"</?jats:[^>]+>", " ", value)
    value = re.sub(r"<[^>]+>", " ", value)
    return normalize_space(value)


def reconstruct_openalex_abstract(inverted: Optional[Dict[str, List[int]]]) -> str:
    if not inverted:
        return ""
    positions: Dict[int, str] = {}
    for word, indexes in inverted.items():
        for idx in indexes:
            positions[int(idx)] = word
    return normalize_space(" ".join(positions[i] for i in sorted(positions)))


@dataclass
class ApiCall:
    provider: str
    endpoint: str
    status: str
    http_status: Optional[int] = None
    error: Optional[str] = None


@dataclass
class Trace:
    run_id: str
    started_at: str
    input_sha256: str
    tool_version: str = TOOL_VERSION
    python_version: str = field(default_factory=lambda: sys.version.split()[0])
    api_calls: List[ApiCall] = field(default_factory=list)
    attempts: List[Dict[str, Any]] = field(default_factory=list)

    def add_call(self, provider: str, endpoint: str, status: str, http_status: Optional[int] = None, error: Optional[str] = None) -> None:
        self.api_calls.append(ApiCall(provider, endpoint, status, http_status, error))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": now_iso(),
            "tool_version": self.tool_version,
            "python_version": self.python_version,
            "input_sha256": self.input_sha256,
            "api_calls": [call.__dict__ for call in self.api_calls],
            "attempts": self.attempts,
        }


class HttpClient:
    def __init__(self, trace: Trace, timeout: int = DEFAULT_TIMEOUT, contact_email: str = ""):
        self.trace = trace
        self.timeout = timeout
        self.user_agent = USER_AGENT
        if contact_email:
            self.user_agent = f"doubao-academic-polish/1.0 (mailto:{contact_email})"

    def json_get(self, provider: str, url: str) -> Optional[Dict[str, Any]]:
        req = Request(url, headers={"User-Agent": self.user_agent, "Accept": "application/json"})
        try:
            with urlopen(req, timeout=self.timeout) as response:
                payload = response.read()
                self.trace.add_call(provider, redact_url(url), "ok", getattr(response, "status", None))
                return json.loads(payload.decode("utf-8", errors="replace"))
        except HTTPError as exc:
            self.trace.add_call(provider, redact_url(url), "http_error", exc.code, str(exc))
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            self.trace.add_call(provider, redact_url(url), "error", None, str(exc))
        return None

    def text_get(self, provider: str, url: str) -> Optional[str]:
        req = Request(url, headers={"User-Agent": self.user_agent, "Accept": "text/html, text/plain;q=0.9,*/*;q=0.1"})
        try:
            with urlopen(req, timeout=self.timeout) as response:
                content_type = response.headers.get("content-type", "")
                payload = response.read(3_000_000)
                self.trace.add_call(provider, redact_url(url), "ok", getattr(response, "status", None))
                if "pdf" in content_type.lower():
                    return ""
                return payload.decode("utf-8", errors="replace")
        except HTTPError as exc:
            self.trace.add_call(provider, redact_url(url), "http_error", exc.code, str(exc))
        except (URLError, TimeoutError) as exc:
            self.trace.add_call(provider, redact_url(url), "error", None, str(exc))
        return None


def redact_url(url: str) -> str:
    parsed = urlparse(url)
    query = []
    for item in parsed.query.split("&"):
        if item.startswith("mailto="):
            query.append("mailto=REDACTED")
        elif item:
            query.append(item)
    return parsed._replace(query="&".join(query)).geturl()


def crossref_by_doi(client: HttpClient, doi: str, contact_email: str = "") -> Optional[Dict[str, Any]]:
    doi = normalize_doi(doi)
    if not doi:
        return None
    params = {"mailto": contact_email} if contact_email else {}
    url = f"https://api.crossref.org/works/{quote(doi)}"
    if params:
        url += "?" + urlencode(params)
    data = client.json_get("crossref", url)
    if data and data.get("message"):
        return data["message"]
    return None


def crossref_search(client: HttpClient, title: str, first_author: str = "", contact_email: str = "") -> List[Dict[str, Any]]:
    params = {"query.title": title, "rows": "5"}
    if first_author:
        params["query.author"] = first_author
    if contact_email:
        params["mailto"] = contact_email
    url = "https://api.crossref.org/works?" + urlencode(params)
    data = client.json_get("crossref", url)
    if data and data.get("message", {}).get("items"):
        return data["message"]["items"]
    return []


def openalex_by_doi(client: HttpClient, doi: str) -> Optional[Dict[str, Any]]:
    doi = normalize_doi(doi)
    if not doi:
        return None
    url = "https://api.openalex.org/works/" + quote(f"https://doi.org/{doi}", safe="")
    return client.json_get("openalex", url)


def openalex_search(client: HttpClient, title: str) -> List[Dict[str, Any]]:
    url = "https://api.openalex.org/works?" + urlencode({"search": title, "per-page": "5"})
    data = client.json_get("openalex", url)
    if data and data.get("results"):
        return data["results"]
    return []


def semantic_scholar_by_doi(client: HttpClient, doi: str) -> Optional[Dict[str, Any]]:
    doi = normalize_doi(doi)
    if not doi:
        return None
    fields = "title,authors,year,venue,url,externalIds,citationCount,influentialCitationCount,abstract"
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{quote(doi)}?" + urlencode({"fields": fields})
    return client.json_get("semantic_scholar", url)


def semantic_scholar_search(client: HttpClient, title: str) -> List[Dict[str, Any]]:
    fields = "title,authors,year,venue,url,externalIds,citationCount,influentialCitationCount,abstract"
    url = "https://api.semanticscholar.org/graph/v1/paper/search?" + urlencode({"query": title, "limit": "5", "fields": fields})
    data = client.json_get("semantic_scholar", url)
    if data and data.get("data"):
        return data["data"]
    return []


def crossref_authors(item: Dict[str, Any]) -> List[str]:
    authors = []
    for author in item.get("author") or []:
        name = normalize_space(" ".join(part for part in [author.get("given", ""), author.get("family", "")] if part))
        if name:
            authors.append(name)
    return authors


def openalex_authors(item: Dict[str, Any]) -> List[str]:
    authors = []
    for authorship in item.get("authorships") or []:
        display_name = (authorship.get("author") or {}).get("display_name")
        if display_name:
            authors.append(display_name)
    return authors


def s2_authors(item: Dict[str, Any]) -> List[str]:
    return [a.get("name", "") for a in item.get("authors") or [] if a.get("name")]


def first(values: Iterable[Any]) -> str:
    for value in values:
        if isinstance(value, str) and value:
            return value
        if isinstance(value, list) and value:
            return str(value[0])
    return ""


def year_from_crossref(item: Dict[str, Any]) -> Optional[int]:
    for key in ("published-print", "published-online", "published", "issued"):
        parts = (item.get(key) or {}).get("date-parts") or []
        if parts and parts[0]:
            try:
                return int(parts[0][0])
            except (TypeError, ValueError):
                pass
    return None


def collect_metadata(ref: Dict[str, Any], client: HttpClient, contact_email: str) -> Dict[str, Any]:
    title = ref.get("title", "")
    first_author = ref.get("first_author", "")
    doi = normalize_doi(ref.get("doi", ""))
    candidates: List[Dict[str, Any]] = []

    crossref_doi = crossref_by_doi(client, doi, contact_email) if doi else None
    if crossref_doi:
        candidates.append({
            "provider": "crossref_doi",
            "title": first([crossref_doi.get("title")]),
            "doi": normalize_doi(crossref_doi.get("DOI", "")),
            "authors": crossref_authors(crossref_doi),
            "year": year_from_crossref(crossref_doi),
            "url": crossref_doi.get("URL", ""),
            "container_title": first([crossref_doi.get("container-title")]),
            "issn": crossref_doi.get("ISSN") or [],
            "abstract": clean_abstract(crossref_doi.get("abstract", "")),
            "raw": crossref_doi,
        })

    openalex_doi = openalex_by_doi(client, doi) if doi else None
    if openalex_doi and not openalex_doi.get("error"):
        candidates.append({
            "provider": "openalex_doi",
            "title": openalex_doi.get("display_name", ""),
            "doi": normalize_doi(openalex_doi.get("doi", "")),
            "authors": openalex_authors(openalex_doi),
            "year": openalex_doi.get("publication_year"),
            "url": first([
                (openalex_doi.get("primary_location") or {}).get("landing_page_url", ""),
                openalex_doi.get("id", ""),
            ]),
            "container_title": ((openalex_doi.get("primary_location") or {}).get("source") or {}).get("display_name", ""),
            "issn": ((openalex_doi.get("primary_location") or {}).get("source") or {}).get("issn") or [],
            "citations": openalex_doi.get("cited_by_count"),
            "abstract": reconstruct_openalex_abstract(openalex_doi.get("abstract_inverted_index")),
            "raw": openalex_doi,
        })

    s2_doi = semantic_scholar_by_doi(client, doi) if doi else None
    if s2_doi and not s2_doi.get("error"):
        candidates.append({
            "provider": "semantic_scholar_doi",
            "title": s2_doi.get("title", ""),
            "doi": normalize_doi((s2_doi.get("externalIds") or {}).get("DOI", "")),
            "authors": s2_authors(s2_doi),
            "year": s2_doi.get("year"),
            "url": s2_doi.get("url", ""),
            "container_title": s2_doi.get("venue", ""),
            "citations": s2_doi.get("citationCount"),
            "influential_citations": s2_doi.get("influentialCitationCount"),
            "abstract": s2_doi.get("abstract", ""),
            "raw": s2_doi,
        })

    search_terms = [title] + [frag for frag in ref.get("key_fragments") or [] if frag]
    for term in search_terms[:3]:
        for item in crossref_search(client, term, first_author, contact_email):
            candidates.append({
                "provider": "crossref_search",
                "title": first([item.get("title")]),
                "doi": normalize_doi(item.get("DOI", "")),
                "authors": crossref_authors(item),
                "year": year_from_crossref(item),
                "url": item.get("URL", ""),
                "container_title": first([item.get("container-title")]),
                "issn": item.get("ISSN") or [],
                "abstract": clean_abstract(item.get("abstract", "")),
                "raw": item,
            })
        for item in openalex_search(client, term):
            candidates.append({
                "provider": "openalex_search",
                "title": item.get("display_name", ""),
                "doi": normalize_doi(item.get("doi", "")),
                "authors": openalex_authors(item),
                "year": item.get("publication_year"),
                "url": first([(item.get("primary_location") or {}).get("landing_page_url", ""), item.get("id", "")]),
                "container_title": ((item.get("primary_location") or {}).get("source") or {}).get("display_name", ""),
                "issn": ((item.get("primary_location") or {}).get("source") or {}).get("issn") or [],
                "citations": item.get("cited_by_count"),
                "abstract": reconstruct_openalex_abstract(item.get("abstract_inverted_index")),
                "raw": item,
            })
        for item in semantic_scholar_search(client, term):
            candidates.append({
                "provider": "semantic_scholar_search",
                "title": item.get("title", ""),
                "doi": normalize_doi((item.get("externalIds") or {}).get("DOI", "")),
                "authors": s2_authors(item),
                "year": item.get("year"),
                "url": item.get("url", ""),
                "container_title": item.get("venue", ""),
                "citations": item.get("citationCount"),
                "influential_citations": item.get("influentialCitationCount"),
                "abstract": item.get("abstract", ""),
                "raw": item,
            })

    best = choose_best_candidate(ref, candidates)
    return {"candidates": strip_raw(candidates), "best": strip_raw_one(best) if best else None, "best_raw": best}


def choose_best_candidate(ref: Dict[str, Any], candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    expected_title = ref.get("title", "")
    expected_author = ref.get("first_author", "")
    expected_doi = normalize_doi(ref.get("doi", ""))
    expected_year = safe_int(ref.get("year"))

    def score(candidate: Dict[str, Any]) -> float:
        title_score = title_similarity(expected_title, candidate.get("title", "")) * 60
        author_ok, _ = first_author_matches(expected_author, candidate.get("authors") or [])
        author_score = 25 if author_ok else 0
        doi_score = 15 if expected_doi and normalize_doi(candidate.get("doi", "")) == expected_doi else 0
        candidate_year = safe_int(candidate.get("year"))
        year_score = (
            10
            if expected_year and candidate_year == expected_year
            else -20
            if expected_year and candidate_year and candidate_year != expected_year
            else 0
        )
        provider_bonus = 5 if candidate.get("provider", "").endswith("_doi") else 0
        return title_score + author_score + doi_score + year_score + provider_bonus

    if not candidates:
        return None
    return max(candidates, key=score)


def strip_raw(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [strip_raw_one(c) for c in candidates[:20]]


def strip_raw_one(candidate: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in candidate.items() if k != "raw"}


def verify_authenticity(ref: Dict[str, Any], best: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    checks = []
    flags = []
    expected_title = ref.get("title", "")
    expected_author = ref.get("first_author", "")
    expected_doi = normalize_doi(ref.get("doi", ""))
    expected_year = safe_int(ref.get("year"))

    if not best:
        return {
            "status": "failed",
            "checks": [{"name": "metadata_lookup", "status": "failed", "detail": "No matching metadata found."}],
            "flags": ["METADATA_NOT_FOUND", "METADATA_ONLY"],
            "matched_metadata": None,
        }

    sim = title_similarity(expected_title, best.get("title", ""))
    checks.append({"name": "title_match", "status": "passed" if sim >= 0.88 else "failed", "score": round(sim, 3), "matched_title": best.get("title", "")})
    if sim < 0.88:
        flags.append("TITLE_MISMATCH")

    author_ok, matched_author = first_author_matches(expected_author, best.get("authors") or [])
    checks.append({"name": "first_author_match", "status": "passed" if author_ok else "failed", "expected": expected_author, "matched": matched_author})
    if expected_author and not author_ok:
        flags.append("AUTHOR_MISMATCH")

    matched_year = safe_int(best.get("year"))
    if expected_year is not None:
        year_ok = matched_year == expected_year
        checks.append(
            {
                "name": "year_match",
                "status": "passed" if year_ok else "failed",
                "expected": expected_year,
                "matched": matched_year,
            }
        )
        if not year_ok:
            flags.append("YEAR_MISMATCH")

    matched_doi = normalize_doi(best.get("doi", ""))
    if expected_doi and matched_doi:
        doi_ok = expected_doi == matched_doi
        checks.append({"name": "doi_reverse_lookup", "status": "passed" if doi_ok else "failed", "expected": expected_doi, "matched": matched_doi})
        if not doi_ok:
            flags.append("DOI_MISMATCH")
    elif expected_doi and not matched_doi:
        checks.append({"name": "doi_reverse_lookup", "status": "failed", "expected": expected_doi, "matched": ""})
        flags.append("DOI_MISMATCH")
    else:
        checks.append({"name": "doi_reverse_lookup", "status": "not_applicable", "detail": "No DOI provided."})

    matched_url = best.get("url") or ref.get("url") or ""
    if matched_url:
        checks.append({"name": "url_present", "status": "passed", "url": matched_url})
    else:
        checks.append({"name": "url_present", "status": "failed"})
        flags.append("MISSING_URL")

    passed_required = (
        sim >= 0.88
        and (not expected_author or author_ok)
        and "DOI_MISMATCH" not in flags
        and "YEAR_MISMATCH" not in flags
    )
    status = "verified" if passed_required else "partial" if sim >= 0.75 else "failed"
    return {"status": status, "checks": checks, "flags": flags, "matched_metadata": strip_raw_one(best)}


def verify_quotes(ref: Dict[str, Any], best: Optional[Dict[str, Any]], client: HttpClient) -> Dict[str, Any]:
    quoted_claims = ref.get("quoted_claims") or []
    if not quoted_claims:
        return {"status": "not_requested", "checks": [], "metadata_only": False}

    source_texts = []
    if best and best.get("abstract"):
        source_texts.append(("abstract_metadata", best.get("abstract", "")))

    url = ref.get("url") or (best or {}).get("url") or ""
    if url and url.startswith("http"):
        html_text = client.text_get("source_url", url)
        if html_text:
            source_texts.append(("source_url", html_to_text(html_text)))

    checks = []
    metadata_only = bool(source_texts) and all(name == "abstract_metadata" for name, _ in source_texts)
    for claim in quoted_claims:
        quote_text = normalize_space(claim.get("quote", ""))
        best_match = find_best_quote_match(quote_text, source_texts)
        status = "passed" if best_match["score"] >= 0.92 else "partial" if best_match["score"] >= 0.78 else "failed"
        checks.append({
            "id": claim.get("id", ""),
            "status": status,
            "score": best_match["score"],
            "source": best_match["source"],
            "matched_excerpt": best_match["excerpt"],
        })

    if not source_texts:
        return {"status": "failed", "checks": checks, "metadata_only": True, "flags": ["QUOTE_SOURCE_UNAVAILABLE", "METADATA_ONLY"]}

    if all(check["status"] == "passed" for check in checks):
        status = "verified"
    elif any(check["status"] in {"passed", "partial"} for check in checks):
        status = "partial"
    else:
        status = "failed"
    flags = ["METADATA_ONLY"] if metadata_only else []
    if status != "verified":
        flags.append("QUOTE_UNVERIFIED")
    return {"status": status, "checks": checks, "metadata_only": metadata_only, "flags": flags}


def html_to_text(value: str) -> str:
    value = re.sub(r"(?is)<(script|style).*?</\1>", " ", value)
    value = re.sub(r"<[^>]+>", " ", value)
    return normalize_space(html.unescape(value))


def find_best_quote_match(quote_text: str, source_texts: List[Tuple[str, str]]) -> Dict[str, Any]:
    norm_quote = normalize_text(quote_text)
    if not norm_quote or not source_texts:
        return {"score": 0.0, "source": "", "excerpt": ""}

    best = {"score": 0.0, "source": "", "excerpt": ""}
    q_words = norm_quote.split()
    window = max(8, len(q_words) + 4)
    for source_name, text in source_texts:
        norm_text = normalize_text(text)
        if norm_quote in norm_text:
            excerpt = excerpt_around(text, quote_text)
            return {"score": 1.0, "source": source_name, "excerpt": excerpt}
        words = norm_text.split()
        for i in range(0, max(1, len(words) - window + 1)):
            candidate = " ".join(words[i:i + window])
            score = difflib.SequenceMatcher(None, norm_quote, candidate).ratio()
            if score > best["score"]:
                best = {"score": round(score, 3), "source": source_name, "excerpt": " ".join(words[i:i + window])[:360]}
    return best


def excerpt_around(text: str, quote_text: str, radius: int = 180) -> str:
    lower = text.casefold()
    idx = lower.find(quote_text.casefold())
    if idx < 0:
        return normalize_space(text[: radius * 2])
    start = max(0, idx - radius)
    end = min(len(text), idx + len(quote_text) + radius)
    return normalize_space(text[start:end])


def load_quality_registry(path: str) -> Dict[str, Any]:
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def verify_quality(ref: Dict[str, Any], best: Optional[Dict[str, Any]], registry: Dict[str, Any], current_year: int) -> Dict[str, Any]:
    credentials = []
    flags = []
    matched = best or {}
    venue_name = normalize_space(matched.get("container_title", ""))
    source_url = matched.get("url", "")
    issn_values = set(normalize_issn(v) for v in ((best or {}).get("issn") or []) if v)

    venue_match = match_venue(venue_name, issn_values, registry.get("venues") or [])
    if venue_match:
        if venue_match.get("jcr_quartile"):
            credentials.append({"type": "jcr_quartile", "value": venue_match.get("jcr_quartile"), "evidence_url": venue_match.get("evidence_url", "")})
        if venue_match.get("cas_zone"):
            credentials.append({"type": "cas_zone", "value": venue_match.get("cas_zone"), "evidence_url": venue_match.get("evidence_url", "")})
        if venue_match.get("impact_factor"):
            credentials.append({"type": "impact_factor", "value": venue_match.get("impact_factor"), "evidence_url": venue_match.get("evidence_url", "")})
        if venue_match.get("is_top_venue"):
            credentials.append({"type": "top_venue", "value": venue_match.get("name"), "evidence_url": venue_match.get("evidence_url", "")})

    citation_count = max_int([matched.get("citations")])
    threshold = int((registry.get("citation_thresholds") or {}).get("highly_cited", 500))
    classic_age = int((registry.get("citation_thresholds") or {}).get("classic_min_age_years", 10))
    publication_year = safe_int(matched.get("year"))
    if citation_count is not None and citation_count >= threshold:
        credentials.append({"type": "highly_cited", "value": citation_count, "threshold": threshold})
    if citation_count is not None and publication_year and current_year - publication_year >= classic_age and citation_count >= threshold:
        credentials.append({"type": "highly_cited_classic", "value": citation_count, "year": publication_year, "threshold": threshold})

    domain = host_domain(source_url)
    if domain and domain_matches(domain, registry.get("authority_domains") or []):
        credentials.append({"type": "authority_org_source", "value": domain, "evidence_url": source_url})
    if source_url and (matched.get("source_type") or "").lower() in {"seminar", "seminar_official", "lecture"}:
        if domain_matches(domain, registry.get("seminar_official_domains") or []):
            credentials.append({"type": "seminar_official", "value": domain, "evidence_url": source_url})

    if not credentials:
        flags.append("NO_AUTHORITY_CREDENTIAL")

    status = "credentialed" if credentials else "uncredentialed"
    return {"status": status, "credentials": credentials, "flags": flags}


def normalize_issn(value: str) -> str:
    return re.sub(r"[^0-9Xx]", "", value or "").upper()


def match_venue(name: str, issns: set, venues: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    norm_name = normalize_text(name)
    for venue in venues:
        venue_issns = set(normalize_issn(v) for v in venue.get("issn") or [])
        if issns and venue_issns and issns.intersection(venue_issns):
            return venue
        names = [venue.get("name", "")] + list(venue.get("aliases") or [])
        for candidate in names:
            candidate_norm = normalize_text(candidate)
            if candidate_norm and (candidate_norm == norm_name or candidate_norm in norm_name or norm_name in candidate_norm):
                return venue
    return None


def host_domain(url: str) -> str:
    if not url:
        return ""
    host = urlparse(url if "://" in url else f"https://{url}").netloc.lower()
    return host[4:] if host.startswith("www.") else host


def domain_matches(domain: str, patterns: List[str]) -> bool:
    if not domain:
        return False
    for pattern in patterns:
        pattern = pattern.lower().strip()
        if not pattern:
            continue
        if domain == pattern or domain.endswith("." + pattern):
            return True
    return False


def safe_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def max_int(values: Iterable[Any]) -> Optional[int]:
    ints = [v for v in (safe_int(value) for value in values) if v is not None]
    return max(ints) if ints else None


def build_reverification(auth: Dict[str, Any], quotes: Dict[str, Any], quality: Dict[str, Any]) -> Dict[str, Any]:
    flags = set(auth.get("flags") or [])
    flags.update(quotes.get("flags") or [])
    flags.update(quality.get("flags") or [])
    triggers = sorted(flags.intersection(REVERIFY_FLAGS))
    return {
        "required": bool(triggers),
        "triggers": triggers,
        "all_flags": sorted(flags),
        "rule": "重新走验真流程：缺 URL、仅 metadata、无权威凭据、DOI 不匹配任一出现即触发。"
    }


def check_by_name(checks: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    for check in checks:
        if check.get("name") == name:
            return check
    return None


def status_from_check(checks: List[Dict[str, Any]], name: str) -> str:
    check = check_by_name(checks, name)
    if not check:
        return "missing"
    status = str(check.get("status") or "").lower()
    if status == "passed":
        return "pass"
    if status == "not_applicable":
        return "not_applicable"
    return "fail"


def title_author_gate(auth: Dict[str, Any]) -> str:
    checks = auth.get("checks") or []
    title_status = status_from_check(checks, "title_match")
    author_status = status_from_check(checks, "first_author_match")
    return "pass" if title_status == "pass" and author_status in {"pass", "not_applicable"} else "fail"


def doi_gate(auth: Dict[str, Any]) -> str:
    checks = auth.get("checks") or []
    status = status_from_check(checks, "doi_reverse_lookup")
    return status if status in {"pass", "not_applicable"} else "fail"


def evidence_url_present(auth: Dict[str, Any], item_input: Dict[str, Any]) -> str:
    matched = auth.get("matched_metadata") or {}
    url = item_input.get("url") or matched.get("url") or ""
    return "yes" if normalize_space(url) else "no"


def quote_read_status(quote_accuracy: Dict[str, Any], item_input: Dict[str, Any], auth: Dict[str, Any]) -> str:
    if quote_accuracy.get("metadata_only"):
        return "metadata_only"
    quote_status = str(quote_accuracy.get("status") or "").lower()
    if quote_status == "verified":
        if any((check.get("source") or "") == "source_url" for check in quote_accuracy.get("checks") or []):
            return "fulltext_checked"
        return "abstract_checked"
    if quote_status == "partial":
        return "partial_text_checked"
    if quote_status == "not_requested" and evidence_url_present(auth, item_input) == "yes":
        return "url_present_not_quoted"
    return "metadata_only"


def credential_basis(credentials: List[Dict[str, Any]]) -> str:
    parts = []
    for credential in credentials:
        ctype = credential.get("type", "")
        value = credential.get("value", "")
        threshold = credential.get("threshold", "")
        if threshold:
            parts.append(f"{ctype}:{value}>=threshold:{threshold}")
        elif value:
            parts.append(f"{ctype}:{value}")
        else:
            parts.append(ctype)
    return "; ".join(part for part in parts if part)


def authority_signal(credentials: List[Dict[str, Any]]) -> str:
    signals = []
    for credential in credentials:
        ctype = credential.get("type", "")
        value = credential.get("value", "")
        if ctype in {
            "jcr_quartile",
            "cas_zone",
            "impact_factor",
            "top_venue",
            "highly_cited",
            "highly_cited_classic",
            "authority_org_source",
            "seminar_official",
        }:
            signals.append(f"{ctype}:{value}" if value else ctype)
    return "; ".join(signals)


def assign_source_quality(auth: Dict[str, Any], quality: Dict[str, Any], reverification: Dict[str, Any]) -> str:
    credentials = quality.get("credentials") or []
    credential_types = {credential.get("type") for credential in credentials}
    auth_status = str(auth.get("status") or "").lower()
    doi_status = doi_gate(auth)
    title_author_status = title_author_gate(auth)
    if reverification.get("required") or doi_status == "fail" or title_author_status == "fail" or not credentials:
        return "C"
    if auth_status == "verified" and (
        "top_venue" in credential_types
        or "jcr_quartile" in credential_types
        or "cas_zone" in credential_types
        or "highly_cited_classic" in credential_types
        or "authority_org_source" in credential_types
    ):
        return "A"
    if auth_status in {"verified", "partial"}:
        return "B"
    return "C"


def core_literature_entry(item: Dict[str, Any]) -> Dict[str, Any]:
    item_input = item.get("input") or {}
    auth = item.get("authenticity") or {}
    quality = item.get("quality_credentials") or {}
    quote_accuracy = item.get("quote_accuracy") or {}
    reverification = item.get("reverification") or {}
    matched = auth.get("matched_metadata") or {}
    credentials = quality.get("credentials") or []
    doi = matched.get("doi") or ""
    url = matched.get("url") or (f"https://doi.org/{doi}" if doi else "")
    matched_authors = matched.get("authors") or []
    first_author = matched_authors[0] if matched_authors else item_input.get("first_author", "")
    basis = credential_basis(credentials)
    signal = authority_signal(credentials)
    return {
        "id": item.get("id", ""),
        "title": matched.get("title") or item_input.get("title", ""),
        "first_author": first_author,
        "year": matched.get("year"),
        "doi": doi,
        "url": url,
        "container_title": matched.get("container_title", ""),
        "read_status": quote_read_status(quote_accuracy, item_input, auth),
        "source_quality": assign_source_quality(auth, quality, reverification),
        "authority_signal": signal,
        "quality_basis": basis,
        "authenticity_status": auth.get("status", ""),
        "title_author_match": title_author_gate(auth),
        "doi_match": doi_gate(auth),
        "reverification_required": "yes" if reverification.get("required") else "no",
        "reverification_triggers": reverification.get("triggers") or [],
    }


def accepted_for_scout(entry: Dict[str, Any]) -> bool:
    return (
        entry.get("url")
        and entry.get("read_status") != "metadata_only"
        and entry.get("source_quality") in {"A", "B"}
        and entry.get("authority_signal")
        and entry.get("quality_basis")
        and entry.get("doi_match") != "fail"
        and entry.get("title_author_match") == "pass"
        and entry.get("reverification_required") == "no"
    )


def build_scout_handoff(payload: Dict[str, Any], report: Dict[str, Any], report_path: str, min_core: int, stage: str) -> Dict[str, Any]:
    core_candidates = [core_literature_entry(item) for item in report.get("results") or []]
    core_literature = [entry for entry in core_candidates if accepted_for_scout(entry)]
    rejected_literature = [entry for entry in core_candidates if not accepted_for_scout(entry)]
    failures = []
    if not report.get("results"):
        failures.append("candidate_pool is empty.")
    if len(core_literature) < min_core:
        failures.append(f"core_literature has {len(core_literature)} accepted item(s), below min_core={min_core}.")

    ready = not failures
    return {
        "stage": stage,
        "read_gate": "pass",
        "candidate_pool_count": len(report.get("results") or []),
        "candidate_pool_done": "yes" if report.get("results") else "no",
        "authenticity_checked": "pass" if report.get("results") else "fail",
        "quality_checked": "pass" if report.get("results") else "fail",
        "verification_report_path": report_path,
        "code_trace_present": "yes" if (report.get("code_trace") or {}).get("run_id") else "no",
        "code_trace_run_id": (report.get("code_trace") or {}).get("run_id", ""),
        "core_literature": core_literature,
        "rejected_literature": rejected_literature,
        "ready_for_synthesis": "yes" if ready else "no",
        "failures": failures,
    }


def verify_reference(ref: Dict[str, Any], index: int, client: HttpClient, registry: Dict[str, Any], contact_email: str, current_year: int, trace: Trace) -> Dict[str, Any]:
    ref_id = safe_id(ref, index)
    metadata = collect_metadata(ref, client, contact_email)
    best_raw = metadata.pop("best_raw", None)
    auth = verify_authenticity(ref, best_raw)
    quotes = verify_quotes(ref, best_raw, client)
    quality = verify_quality(ref, best_raw, registry, current_year)
    reverification = build_reverification(auth, quotes, quality)

    trace.attempts.append({
        "reference_id": ref_id,
        "attempt": 1,
        "providers": sorted(set(c.get("provider", "") for c in metadata.get("candidates", []))),
        "reverification_triggers": reverification["triggers"],
    })

    return {
        "id": ref_id,
        "input": {
            "title": ref.get("title", ""),
            "first_author": ref.get("first_author", ""),
            "doi": normalize_doi(ref.get("doi", "")),
            "url": ref.get("url", ""),
            "container_title": ref.get("container_title", ""),
            "year": ref.get("year"),
            "source_type": ref.get("source_type", ""),
        },
        "authenticity": auth,
        "quote_accuracy": quotes,
        "quality_credentials": quality,
        "reverification": reverification,
        "metadata_candidates": metadata.get("candidates", []),
    }


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    verified = sum(1 for r in results if r["authenticity"]["status"] == "verified")
    needs_reverification = sum(1 for r in results if r["reverification"]["required"])
    credentialed = sum(1 for r in results if r["quality_credentials"]["status"] == "credentialed")
    return {
        "total_references": total,
        "authenticity_verified": verified,
        "quality_credentialed": credentialed,
        "needs_reverification": needs_reverification,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Literature Verification Report",
        "",
        f"- Run ID: `{report['code_trace']['run_id']}`",
        f"- Started: `{report['code_trace']['started_at']}`",
        f"- Input SHA-256: `{report['code_trace']['input_sha256']}`",
        f"- Total references: {report['summary']['total_references']}",
        f"- Needs reverification: {report['summary']['needs_reverification']}",
        "",
    ]
    for item in report["results"]:
        lines.extend([
            f"## {item['id']}",
            "",
            f"- Authenticity: **{item['authenticity']['status']}**",
            f"- Quote accuracy: **{item['quote_accuracy']['status']}**",
            f"- Quality credentials: **{item['quality_credentials']['status']}**",
            f"- Reverification required: **{item['reverification']['required']}**",
            f"- Reverification triggers: {', '.join(item['reverification']['triggers']) or 'none'}",
            "",
            "### Checks",
            "",
        ])
        for check in item["authenticity"].get("checks", []):
            lines.append(f"- `{check.get('name')}`: {check.get('status')} {compact_detail(check)}")
        for check in item["quote_accuracy"].get("checks", []):
            lines.append(f"- `quote:{check.get('id')}`: {check.get('status')} score={check.get('score')} source={check.get('source')}")
        if item["quality_credentials"].get("credentials"):
            lines.extend(["", "### Positive Quality Credentials", ""])
            for cred in item["quality_credentials"]["credentials"]:
                lines.append(f"- `{cred.get('type')}`: {cred.get('value', '')} {cred.get('evidence_url', '')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def compact_detail(check: Dict[str, Any]) -> str:
    parts = []
    if "score" in check:
        parts.append(f"score={check['score']}")
    if check.get("matched"):
        parts.append(f"matched={check['matched']}")
    if check.get("matched_title"):
        parts.append(f"title={check['matched_title'][:120]}")
    if check.get("expected") and check.get("matched") is not None:
        parts.append(f"expected={check['expected']}")
    return " ".join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify literature authenticity, quote accuracy, and quality credentials.")
    parser.add_argument("input_json", help="JSON file containing a top-level 'references' array.")
    parser.add_argument("--out", default="literature-verification-report.json", help="Path for JSON report.")
    parser.add_argument("--markdown", default="", help="Optional Markdown report path.")
    parser.add_argument("--handoff", default="", help="Optional .workflow/scout_handoff.json path.")
    parser.add_argument("--workflow-stage", default="literature-scout", help="Stage name written into the handoff.")
    parser.add_argument("--min-core", type=int, default=1, help="Minimum accepted A/B core_literature entries required for ready_for_synthesis=yes.")
    parser.add_argument("--require-handoff-pass", action="store_true", help="Exit 1 unless generated handoff is ready_for_synthesis=yes.")
    parser.add_argument("--quality-registry", default="", help="Optional local JSON registry for JCR/CAS/IF/top venues/authority domains.")
    parser.add_argument("--contact-email", default="", help="Contact email passed to scholarly APIs where supported.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="HTTP timeout in seconds.")
    parser.add_argument("--current-year", type=int, default=datetime.now().year, help="Year used for classic citation checks.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with open(args.input_json, "rb") as handle:
        input_bytes = handle.read()
    payload = json.loads(input_bytes.decode("utf-8-sig"))
    references = payload.get("references")
    if not isinstance(references, list):
        raise SystemExit("Input JSON must contain a top-level 'references' array.")

    registry = load_quality_registry(args.quality_registry)
    trace = Trace(run_id=str(uuid.uuid4()), started_at=now_iso(), input_sha256=hashlib.sha256(input_bytes).hexdigest())
    client = HttpClient(trace, timeout=args.timeout, contact_email=args.contact_email)

    results = []
    for index, ref in enumerate(references):
        if not isinstance(ref, dict):
            continue
        results.append(verify_reference(ref, index, client, registry, args.contact_email, args.current_year, trace))
        time.sleep(0.2)

    report = {
        "summary": summarize(results),
        "results": results,
        "code_trace": trace.as_dict(),
    }
    if args.handoff:
        handoff = build_scout_handoff(payload, report, args.out, args.min_core, args.workflow_stage)
        report["summary"]["core_literature_ready"] = len(handoff["core_literature"])
        report["summary"]["ready_for_synthesis"] = handoff["ready_for_synthesis"]
    else:
        handoff = None

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    if args.markdown:
        Path(args.markdown).parent.mkdir(parents=True, exist_ok=True)
        with open(args.markdown, "w", encoding="utf-8") as handle:
            handle.write(render_markdown(report))
    if handoff:
        Path(args.handoff).parent.mkdir(parents=True, exist_ok=True)
        with open(args.handoff, "w", encoding="utf-8") as handle:
            json.dump(handoff, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    print(json.dumps(report["summary"], ensure_ascii=False))
    if args.require_handoff_pass and handoff and handoff.get("ready_for_synthesis") != "yes":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
