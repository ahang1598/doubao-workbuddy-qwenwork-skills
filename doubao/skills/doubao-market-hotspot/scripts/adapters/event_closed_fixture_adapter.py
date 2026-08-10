#!/usr/bin/env python3
"""Build a field-driven evidence ledger for closed event-analysis fixtures."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable


INPUT_FILES = {
    "anonymous_media": "anonymous_media.md",
    "social_chain": "social_chain.csv",
    "official_record": "official_record.md",
    "mixed_prices": "mixed_prices.csv",
    "company_exposure": "company_exposure.csv",
}

PRICE_IDENTITY_FIELDS = (
    "instrument",
    "market_type",
    "contract_or_basis",
    "location",
    "currency",
    "unit",
)

EXPOSURE_FIELDS = (
    "business_role",
    "direct_norlandia_feed_share",
    "indirect_dependency",
    "usable_inventory_days",
    "contract_price_mechanism",
    "alternative_or_buffer",
    "qualification_or_switch_time",
    "data_status",
    "transmission_constraint",
)

MISSING_VALUES = {
    "",
    "unknown",
    "not known",
    "not disclosed",
    "none disclosed",
    "n/a",
    "na",
}

UNVERIFIABLE_SOURCE_MARKERS = (
    "unverifiable",
    "unverified",
    "aggregation",
    "aggregator",
    "none",
    "unknown",
)

REQUIRED_QUESTION_TOPICS = [
    {
        "topic": "formal_restriction_document",
        "required_fields": [
            "issuing_authority",
            "covered_product",
            "scope",
            "effective_time",
            "duration",
        ],
    },
    {
        "topic": "independent_original_source",
        "required_fields": [
            "source_identity_or_provenance",
            "first_hand_evidence",
            "independence_from_existing_roots",
        ],
    },
    {
        "topic": "company_buffers",
        "required_fields": [
            "usable_inventory_days",
            "contract_price_mechanism",
            "alternative_or_buffer",
            "qualification_or_switch_time",
        ],
    },
]

REQUIRED_CONFIRMER_TOPICS = [
    {
        "topic": "verifiable_official_or_port_document",
        "required_fields": [
            "issuing_authority",
            "covered_product",
            "scope",
            "effective_time",
            "duration",
        ],
    },
    {
        "topic": "observed_operational_restriction",
        "required_fields": [
            "customs_or_loading_record",
            "record_time",
            "consistency_with_claimed_scope",
        ],
    },
]

REQUIRED_FALSIFIER_TOPICS = [
    {
        "topic": "explicit_competent_authority_denial",
        "required_fields": ["issuing_authority", "explicit_denial", "publication_time"],
    },
    {
        "topic": "normal_operations_after_claimed_effective_time",
        "required_fields": [
            "customs_clearance_record",
            "loading_record",
            "record_time",
        ],
    },
]


class ValidationError(ValueError):
    """Raised when an input fixture cannot be validated safely."""


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValidationError(f"{path.name}: missing CSV header")
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in reader
        ]


def _require_columns(
    rows: list[dict[str, str]], required: Iterable[str], filename: str
) -> None:
    if not rows:
        raise ValidationError(f"{filename}: no data rows")
    missing = sorted(set(required) - set(rows[0]))
    if missing:
        raise ValidationError(f"{filename}: missing columns {', '.join(missing)}")


def _canonical_source_tag(raw: str) -> str | None:
    value = raw.strip().strip("`")
    lowered = value.casefold()
    if not value or any(marker in lowered for marker in UNVERIFIABLE_SOURCE_MARKERS):
        return None
    source_match = re.search(r"\bsource\s+([A-Za-z0-9_.-]+)", value, re.I)
    if source_match:
        return f"Source {source_match.group(1)}"
    relay_prefix = re.match(r"(?:relay|repost|forward)(?:ed)?\s+(?:of|from)\s+(.+)", value, re.I)
    if relay_prefix:
        value = relay_prefix.group(1).strip()
    return value


def _media_source_tags(text: str) -> list[str]:
    tags = []
    pattern = re.compile(
        r"(?:internal\s+)?source\s+tag[^:\n]*:\s*`([^`]+)`", re.I
    )
    for match in pattern.finditer(text):
        tag = _canonical_source_tag(match.group(1))
        if tag:
            tags.append(tag)
    return tags


def build_source_ledger(
    media_text: str, social_rows: list[dict[str, str]]
) -> dict[str, Any]:
    _require_columns(
        social_rows,
        ("record_id", "direct_parent", "original_source_tag"),
        INPUT_FILES["social_chain"],
    )
    media_tags = _media_source_tags(media_text)
    social_tags = [
        tag
        for row in social_rows
        if (tag := _canonical_source_tag(row["original_source_tag"]))
    ]
    roots = sorted(set(media_tags + social_tags), key=str.casefold)
    propagation = [
        {
            "record_id": row["record_id"],
            "direct_parent": row["direct_parent"],
            "original_source": _canonical_source_tag(row["original_source_tag"]),
            "adds_independent_source": (
                row.get("independent_original_source", "").casefold() == "true"
            ),
        }
        for row in social_rows
    ]
    return {
        "independent_original_source_count": len(roots),
        "original_sources": roots,
        "propagation_chain": propagation,
    }


def determine_status(official_text: str) -> dict[str, str]:
    explicit_status = re.search(
        r"(?:event\s+)?status\s+(?:remains|is|=|:)\s*[`'\"]*"
        r"(confirmed|unconfirmed|denied|false|cancelled)",
        official_text,
        re.I,
    )
    if explicit_status:
        status = explicit_status.group(1).casefold()
    else:
        has_confirmation = bool(
            re.search(
                r"\b(?:officially confirmed|confirmed by|issued a .*?(?:order|notice))\b",
                official_text,
                re.I,
            )
        )
        has_denial = bool(
            re.search(r"\b(?:officially denied|explicit(?:ly)? denied)\b", official_text, re.I)
        )
        status = "confirmed" if has_confirmation else "denied" if has_denial else "unconfirmed"

    silence_only = bool(
        re.search(
            r"(?:no confirming or denying|neither confirmation nor denial|"
            r"silence .* neither|no relevant (?:release|notice|circular))",
            official_text,
            re.I,
        )
    )
    return {
        "status": status,
        "official_interpretation": (
            "no_confirmation_or_denial_found"
            if status == "unconfirmed" and silence_only
            else "explicit_status_from_official_record"
        ),
    }


def _parse_utc(value: str, price_id: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValidationError(
            f"{INPUT_FILES['mixed_prices']}: {price_id} invalid timestamp_utc"
        ) from error
    if parsed.tzinfo is None:
        raise ValidationError(
            f"{INPUT_FILES['mixed_prices']}: {price_id} timestamp_utc lacks timezone"
        )
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _price_pair(left: dict[str, str], right: dict[str, str]) -> dict[str, Any]:
    differences = [
        field for field in PRICE_IDENTITY_FIELDS if left[field] != right[field]
    ]
    pair = [left["price_id"], right["price_id"]]
    if differences:
        return {
            "pair": pair,
            "comparable": False,
            "comparison_mode": "forbidden",
            "reasons": [f"different_{field}" for field in differences],
        }

    statuses_match = left["observation_status"] == right["observation_status"]
    relations = {left["relation_to_first_rumor"], right["relation_to_first_rumor"]}
    if not statuses_match:
        mode = "indicative_only"
        reasons = ["different_observation_status", "not_formal_event_return"]
    elif relations == {"before"}:
        mode = "historical_baseline_only"
        reasons = ["both_observations_before_first_rumor"]
    else:
        mode = "like_for_like"
        reasons = []
    return {
        "pair": pair,
        "comparable": True,
        "comparison_mode": mode,
        "reasons": reasons,
    }


def build_price_matrix(price_rows: list[dict[str, str]]) -> dict[str, Any]:
    required = (
        "price_id",
        *PRICE_IDENTITY_FIELDS,
        "price",
        "timestamp_local",
        "timezone",
        "timestamp_utc",
        "observation_status",
        "relation_to_first_rumor",
    )
    _require_columns(price_rows, required, INPUT_FILES["mixed_prices"])
    ids = [row["price_id"] for row in price_rows]
    if len(ids) != len(set(ids)):
        raise ValidationError(f"{INPUT_FILES['mixed_prices']}: duplicate price_id")

    normalized_prices = []
    for row in price_rows:
        try:
            numeric_price = float(row["price"])
        except ValueError as error:
            raise ValidationError(
                f"{INPUT_FILES['mixed_prices']}: {row['price_id']} invalid price"
            ) from error
        normalized_prices.append(
            {
                **row,
                "price": numeric_price,
                "timestamp_utc": _parse_utc(row["timestamp_utc"], row["price_id"]),
            }
        )

    matrix = [_price_pair(left, right) for left, right in combinations(price_rows, 2)]
    comparable_pairs = [item["pair"] for item in matrix if item["comparable"]]
    forbidden = [
        {"pair": item["pair"], "reasons": item["reasons"]}
        for item in matrix
        if not item["comparable"]
    ]
    return {
        "normalized_prices": normalized_prices,
        "comparable_pairs": comparable_pairs,
        "forbidden_comparisons": forbidden,
        "comparison_matrix": matrix,
    }


def _percent(value: str) -> float | None:
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)%\s*", value)
    return float(match.group(1)) if match else None


def build_exposure_requirements(rows: list[dict[str, str]]) -> dict[str, Any]:
    _require_columns(rows, ("company", *EXPOSURE_FIELDS), INPUT_FILES["company_exposure"])
    exposures = []
    gaps = []
    for row in rows:
        direct_share = _percent(row["direct_norlandia_feed_share"])
        indirect = row["indirect_dependency"].casefold() not in {
            "",
            "none",
            "no",
            "not_applicable",
            "not applicable",
        }
        missing_fields = [
            field
            for field in EXPOSURE_FIELDS
            if row[field].strip().casefold() in MISSING_VALUES
        ]
        for field in missing_fields:
            gaps.append(
                {"company": row["company"], "field": field, "value": row[field]}
            )
        exposures.append(
            {
                "company": row["company"],
                "business_role": row["business_role"],
                "direct_feed_share_percent": direct_share,
                "has_direct_exposure": bool(direct_share and direct_share > 0),
                "has_indirect_dependency": indirect,
                "conditional_inputs": {
                    field: row[field]
                    for field in EXPOSURE_FIELDS
                    if field not in {"business_role", "direct_norlandia_feed_share"}
                },
                "missing_fields": missing_fields,
            }
        )
    return {
        "required_exposure_fields": list(EXPOSURE_FIELDS),
        "company_exposures": exposures,
        "exposure_gaps": gaps,
    }


def _load_oracle(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        if len(payload) != 1 or not isinstance(payload[0], dict):
            raise ValidationError("oracle JSON must contain exactly one case")
        payload = payload[0]
    if not isinstance(payload, dict):
        raise ValidationError("oracle JSON must be an object")
    oracle = payload.get("oracle", payload)
    if not isinstance(oracle, dict):
        raise ValidationError("oracle field must be an object")
    return oracle


def _pair_set(pairs: Iterable[Iterable[str]]) -> set[frozenset[str]]:
    return {frozenset(pair) for pair in pairs}


def crosscheck_oracle(result: dict[str, Any], oracle: dict[str, Any]) -> dict[str, Any]:
    expected_status = oracle.get("event_status")
    expected_count = oracle.get("independent_original_source_count")
    price_oracle = oracle.get("price_basis_oracle", {})
    expected_comparable = price_oracle.get("comparable_pairs", [])
    expected_forbidden = price_oracle.get("non_comparable_pairs", [])
    actual_comparable = _pair_set(result["comparable_pairs"])
    actual_forbidden = _pair_set(
        item["pair"] for item in result["forbidden_comparisons"]
    )
    checks = {
        "status_matches": (
            expected_status is None or result["status"] == expected_status
        ),
        "independent_source_count_matches": (
            expected_count is None
            or result["independent_original_source_count"] == expected_count
        ),
        "comparable_pairs_match": (
            not expected_comparable
            or actual_comparable == _pair_set(expected_comparable)
        ),
        "required_forbidden_pairs_present": (
            not expected_forbidden
            or _pair_set(expected_forbidden).issubset(actual_forbidden)
        ),
        "required_question_count_matches": (
            len(result["required_question_topics"])
            == len(oracle.get("required_question_topics", REQUIRED_QUESTION_TOPICS))
        ),
    }
    return {"passed": all(checks.values()), "checks": checks}


def validate_event_evidence(
    input_directory: str | Path, oracle_path: str | Path | None = None
) -> dict[str, Any]:
    directory = Path(input_directory)
    missing = [
        filename
        for filename in INPUT_FILES.values()
        if not (directory / filename).is_file()
    ]
    if missing:
        raise ValidationError(f"missing input files: {', '.join(sorted(missing))}")

    media_text = (directory / INPUT_FILES["anonymous_media"]).read_text(
        encoding="utf-8"
    )
    official_text = (directory / INPUT_FILES["official_record"]).read_text(
        encoding="utf-8"
    )
    social_rows = _read_csv(directory / INPUT_FILES["social_chain"])
    price_rows = _read_csv(directory / INPUT_FILES["mixed_prices"])
    exposure_rows = _read_csv(directory / INPUT_FILES["company_exposure"])

    source = build_source_ledger(media_text, social_rows)
    status = determine_status(official_text)
    prices = build_price_matrix(price_rows)
    exposures = build_exposure_requirements(exposure_rows)
    result: dict[str, Any] = {
        "independent_original_source_count": source[
            "independent_original_source_count"
        ],
        "status": status["status"],
        "comparable_pairs": prices["comparable_pairs"],
        "forbidden_comparisons": prices["forbidden_comparisons"],
        "required_confirmer_topics": REQUIRED_CONFIRMER_TOPICS,
        "required_falsifier_topics": REQUIRED_FALSIFIER_TOPICS,
        "required_question_topics": REQUIRED_QUESTION_TOPICS,
        "source_ledger": source,
        "official_record": status,
        "price_comparability": prices,
        "transmission_requirements": exposures,
    }
    if oracle_path is not None:
        result["oracle_check"] = crosscheck_oracle(
            result, _load_oracle(Path(oracle_path))
        )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate closed-fixture event evidence and emit JSON."
    )
    parser.add_argument(
        "input_directory",
        help="Directory containing the five standard event evidence files.",
    )
    parser.add_argument(
        "--oracle",
        help="Optional V6 case or oracle JSON used for a non-mutating cross-check.",
    )
    parser.add_argument("--output", help="Optional path for the emitted JSON.")
    args = parser.parse_args(argv)
    try:
        result = validate_event_evidence(args.input_directory, args.oracle)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2

    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")
    if result.get("oracle_check", {}).get("passed") is False:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
