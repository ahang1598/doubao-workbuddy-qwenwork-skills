"""Numeric fact references in the structured report."""

from __future__ import annotations

import re

from check_facts import CLAIM_ID_RE


NUMERIC_FACT_RE = re.compile(
    r"(?<![A-Za-z0-9])[-+＋−]?\d+(?:,\d{3})*(?:\.\d+)?\s*"
    r"(?:%|pct|pcts|个百分点|bp|bps|亿|亿元|万|万元|元|人民币|美元|港元|台|套|吨|平方米|项|次|倍|x|X)"
)


def collect_claims(facts: dict | None) -> dict[str, dict]:
    if not isinstance(facts, dict):
        return {}
    claims_raw = facts.get("claims")
    if not isinstance(claims_raw, list):
        return {}
    claims: dict[str, dict] = {}
    for item in claims_raw:
        if not isinstance(item, dict):
            continue
        claim_id = item.get("claim_id")
        if isinstance(claim_id, str) and CLAIM_ID_RE.fullmatch(claim_id):
            claims[claim_id] = item
    return claims
