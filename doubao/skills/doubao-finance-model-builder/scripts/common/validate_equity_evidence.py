#!/usr/bin/env python3
"""Validate frozen primary equity evidence before valuation inputs are used."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


OFFICIAL_DOMAINS = {
    "SSE": ("sse.com.cn", "cninfo.com.cn"),
    "SZSE": ("szse.cn", "cninfo.com.cn"),
    "BSE": ("bse.cn", "cninfo.com.cn"),
    "HKEX": ("hkexnews.hk", "hkex.com.hk"),
    "NASDAQ": ("sec.gov",),
    "NYSE": ("sec.gov",),
    "AMEX": ("sec.gov",),
    "SEC": ("sec.gov",),
}
PRIMARY_ROLES = {
    "baseline_share_disclosure",
    "corporate_action_search_result",
    "corporate_action_announcement",
}
ACTION_TYPES_REQUIRING_BASIS_REVIEW = {"capitalisation", "bonus", "split", "consolidation"}


def parse_date(value: Any, field: str, errors: list[str]) -> date | None:
    if not isinstance(value, str):
        errors.append(f"{field} must be YYYY-MM-DD")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{field} must be YYYY-MM-DD")
        return None


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def safe_file(root: Path, relative: Any, field: str, errors: list[str]) -> Path | None:
    if not nonempty(relative):
        errors.append(f"{field} must be a non-empty relative path")
        return None
    candidate = (root / relative).resolve()
    resolved_root = root.resolve()
    if candidate == resolved_root or resolved_root not in candidate.parents:
        errors.append(f"{field} escapes evidence root")
        return None
    if not candidate.is_file():
        errors.append(f"{field} does not exist: {relative}")
        return None
    return candidate


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def official_host(url: Any, exchange: str) -> bool:
    if not nonempty(url) or exchange not in OFFICIAL_DOMAINS:
        return False
    host = urlparse(url).hostname or ""
    host = host.lower()
    return any(host == domain or host.endswith("." + domain) for domain in OFFICIAL_DOMAINS[exchange])


def validate(payload: dict[str, Any], root: Path) -> dict[str, Any]:
    errors: list[str] = []
    checks: dict[str, str] = {}

    if payload.get("schema_version") != "3.1":
        errors.append("schema_version must be 3.1")
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    if not meta:
        errors.append("meta is required")
    valuation_date = parse_date(meta.get("valuation_date"), "meta.valuation_date", errors)
    cutoff_date = parse_date(meta.get("information_cutoff_date"), "meta.information_cutoff_date", errors)
    if valuation_date and cutoff_date and cutoff_date > valuation_date:
        errors.append("information cutoff cannot be later than valuation date")
    formal = meta.get("model_purpose") == "formal"
    if meta.get("model_purpose") not in {"formal", "illustrative"}:
        errors.append("meta.model_purpose must be formal or illustrative")
    aliases = meta.get("issuer_aliases")
    if not isinstance(aliases, list) or not aliases or any(not nonempty(x) for x in aliases):
        errors.append("meta.issuer_aliases must be a non-empty list")
        aliases = []

    securities = payload.get("securities")
    if not isinstance(securities, list) or not securities:
        errors.append("securities must be a non-empty list")
        securities = []
    security_map: dict[str, dict[str, Any]] = {}
    for i, security in enumerate(securities):
        prefix = f"securities[{i}]"
        if not isinstance(security, dict) or not nonempty(security.get("security_id")):
            errors.append(f"{prefix}.security_id is required")
            continue
        sid = security["security_id"]
        if sid in security_map:
            errors.append(f"duplicate security_id: {sid}")
        exchange = security.get("exchange")
        if exchange not in OFFICIAL_DOMAINS:
            errors.append(f"{prefix}.exchange is unsupported")
        for key in ("baseline_evidence_id", "search_id"):
            if not nonempty(security.get(key)):
                errors.append(f"{prefix}.{key} is required")
        security_map[sid] = security

    evidence = payload.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("evidence must be a non-empty list")
        evidence = []
    evidence_map: dict[str, dict[str, Any]] = {}
    evidence_text: dict[str, str] = {}
    for i, item in enumerate(evidence):
        prefix = f"evidence[{i}]"
        if not isinstance(item, dict) or not nonempty(item.get("evidence_id")):
            errors.append(f"{prefix}.evidence_id is required")
            continue
        eid = item["evidence_id"]
        if eid in evidence_map:
            errors.append(f"duplicate evidence_id: {eid}")
            continue
        evidence_map[eid] = item
        sid = item.get("security_id")
        security = security_map.get(sid)
        if not security:
            errors.append(f"{prefix}.security_id must match securities")
            continue
        role = item.get("role")
        if role not in PRIMARY_ROLES:
            errors.append(f"{prefix}.role is invalid")
        if item.get("authority_tier") != "primary":
            errors.append(f"{prefix}.authority_tier must be primary")
        if not official_host(item.get("url"), security.get("exchange")):
            errors.append(f"{prefix}.url is not an accepted official domain")
        published = parse_date(item.get("published_date"), f"{prefix}.published_date", errors)
        if cutoff_date and published and published > cutoff_date:
            errors.append(f"{prefix} was published after the information cutoff")
        original = safe_file(root, item.get("local_file"), f"{prefix}.local_file", errors)
        text_path = safe_file(root, item.get("text_file"), f"{prefix}.text_file", errors)
        if original:
            if original.stat().st_size < 80:
                errors.append(f"{prefix}.local_file is too small to be evidence")
            if hash_file(original) != item.get("sha256"):
                errors.append(f"{prefix}.sha256 does not match local_file")
        if text_path:
            if hash_file(text_path) != item.get("text_sha256"):
                errors.append(f"{prefix}.text_sha256 does not match text_file")
            text = text_path.read_text(encoding="utf-8", errors="replace")
            evidence_text[eid] = text
            if not any(alias in text for alias in aliases + [sid]):
                errors.append(f"{prefix}.text_file does not identify the issuer/security")
            if formal and ("结构示例" in text or "不得用于正式估值" in text):
                errors.append(f"{prefix} uses illustrative skill evidence in a formal task")

    searches = payload.get("searches")
    if not isinstance(searches, list) or not searches:
        errors.append("searches must be a non-empty list")
        searches = []
    search_map: dict[str, dict[str, Any]] = {}
    discovered_by_security: dict[str, set[str]] = {}
    for i, search in enumerate(searches):
        prefix = f"searches[{i}]"
        if not isinstance(search, dict) or not nonempty(search.get("search_id")):
            errors.append(f"{prefix}.search_id is required")
            continue
        search_id = search["search_id"]
        if search_id in search_map:
            errors.append(f"duplicate search_id: {search_id}")
        search_map[search_id] = search
        sid = search.get("security_id")
        security = security_map.get(sid)
        if not security:
            errors.append(f"{prefix}.security_id must match securities")
            continue
        baseline = parse_date(search.get("baseline_date"), f"{prefix}.baseline_date", errors)
        start = parse_date(search.get("search_start_date"), f"{prefix}.search_start_date", errors)
        end = parse_date(search.get("search_end_date"), f"{prefix}.search_end_date", errors)
        if baseline and start and start > baseline:
            errors.append(f"{prefix}.search_start_date must be no later than baseline_date")
        if valuation_date and end and end != valuation_date:
            errors.append(f"{prefix}.search_end_date must equal valuation_date")
        if not official_host(search.get("official_entry_url"), security.get("exchange")):
            errors.append(f"{prefix}.official_entry_url is not official")
        if search.get("completed") is not True or search.get("coverage_gaps") != []:
            errors.append(f"{prefix} is incomplete or has coverage gaps")
        queries = search.get("queries")
        if not isinstance(queries, list) or len(queries) < 2 or any(not nonempty(x) for x in queries):
            errors.append(f"{prefix}.queries requires at least two documented queries")
        result_ids = search.get("result_evidence_ids")
        if not isinstance(result_ids, list) or not result_ids:
            errors.append(f"{prefix}.result_evidence_ids must be non-empty")
            result_ids = []
        for eid in result_ids:
            item = evidence_map.get(eid)
            if not item or item.get("role") != "corporate_action_search_result" or item.get("security_id") != sid:
                errors.append(f"{prefix} references invalid official search-result evidence: {eid}")
        action_ids = search.get("discovered_action_ids")
        if not isinstance(action_ids, list) or len(action_ids) != len(set(action_ids)) or any(not nonempty(x) for x in action_ids):
            errors.append(f"{prefix}.discovered_action_ids must be a unique list")
            action_ids = []
        frozen_search_text = "\n".join(evidence_text.get(eid, "") for eid in result_ids)
        frozen_ids = set(re.findall(r"\[DISCOVERED_ACTION_ID:([^\]]+)\]", frozen_search_text))
        no_actions_marker = "[NO_ACTIONS_FOUND]" in frozen_search_text
        if frozen_ids and no_actions_marker:
            errors.append(f"{prefix} search evidence contains conflicting action markers")
        if set(action_ids) != frozen_ids:
            errors.append(f"{prefix}.discovered_action_ids do not match frozen search-result markers")
        if not action_ids and not no_actions_marker:
            errors.append(f"{prefix} empty result requires [NO_ACTIONS_FOUND] in frozen search text")
        for action_id in action_ids:
            if not any(action_id in evidence_text.get(eid, "") for eid in result_ids):
                errors.append(f"{prefix} action {action_id} is not present in frozen search-result text")
        discovered_by_security[sid] = set(action_ids)

    for sid, security in security_map.items():
        if security.get("search_id") not in search_map:
            errors.append(f"{sid} does not reference a valid search")
        baseline_item = evidence_map.get(security.get("baseline_evidence_id"))
        if not baseline_item or baseline_item.get("role") != "baseline_share_disclosure" or baseline_item.get("security_id") != sid:
            errors.append(f"{sid} does not reference valid baseline share evidence")

    bridge = payload.get("share_bridge") if isinstance(payload.get("share_bridge"), dict) else {}
    classes = bridge.get("security_classes")
    if not isinstance(classes, list) or not classes:
        errors.append("share_bridge.security_classes must be non-empty")
        classes = []
    bridge_security_ids: set[str] = set()
    bridge_action_ids: set[str] = set()
    recent_basis_actions: set[str] = set()
    for i, item in enumerate(classes):
        prefix = f"share_bridge.security_classes[{i}]"
        if not isinstance(item, dict) or item.get("security_id") not in security_map:
            errors.append(f"{prefix}.security_id must match securities")
            continue
        sid = item["security_id"]
        bridge_security_ids.add(sid)
        baseline = parse_date(item.get("baseline_date"), f"{prefix}.baseline_date", errors)
        value_date = parse_date(item.get("valuation_date"), f"{prefix}.valuation_date", errors)
        if valuation_date and value_date and value_date != valuation_date:
            errors.append(f"{prefix}.valuation_date must equal meta.valuation_date")
        search = search_map.get(security_map[sid].get("search_id"), {})
        search_baseline = parse_date(search.get("baseline_date"), f"{prefix}.search_baseline_date", []) if search else None
        if baseline and search_baseline and baseline != search_baseline:
            errors.append(f"{prefix}.baseline_date does not match search baseline")
        if item.get("baseline_evidence_id") != security_map[sid].get("baseline_evidence_id"):
            errors.append(f"{prefix}.baseline_evidence_id does not match securities")
        start_shares = item.get("baseline_shares")
        end_shares = item.get("valuation_date_shares")
        if not number(start_shares) or start_shares < 0 or not number(end_shares) or end_shares < 0:
            errors.append(f"{prefix} share values must be non-negative numbers")
            continue
        calculated = float(start_shares)
        actions = item.get("actions")
        if not isinstance(actions, list):
            errors.append(f"{prefix}.actions must be a list")
            actions = []
        class_action_ids: set[str] = set()
        for j, action in enumerate(actions):
            ap = f"{prefix}.actions[{j}]"
            if not isinstance(action, dict) or not nonempty(action.get("action_id")):
                errors.append(f"{ap}.action_id is required")
                continue
            action_id = action["action_id"]
            if action_id in bridge_action_ids:
                errors.append(f"duplicate bridge action_id: {action_id}")
            bridge_action_ids.add(action_id)
            class_action_ids.add(action_id)
            announced = parse_date(action.get("announcement_date"), f"{ap}.announcement_date", errors)
            effective = parse_date(action.get("effective_date"), f"{ap}.effective_date", errors)
            if cutoff_date and announced and announced > cutoff_date:
                errors.append(f"{ap} was announced after cutoff")
            if valuation_date and effective and effective > valuation_date:
                errors.append(f"{ap} is not effective by valuation date")
            change = action.get("change_shares")
            if not number(change):
                errors.append(f"{ap}.change_shares must be numeric")
            else:
                calculated += float(change)
            ev = evidence_map.get(action.get("evidence_id"))
            if not ev or ev.get("role") != "corporate_action_announcement" or ev.get("security_id") != sid:
                errors.append(f"{ap} lacks frozen official announcement evidence")
            if action_id not in evidence_text.get(action.get("evidence_id"), ""):
                errors.append(f"{ap}.action_id is absent from announcement text")
            if action.get("action_type") in ACTION_TYPES_REQUIRING_BASIS_REVIEW and valuation_date and effective and effective >= valuation_date - timedelta(days=90):
                recent_basis_actions.add(action_id)
        if class_action_ids != discovered_by_security.get(sid, set()):
            missing = discovered_by_security.get(sid, set()) - class_action_ids
            extra = class_action_ids - discovered_by_security.get(sid, set())
            errors.append(f"{prefix} action bridge does not match frozen search results; missing={sorted(missing)}, extra={sorted(extra)}")
        if abs(calculated - float(end_shares)) > 0.5:
            errors.append(f"{prefix} does not roll forward to valuation_date_shares")
    if bridge_security_ids != set(security_map):
        errors.append("share bridge must contain every security exactly once")

    reviews = payload.get("price_share_basis_reviews")
    if not isinstance(reviews, list):
        errors.append("price_share_basis_reviews must be a list")
        reviews = []
    review_map = {item.get("action_id"): item for item in reviews if isinstance(item, dict)}
    for action_id in recent_basis_actions:
        review = review_map.get(action_id)
        if not review:
            errors.append(f"missing price/share/EPS basis review for {action_id}")
            continue
        for key in ("unadjusted_price_confirmed", "post_action_shares_confirmed", "historical_eps_basis_confirmed"):
            if review.get(key) is not True:
                errors.append(f"basis review {action_id}.{key} must be true")
        if not isinstance(review.get("evidence_ids"), list) or not review.get("evidence_ids"):
            errors.append(f"basis review {action_id}.evidence_ids must be non-empty")

    clearance = payload.get("issue_clearance") if isinstance(payload.get("issue_clearance"), dict) else {}
    if clearance.get("contradictions") != []:
        errors.append("issue_clearance.contradictions must be empty")
    if clearance.get("blocking_issues") != []:
        errors.append("issue_clearance.blocking_issues must be empty")

    checks["local_primary_evidence"] = "FAIL" if any("evidence[" in x or "official" in x or "hash" in x for x in errors) else "PASS"
    checks["search_window"] = "FAIL" if any("searches[" in x or "valid search" in x for x in errors) else "PASS"
    checks["share_bridge"] = "FAIL" if any("share_bridge" in x or "action bridge" in x or "bridge action" in x for x in errors) else "PASS"
    checks["basis_consistency"] = "FAIL" if any("basis review" in x for x in errors) else "PASS"
    checks["issue_clearance"] = "FAIL" if any("issue_clearance" in x for x in errors) else "PASS"
    return {"model_status_code": "PASS" if not errors else "FAIL", "valid": not errors, "checks": checks, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description="验证股本原始证据、检索结果与估值日股数桥")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    raw = args.manifest.read_bytes()
    root = args.root.resolve() if args.root else args.manifest.parent.resolve()
    result = validate(json.loads(raw.decode("utf-8")), root)
    result["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
