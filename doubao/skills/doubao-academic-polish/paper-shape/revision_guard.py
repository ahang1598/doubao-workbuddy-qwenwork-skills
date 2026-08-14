"""Shared deterministic guard for substantive draft revisions.

This module checks only literal invariants. It does not judge whether a claim,
method, mechanism, or causal interpretation is academically valid.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


CITATION_PATTERNS = (
    r"\[(?:\^)?\d+(?:\s*[-–—,，]\s*\d+)*\]",
    r"[①②③④⑤⑥⑦⑧⑨⑩]",
    r"[\(（][^()（）]{1,100}?(?:(?:19|20)\d{2}[a-z]?|n\.?\s*d\.?)[^()（）]*?[\)）]",
    r"[\(（](?:qtd\.\s+in\s+)?[A-Z][A-Za-z'&.-]+"
    r"(?:\s+(?:[A-Z][A-Za-z'&.-]+|and|for|of|the|on|in|to)){0,11}"
    r"(?:\s+\d+(?:\s*[-–—]\s*\d+)?)?[\)）]",
)
NUMBER_PATTERN = r"(?<![A-Za-z0-9_.])[-+]?\d+(?:[.,]\d+)?(?:\s*(?:%|‰|[A-Za-zµμ°/·^-]+))?"


def text_sha256(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_literal(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def protected_anchors(text: str) -> list[str]:
    anchors: list[str] = []
    for pattern in CITATION_PATTERNS:
        anchors.extend(
            match.group(0).strip()
            for match in re.finditer(pattern, text)
        )
    anchors.extend(match.group(0).strip() for match in re.finditer(NUMBER_PATTERN, text))
    return [anchor for anchor in anchors if normalize_literal(anchor)]


def protected_anchor_counts(text: str) -> Counter[str]:
    return Counter(normalize_literal(anchor) for anchor in protected_anchors(text))


def _load_contract(path: Path) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    if not path.is_file():
        return {}, [f"实质性修订缺少 {path.name}。"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {}, [f"{path.name} 不是可解析的JSON：{exc}"]
    if not isinstance(payload, dict):
        return {}, [f"{path.name} 顶层必须是JSON对象。"]
    preserve = payload.get("preserve")
    changes = payload.get("approved_changes")
    if not isinstance(preserve, list) or not any(normalize_literal(item) for item in preserve):
        failures.append("revision_contract.json 的 preserve 必须列出至少一个需保留的术语、限定语或核心表述。")
    if not isinstance(changes, list):
        failures.append("revision_contract.json 的 approved_changes 必须是数组；无授权变化时使用空数组。")
    return payload, failures


def narrative_year_marker_count(text: str) -> int:
    return len(
        re.findall(
            r"[\(（]\s*(?:(?:19|20)\d{2}[a-z]?|n\.?\s*d\.?)\s*[\)）]",
            text,
            flags=re.I,
        )
    )


def validate_revision(
    revised_text: str,
    original_path: Path,
    contract_path: Path,
) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    result: dict[str, Any] = {
        "original_sha256": "",
        "revision_contract_sha256": "",
        "protected_anchor_count": 0,
    }
    if not original_path.is_file():
        failures.append(f"实质性修订缺少 {original_path.name}，无法对照原稿。")
        return failures, result
    try:
        original = original_path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        failures.append(f"无法读取原稿 {original_path.name}：{exc}")
        return failures, result
    if not original.strip():
        failures.append(f"原稿 {original_path.name} 为空。")
        return failures, result

    contract, contract_failures = _load_contract(contract_path)
    failures.extend(contract_failures)
    result["original_sha256"] = text_sha256(original_path)
    if contract_path.is_file():
        try:
            result["revision_contract_sha256"] = text_sha256(contract_path)
        except (OSError, UnicodeDecodeError):
            pass
    if contract_failures:
        return failures, result

    revised_norm = normalize_literal(revised_text)
    preserve = [str(item) for item in contract.get("preserve", []) if normalize_literal(item)]
    changes = contract.get("approved_changes", [])
    approved_pairs: list[tuple[str, str]] = []
    for index, change in enumerate(changes, start=1):
        if not isinstance(change, dict):
            failures.append(f"approved_changes 第{index}项必须是对象。")
            continue
        original_value = normalize_literal(change.get("from", ""))
        replacement = normalize_literal(change.get("to", ""))
        reason = normalize_literal(change.get("reason", ""))
        authorized = change.get("user_authorized") is True
        if not original_value or not replacement or not reason or not authorized:
            failures.append(
                f"approved_changes 第{index}项必须含非空from/to/reason，且user_authorized=true。"
            )
            continue
        approved_pairs.append((original_value, replacement))

    preserve_keys = {
        normalize_literal(item)
        for item in preserve
        if normalize_literal(item)
    }
    original_norm = normalize_literal(original)
    absent_preserve = sorted(key for key in preserve_keys if key not in original_norm)
    if absent_preserve:
        failures.append(
            "revision_contract.json 的preserve包含原稿中不存在的锚点："
            + " | ".join(absent_preserve[:8])
        )

    def line_requires_full_authorization(line: str) -> bool:
        normalized = normalize_literal(line)
        return bool(
            protected_anchor_counts(line)
            or any(key in normalized for key in preserve_keys)
        )

    original_base_protected = {
        normalize_literal(line)
        for line in original.splitlines()
        if line.strip() and line_requires_full_authorization(line)
    }
    revised_base_protected = {
        normalize_literal(line)
        for line in revised_text.splitlines()
        if line.strip() and line_requires_full_authorization(line)
    }
    linked_original_lines: set[str] = set()
    linked_revised_lines: set[str] = set()
    for original_value, replacement in approved_pairs:
        if (
            original_value in original_base_protected
            or replacement in revised_base_protected
        ):
            linked_original_lines.add(original_value)
            linked_revised_lines.add(replacement)

    original_protected_lines = [
        normalize_literal(line)
        for line in original.splitlines()
        if line.strip()
        and (
            line_requires_full_authorization(line)
            or normalize_literal(line) in linked_original_lines
        )
    ]
    revised_protected_lines = [
        normalize_literal(line)
        for line in revised_text.splitlines()
        if line.strip()
        and (
            line_requires_full_authorization(line)
            or normalize_literal(line) in linked_revised_lines
        )
    ]
    original_lines = Counter(original_protected_lines)
    revised_lines = Counter(revised_protected_lines)
    unchanged = original_lines & revised_lines
    original_lines.subtract(unchanged)
    revised_lines.subtract(unchanged)
    authorized_original_lines: Counter[str] = Counter()
    authorized_revised_lines: Counter[str] = Counter()
    for original_line, revised_line in approved_pairs:
        line_change = (
            original_line in set(original_protected_lines)
            or revised_line in set(revised_protected_lines)
        )
        if not line_change:
            continue
        if original_lines[original_line] < 1:
            failures.append(
                "approved_changes 的完整原行没有可消费的未授权实例："
                + original_line[:160]
            )
            continue
        if revised_lines[revised_line] < 1:
            failures.append(
                "approved_changes 的完整新行未在修订稿中精确出现："
                + revised_line[:160]
            )
            continue
        original_lines[original_line] -= 1
        revised_lines[revised_line] -= 1
        authorized_original_lines[original_line] += 1
        authorized_revised_lines[revised_line] += 1
    missing_lines = [
        line
        for line, count in original_lines.items()
        if count > 0
    ]
    unexpected_lines = [
        line
        for line, count in revised_lines.items()
        if count > 0
    ]
    if missing_lines:
        failures.append(
            "修订稿改写或删除了未获完整行授权的引用、数字或preserve所在行："
            + " | ".join(missing_lines[:8])
        )
    if unexpected_lines:
        failures.append(
            "修订稿新增了未获完整行授权的引用、数字或preserve所在行："
            + " | ".join(unexpected_lines[:8])
        )

    def lines_without_authorized_instances(
        text: str,
        instances: Counter[str],
    ) -> str:
        kept: list[str] = []
        remaining = instances.copy()
        for line in text.splitlines():
            normalized = normalize_literal(line)
            if remaining[normalized] > 0:
                remaining[normalized] -= 1
                continue
            kept.append(line)
        return "\n".join(kept)

    original_atomic_text = lines_without_authorized_instances(
        original,
        authorized_original_lines,
    )
    revised_atomic_text = lines_without_authorized_instances(
        revised_text,
        authorized_revised_lines,
    )
    original_anchors = protected_anchor_counts(original_atomic_text)
    revised_anchors = protected_anchor_counts(revised_atomic_text)
    result["protected_anchor_count"] = sum(original_anchors.values())

    remaining_original = original_anchors.copy()
    remaining_revised = revised_anchors.copy()
    unchanged_anchors = remaining_original & remaining_revised
    remaining_original.subtract(unchanged_anchors)
    remaining_revised.subtract(unchanged_anchors)

    protected_line_pairs = {
        (original_line, revised_line)
        for original_line, revised_line in approved_pairs
        if original_line in set(original_protected_lines)
        or revised_line in set(revised_protected_lines)
    }
    original_atomic_lines = Counter(
        normalize_literal(line)
        for line in original_atomic_text.splitlines()
        if line.strip()
    )
    revised_atomic_lines = Counter(
        normalize_literal(line)
        for line in revised_atomic_text.splitlines()
        if line.strip()
    )
    consumed_original_text: Counter[str] = Counter()
    consumed_revised_text: Counter[str] = Counter()
    for original_value, replacement in approved_pairs:
        if (original_value, replacement) in protected_line_pairs:
            continue
        if (
            original_atomic_lines[original_value]
            <= consumed_original_text[original_value]
        ):
            failures.append(
                "approved_changes 的from未在未授权原稿中精确出现，或实例已被消费："
                + original_value[:160]
            )
            continue
        if (
            revised_atomic_lines[replacement]
            <= consumed_revised_text[replacement]
        ):
            failures.append(
                "approved_changes 的to未在修订稿中精确出现，或实例已被消费："
                + replacement[:160]
            )
            continue
        original_change_anchors = protected_anchor_counts(original_value)
        replacement_anchors = protected_anchor_counts(replacement)
        unavailable_original = [
            anchor
            for anchor, count in original_change_anchors.items()
            if remaining_original[anchor] < count
        ]
        unavailable_replacement = [
            anchor
            for anchor, count in replacement_anchors.items()
            if remaining_revised[anchor] < count
        ]
        if unavailable_original:
            failures.append(
                "approved_changes 的原引用或数字没有可消费的未授权实例："
                + " | ".join(unavailable_original[:8])
            )
            continue
        if unavailable_replacement:
            failures.append(
                "approved_changes 的新引用或数字未在修订稿中精确出现："
                + " | ".join(unavailable_replacement[:8])
            )
            continue
        consumed_original_text[original_value] += 1
        consumed_revised_text[replacement] += 1
        remaining_original.subtract(original_change_anchors)
        remaining_revised.subtract(replacement_anchors)

    missing = [
        f"{anchor}（缺少{count}处）"
        for anchor, count in remaining_original.items()
        if count > 0
    ]
    unexpected = [
        f"{anchor}（新增{count}处）"
        for anchor, count in remaining_revised.items()
        if count > 0
    ]
    if unexpected:
        failures.append(
            "修订稿新增了未获授权的引用或数字："
            + " | ".join(unexpected[:12])
        )

    if missing:
        failures.append(
            "修订稿删除或改写了未获授权的引用、数字或合同锚点："
            + " | ".join(missing[:12])
        )

    return failures, result
