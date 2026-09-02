#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把自然语言中的国家、地区、机构和法律引用映射为 LDH jurisdiction code。

本脚本只做确定性解析，不调用网络。运行时允许用 LDH discover/countries 的响应
通过 --allowed-codes-file 限定合法代码；未提供时使用本技能静态目录作为离线回退。
"""

import argparse
import json
import os
import re
import sys
import unicodedata


HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
DEFAULT_RULES = os.path.join(SKILL_ROOT, "references", "jurisdiction-rules.json")
DEFAULT_SOURCES = os.path.join(SKILL_ROOT, "references", "sources-global.md")
ISO3166_PATHS = (
    "/usr/share/zoneinfo/iso3166.tab",
    "/usr/share/misc/iso3166",
)


def _normalize(value):
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    value = re.sub(r"[\s\u3000]+", " ", value)
    return value.strip()


def _emit(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_static_country_names(path):
    """从 sources-global.md 标题提取中文标准名和 LDH 代码。"""
    names = {}
    if not os.path.exists(path):
        return names
    pattern = re.compile(r"^##\s+(.+?)（([A-Za-z]{2,5})）")
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            match = pattern.match(line)
            if match:
                names[_normalize(match.group(1))] = match.group(2)
    return names


def _load_iso_english_names():
    """加载系统 ISO 3166 英文名称；不可用时由显式别名和代码继续工作。"""
    names = {}
    for path in ISO3166_PATHS:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line or line.startswith("#") or "\t" not in line:
                    continue
                code, label = line.rstrip("\n").split("\t", 1)
                names[_normalize(label)] = code
        if names:
            break
    return names


def _extract_codes(value):
    """兼容 countries、coverage、代理外层包装和纯代码数组。"""
    if value is None:
        return set()
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        codes = set()
        for item in value:
            if isinstance(item, str):
                codes.add(item)
            elif isinstance(item, dict):
                for key in ("code", "country", "country_code", "countryCode"):
                    if item.get(key):
                        codes.add(str(item[key]))
        return codes
    if not isinstance(value, dict):
        return set()
    for key in ("countries", "coverage", "data"):
        if key in value:
            found = _extract_codes(value[key])
            if found:
                return found
    keyed = {
        key for key in value
        if re.fullmatch(r"(?:[A-Za-z]{2}|CoE|INTL|OECD|EU|UN|XK)", str(key))
    }
    if keyed:
        return keyed
    return set()


def _canonical_code(raw_code, overrides, allowed_codes):
    if not raw_code:
        return None
    raw = str(raw_code).strip()
    override = overrides.get(raw.upper())
    if override:
        raw = override
    if raw.lower() == "coe":
        raw = "CoE"
    elif raw.upper() in {"INTL", "OECD"}:
        raw = raw.upper()
    else:
        raw = raw.upper()
    if allowed_codes and raw not in allowed_codes:
        return None
    return raw


def _alias_pattern(alias):
    escaped = re.escape(_normalize(alias))
    if re.fullmatch(r"[a-z0-9 .'\-]+", _normalize(alias)):
        return re.compile(r"(?<![a-z0-9])" + escaped + r"(?![a-z0-9])", re.I)
    return re.compile(escaped, re.I)


def _find_matches(text, aliases, category, payload, priority):
    matches = []
    for alias in sorted(set(aliases), key=lambda item: len(_normalize(item)), reverse=True):
        for match in _alias_pattern(alias).finditer(text):
            matches.append({
                "start": match.start(),
                "end": match.end(),
                "length": match.end() - match.start(),
                "priority": priority,
                "category": category,
                "matched_text": match.group(0),
                "payload": payload,
            })
    return matches


def _find_explicit_code_matches(text, code, payload, priority):
    """只识别有法域语境的两字母代码，避免把 CA/AI/IP 等业务缩写当国家。"""
    matches = []
    stripped = text.strip()
    if stripped.casefold() == code.casefold():
        start = text.find(stripped)
        return [{
            "start": max(start, 0),
            "end": max(start, 0) + len(stripped),
            "length": len(stripped),
            "priority": priority,
            "category": "code",
            "matched_text": stripped,
            "payload": payload,
        }]
    token_pattern = re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(code)}(?![A-Za-z0-9])")
    if len(code) != 2:
        accepted = list(token_pattern.finditer(text))
    else:
        context_pattern = re.compile(
            rf"(?:国家代码|地区代码|法域|ISO|country|jurisdiction)"
            rf"\s*(?:code)?\s*[:：=\-]?\s*{re.escape(code)}"
            rf"(?![A-Za-z0-9])",
            re.I,
        )
        context_spans = [
            (match.start(), match.end()) for match in context_pattern.finditer(text)
        ]
        comparison_spans = []
        comparison_marker = re.search(
            r"比较|对比|\bcompare\b", text, re.I)
        if comparison_marker:
            tail = text[comparison_marker.end():]
            code_list = re.match(
                r"\s*[A-Z]{2}"
                r"(?:\s*(?:与|和|及|、|,|，|&|(?i:\band\b|\bvs\.?\b|\bversus\b))"
                r"\s*[A-Z]{2})+",
                tail,
            )
            if code_list:
                comparison_spans.append((
                    comparison_marker.end() + code_list.start(),
                    comparison_marker.end() + code_list.end(),
                ))
        accepted = [
            match for match in token_pattern.finditer(text)
            if any(
                start <= match.start() and match.end() <= end
                for start, end in context_spans + comparison_spans
            )
        ]
    for match in accepted:
        matches.append({
            "start": match.start(),
            "end": match.end(),
            "length": match.end() - match.start(),
            "priority": priority,
            "category": "code",
            "matched_text": match.group(0),
            "payload": payload,
        })
    return matches


def _find_ignored_mentions(text, rules):
    """识别形似国家代码、但在当前语境中属于行业或地区缩写的 token。"""
    ignored = []
    spans = []
    for rule in rules.get("domain_acronyms", []):
        if not re.search(rule["context_pattern"], text, re.I):
            continue
        acronym = rule["acronym"]
        pattern = re.compile(
            rf"(?<![A-Za-z0-9]){re.escape(acronym)}(?![A-Za-z0-9])")
        for match in pattern.finditer(text):
            item = {
                "mention": match.group(0),
                "reason": rule["reason"],
                "expansion": rule["expansion"],
            }
            if item not in ignored:
                ignored.append(item)
            spans.append((match.start(), match.end()))
    return ignored, spans


def _non_overlapping(matches):
    """同一片段优先保留机构/地区规则和最长别名，避免“中国香港”同时命中 CN。"""
    chosen = []
    for item in sorted(matches, key=lambda x: (x["start"], -x["priority"], -x["length"])):
        overlaps = any(not (item["end"] <= old["start"] or item["start"] >= old["end"])
                       for old in chosen)
        if not overlaps:
            chosen.append(item)
    return sorted(chosen, key=lambda x: x["start"])


def _merge_target(targets, candidate):
    key = (candidate["ldh_country"], candidate.get("region"))
    for target in targets:
        if (target["ldh_country"], target.get("region")) == key:
            target["source_hints"] = sorted(set(target["source_hints"] + candidate["source_hints"]))
            target["evidence"].extend(candidate["evidence"])
            target["confidence"] = max(target["confidence"], candidate["confidence"])
            target["matched_by"] = sorted(set(target["matched_by"] + candidate["matched_by"]))
            return
    targets.append(candidate)


def resolve(text, rules, allowed_codes=None, sources_path=DEFAULT_SOURCES):
    normalized = _normalize(text)
    overrides = rules.get("code_overrides", {})
    static_names = _load_static_country_names(sources_path)
    iso_names = _load_iso_english_names()
    effective_allowed = set(allowed_codes or ())
    if not effective_allowed:
        effective_allowed.update(static_names.values())
        effective_allowed.update(item["code"] for item in rules.get("special_jurisdictions", []))

    ignored_mentions, ignored_spans = _find_ignored_mentions(text, rules)
    ambiguous = []
    ambiguous_spans = []
    for rule in rules.get("ambiguous_terms", []):
        for match in _alias_pattern(rule["term"]).finditer(normalized):
            candidates = []
            for item in rule.get("candidates", []):
                code = _canonical_code(item.get("country_code"), overrides, effective_allowed)
                if code:
                    candidates.append({**item, "country_code": code})
            if len(candidates) > 1:
                ambiguous.append({
                    "mention": match.group(0),
                    "candidates": candidates,
                    "reason": "ambiguous_term",
                })
                ambiguous_spans.append((match.start(), match.end()))

    matches = []
    for item in rules.get("institutions", []):
        matches.extend(_find_matches(normalized, item.get("aliases", []), "institution", item, 50))
    for item in rules.get("subnational_regions", []):
        matches.extend(_find_matches(normalized, item.get("aliases", []), "subnational", item, 40))
    for item in rules.get("special_jurisdictions", []):
        aliases = list(item.get("aliases", [])) + [item.get("canonical_name", "")]
        matches.extend(_find_matches(normalized, aliases, "jurisdiction", item, 30))
    for alias, code in {**iso_names, **static_names}.items():
        payload = {"code": code, "canonical_name": alias, "kind": "country", "aliases": [alias]}
        matches.extend(_find_matches(normalized, [alias], "jurisdiction", payload, 20))

    # 显式 LDH/ISO 代码仅在独立且保持大小写的 token 中识别。
    code_candidates = sorted(effective_allowed, key=len, reverse=True)
    for code in code_candidates:
        code_matches = _find_explicit_code_matches(
            text, code, {"code": code}, 10)
        matches.extend(
            item for item in code_matches
            if not any(not (item["end"] <= start or item["start"] >= end)
                       for start, end in ignored_spans)
        )
    for source_code, target_code in overrides.items():
        code_matches = _find_explicit_code_matches(
            text, source_code,
            {"code": target_code, "canonical_name": source_code}, 15)
        matches.extend(
            item for item in code_matches
            if not any(not (item["end"] <= start or item["start"] >= end)
                       for start, end in ignored_spans)
        )

    # 歧义片段不得被普通国家别名静默覆盖。
    matches = [
        item for item in matches
        if not any(not (item["end"] <= start or item["start"] >= end)
                   for start, end in ambiguous_spans)
    ]
    matches = _non_overlapping(matches)

    targets = []
    for match in matches:
        payload = match["payload"]
        if match["category"] == "subnational":
            raw_code = payload.get("parent_code")
            region = payload.get("canonical_name")
            kind = "subnational"
            source_hints = payload.get("source_hints", [])
            query_terms = payload.get("query_terms", [])
        elif match["category"] == "institution":
            raw_code = payload.get("country_code")
            region = None
            kind = "institution"
            source_hints = payload.get("source_hints", [])
            query_terms = []
        else:
            raw_code = payload.get("code")
            region = None
            kind = payload.get("kind", "country")
            source_hints = payload.get("source_hints", [])
            query_terms = []
        code = _canonical_code(raw_code, overrides, effective_allowed)
        if not code:
            continue
        _merge_target(targets, {
            "mention": match["matched_text"],
            "ldh_country": code,
            "entity_level": kind,
            "region": region,
            "query_terms": query_terms,
            "source_hints": source_hints,
            "confidence": 1.0 if match["priority"] >= 30 else 0.96,
            "matched_by": [match["category"] + "_exact"],
            "evidence": [{
                "type": match["category"],
                "text": match["matched_text"],
            }],
        })

    for rule in rules.get("citation_patterns", []):
        if not re.search(rule["pattern"], text, re.I):
            continue
        code = _canonical_code(rule.get("country_code"), overrides, effective_allowed)
        if not code:
            continue
        _merge_target(targets, {
            "mention": rule.get("reason", "citation"),
            "ldh_country": code,
            "entity_level": "citation",
            "region": None,
            "query_terms": [],
            "source_hints": rule.get("source_hints", []),
            "confidence": 0.99,
            "matched_by": [rule.get("reason", "citation_pattern")],
            "evidence": [{"type": "citation_pattern", "text": rule["pattern"]}],
        })

    status = "ok"
    requires_clarification = False
    if ambiguous:
        status = "ambiguous"
        requires_clarification = True
    elif not targets:
        status = "unresolved"
        requires_clarification = True

    return {
        "status": status,
        "targets": targets,
        "ambiguous_mentions": ambiguous,
        "ignored_mentions": ignored_mentions,
        "requires_clarification": requires_clarification,
        "allowed_codes_count": len(effective_allowed),
        "rules_version": rules.get("version"),
    }


def main():
    parser = argparse.ArgumentParser(description="LDH 国家/地区确定性映射器")
    parser.add_argument("--text", required=True, help="用户问题或已抽取的法域文本")
    parser.add_argument("--rules", default=DEFAULT_RULES)
    parser.add_argument("--sources", default=DEFAULT_SOURCES,
                        help="离线国家中文名目录 sources-global.md")
    parser.add_argument("--allowed-codes-file",
                        help="ldh_client.py coverage 的 JSON 输出；用于动态校验")
    args = parser.parse_args()

    try:
        rules = _load_json(args.rules)
        allowed = set()
        if args.allowed_codes_file:
            allowed = _extract_codes(_load_json(args.allowed_codes_file))
        _emit(resolve(args.text, rules, allowed_codes=allowed, sources_path=args.sources))
    except Exception as exc:
        _emit({
            "status": "error",
            "targets": [],
            "ambiguous_mentions": [],
            "ignored_mentions": [],
            "requires_clarification": True,
            "reason": str(exc)[:300],
        })
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
