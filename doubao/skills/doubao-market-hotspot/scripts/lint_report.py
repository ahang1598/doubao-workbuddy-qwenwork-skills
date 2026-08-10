#!/usr/bin/env python3
"""Shared V3 mode-aware report linter. Stdlib only."""

import argparse
import json
import re
from pathlib import Path


COMMON_BANNED = [
    r"\bTODO\b",
    r"\bTBD\b",
    r"待补充",
    r"保证收益",
    r"稳赚(?:不赔)?",
    r"必然?(?:上涨|下跌)",
    r"强烈推荐(?:买入|卖出)",
    r"建议(?:立即|马上)?(?:买入|卖出|加仓|减仓)",
    r"目标价\s*[:：]?\s*[￥$¥]?\d",
    r"仓位\s*[:：]?\s*\d+(?:\.\d+)?%",
]
SENSITIVE = [
    r"\b\d{17}[\dXx]\b",
    r"\b\d{16,19}\b",
    r"\b1[3-9]\d{9}\b",
]
FACT_RE = re.compile(r"\{fact:([A-Za-z0-9_.-]+)\}")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sections(text):
    found = {}
    current = None
    for line in text.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            current = re.sub(r"^\[[^\]]+\]\s*", "", match.group(1)).strip()
            found[current] = []
        elif current is not None:
            found[current].append(line)
    return {name: "\n".join(body).strip() for name, body in found.items()}


def find_section(parsed, aliases):
    for alias in aliases:
        if alias in parsed:
            return alias, parsed[alias]
    return None, ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    parser.add_argument("facts")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parent.parent / "config" / "runtime.json"),
    )
    args = parser.parse_args()
    try:
        text = Path(args.report).read_text(encoding="utf-8")
        facts = load(args.facts)
        config = load(args.config)
    except Exception as error:
        print(f"ERROR: cannot load input: {error}")
        return 2

    errors = []
    warnings = []
    mode = facts.get("meta", {}).get("mode")
    mode_config = config.get("modes", {}).get(mode)
    if not mode_config:
        errors.append(f"unsupported or missing mode: {mode}")
        mode_config = {}
    parsed = sections(text)
    for spec in mode_config.get("required_sections", []):
        name, body = find_section(parsed, spec["aliases"])
        if not name:
            errors.append(f"missing section: {spec['aliases'][0]}")
            continue
        if len(re.sub(r"\s+", "", body)) < spec.get("min_chars", 20):
            errors.append(f"section too thin: {name}")
        if spec.get("fact_binding") and not FACT_RE.search(body):
            errors.append(f"section has no fact binding: {name}")

    patterns = COMMON_BANNED + config.get("banned_patterns", [])
    for pattern in patterns:
        if re.search(pattern, text, re.I):
            errors.append(f"banned pattern: {pattern}")
    if config.get("privacy_scan"):
        for pattern in SENSITIVE:
            if re.search(pattern, text):
                errors.append(f"sensitive data pattern: {pattern}")

    refs = set(FACT_RE.findall(text))
    known = {
        claim.get("claim_id")
        for claim in facts.get("claims", [])
        if isinstance(claim, dict) and claim.get("claim_id")
    }
    for ref in sorted(refs - known):
        errors.append(f"unknown fact binding: {ref}")
    if not refs:
        errors.append("report has no fact bindings")
    if "来源" not in text and "Sources" not in text:
        errors.append("source disclosure missing")
    if (
        "局限" not in text
        and "限制" not in text
        and "Limitations" not in text
    ):
        errors.append("limitations disclosure missing")
    if "不构成" not in text and "does not constitute" not in text.lower():
        errors.append("financial disclaimer missing")

    for item in warnings:
        print("WARNING:", item)
    for item in errors:
        print("ERROR:", item)
    print(
        f"SUMMARY errors={len(errors)} warnings={len(warnings)} "
        f"mode={mode} fact_bindings={len(refs)}"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
