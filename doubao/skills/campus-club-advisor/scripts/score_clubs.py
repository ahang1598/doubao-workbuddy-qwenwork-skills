#!/usr/bin/env python3
"""Score campus clubs without blending fit and verification confidence."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from validate_club_packet import validate_input


DEFAULT_WEIGHTS = {
    "interest_fit": 0.30,
    "goal_fit": 0.20,
    "environment_fit": 0.15,
    "skill_fit": 0.15,
    "time_fit": 0.20,
}

VERIFICATION_STATUSES = {
    "verified_current",
    "verified_exists",
    "probable",
    "stale",
    "unverified",
    "conflict",
}

STATE_ORDER = {
    "recommended": 0,
    "recommended_recruitment_unconfirmed": 1,
    "hold_needs_profile": 2,
    "hold_verification": 3,
    "excluded": 4,
}


def _tokens(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {str(value).strip().casefold() for value in values if str(value).strip()}


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _overlap_score(user_values: Any, club_values: Any) -> float | None:
    user = _tokens(user_values)
    club = _tokens(club_values)
    if not user or not club:
        return None
    coverage = len(user & club) / len(user)
    return round(1.0 + 4.0 * coverage, 2)


def _skill_score(profile: dict[str, Any], attributes: dict[str, Any]) -> float | None:
    skills = profile.get("skills") or {}
    contribution = _overlap_score(skills.get("have"), attributes.get("useful_skills"))
    growth = _overlap_score(
        skills.get("want_to_learn"), attributes.get("skill_opportunities")
    )
    known = [score for score in (contribution, growth) if score is not None]
    return round(sum(known) / len(known), 2) if known else None


def _time_score(profile: dict[str, Any], attributes: dict[str, Any]) -> float | None:
    available = _number((profile.get("time") or {}).get("hours_per_week_available"))
    expected = _number(attributes.get("expected_hours_per_week"))
    if available is None or expected is None or available <= 0:
        return None
    ratio = expected / available
    if ratio <= 1.0:
        return 5.0
    if ratio <= 1.25:
        return 3.0
    if ratio <= 1.5:
        return 2.0
    return 1.0


def _vetoes(profile: dict[str, Any], club: dict[str, Any]) -> list[str]:
    attributes = club.get("attributes") or {}
    constraints = profile.get("hard_constraints") or {}
    vetoes: list[str] = []

    expected = _number(attributes.get("expected_hours_per_week"))
    maximum = _number(constraints.get("max_hours_per_week"))
    if expected is not None and maximum is not None and expected > maximum:
        vetoes.append("weekly_hours_exceed_max")

    available_periods = _tokens((profile.get("time") or {}).get("available_periods"))
    meeting_periods = _tokens(attributes.get("meeting_periods"))
    flexible = {"灵活", "待定", "flexible", "tbd"}
    if (
        available_periods
        and meeting_periods
        and not meeting_periods.intersection(flexible)
        and not available_periods.intersection(meeting_periods)
    ):
        vetoes.append("fixed_schedule_conflict")

    excluded_tags = _tokens(constraints.get("exclude_tags"))
    club_tags = _tokens(attributes.get("tags")) | _tokens(
        attributes.get("environment_tags")
    )
    conflicts = sorted(excluded_tags & club_tags)
    if conflicts:
        vetoes.append("excluded_tags:" + ",".join(conflicts))

    max_fee = _number(constraints.get("max_fee"))
    fee = _number(attributes.get("fee"))
    if max_fee is not None and fee is not None and fee > max_fee:
        vetoes.append("fee_exceeds_max")

    cross_campus_ok = constraints.get("cross_campus_ok", True)
    profile_campus = str(profile.get("campus") or "unknown").strip().casefold()
    club_campus = str(club.get("campus") or "unknown").strip().casefold()
    if (
        cross_campus_ok is False
        and profile_campus not in {"", "unknown"}
        and club_campus not in {"", "unknown"}
        and profile_campus != club_campus
    ):
        vetoes.append("campus_mismatch")

    return vetoes


def _weighted_score(
    dimensions: dict[str, float | None], weights: dict[str, float]
) -> tuple[float | None, float]:
    total_weight = sum(weights.values())
    known_weight = sum(weights[key] for key, value in dimensions.items() if value is not None)
    coverage = known_weight / total_weight if total_weight else 0.0
    if not known_weight:
        return None, round(coverage, 3)
    weighted = sum(
        value * weights[key]
        for key, value in dimensions.items()
        if value is not None
    ) / known_weight
    score_100 = (weighted - 1.0) / 4.0 * 100.0
    return round(max(0.0, min(100.0, score_100)), 1), round(coverage, 3)


def _state(
    vetoes: list[str], match_score: float | None, coverage: float, status: str
) -> str:
    if vetoes:
        return "excluded"
    if match_score is None or coverage < 0.60:
        return "hold_needs_profile"
    if status == "verified_current":
        return "recommended"
    if status == "verified_exists":
        return "recommended_recruitment_unconfirmed"
    return "hold_verification"


def score_packet(packet: dict[str, Any]) -> dict[str, Any]:
    profile = packet.get("profile") or {}
    supplied_weights = packet.get("weights") or {}
    weights: dict[str, float] = {}
    for key, default in DEFAULT_WEIGHTS.items():
        raw_value = supplied_weights.get(key, default)
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            raise ValueError(f"weight {key} must be numeric")
        if raw_value < 0:
            raise ValueError(f"weight {key} must be non-negative")
        weights[key] = float(raw_value)
    if not sum(weights.values()):
        raise ValueError("at least one weight must be positive")

    scored: list[dict[str, Any]] = []
    for club in packet.get("clubs") or []:
        attributes = club.get("attributes") or {}
        dimensions = {
            "interest_fit": _overlap_score(
                profile.get("interests"), attributes.get("interests")
            ),
            "goal_fit": _overlap_score(profile.get("goals"), attributes.get("goals")),
            "environment_fit": _overlap_score(
                profile.get("personality_preferences"),
                attributes.get("environment_tags"),
            ),
            "skill_fit": _skill_score(profile, attributes),
            "time_fit": _time_score(profile, attributes),
        }
        vetoes = _vetoes(profile, club)
        match_score, coverage = _weighted_score(dimensions, weights)
        verification = club.get("verification") or {}
        status = str(verification.get("status") or "unverified")
        if status not in VERIFICATION_STATUSES:
            status = "unverified"
        recommendation_state = _state(vetoes, match_score, coverage, status)
        scored.append(
            {
                "id": club.get("id"),
                "name": club.get("name"),
                "school": club.get("school"),
                "campus": club.get("campus", "unknown"),
                "match_score": match_score,
                "coverage": coverage,
                "dimensions": dimensions,
                "vetoes": vetoes,
                "verification": verification,
                "selection_process": club.get("selection_process", "unknown"),
                "recommendation_state": recommendation_state,
                "notes": club.get("notes") or [],
            }
        )

    scored.sort(
        key=lambda item: (
            STATE_ORDER[item["recommendation_state"]],
            -(item["match_score"] if item["match_score"] is not None else -1.0),
            str(item.get("name") or ""),
        )
    )

    return {
        "generated_at": date.today().isoformat(),
        "weights": weights,
        "normalization_notes": packet.get("normalization_notes") or [],
        "clubs": scored,
        "recommended": [
            item
            for item in scored
            if item["recommendation_state"].startswith("recommended")
        ],
        "holds": [
            item
            for item in scored
            if item["recommendation_state"].startswith("hold")
        ],
        "excluded": [
            item for item in scored if item["recommendation_state"] == "excluded"
        ],
    }


def _escape(value: Any) -> str:
    return (
        str(value if value is not None else "未知")
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("|", "\\|")
    )


def _markdown_text(value: Any) -> str:
    return _escape(value).replace("[", "\\[").replace("]", "\\]")


def _safe_url(value: Any) -> str | None:
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value.replace(" ", "%20").replace(")", "%29")
    return None


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# 社团匹配排序",
        "",
        f"生成日期：{result['generated_at']}",
        "",
        "匹配分与真实性状态分开计算；`hold` 表示仍需补画像或核验证据。",
        "",
        "| 社团 | 匹配分 | 覆盖率 | 真实性 | 推荐状态 | 硬约束 |",
        "| --- | ---: | ---: | --- | --- | --- |",
    ]
    for club in result["clubs"]:
        score = "未知" if club["match_score"] is None else f"{club['match_score']:.1f}"
        coverage = f"{club['coverage'] * 100:.0f}%"
        verification = (club.get("verification") or {}).get("status", "unverified")
        vetoes = ", ".join(club["vetoes"]) or "无"
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape(club.get("name")),
                    score,
                    coverage,
                    _escape(verification),
                    _escape(club["recommendation_state"]),
                    _escape(vetoes),
                ]
            )
            + " |"
        )

    lines.extend(["", "## 官方来源", ""])
    for club in result["clubs"]:
        sources = (club.get("verification") or {}).get("sources") or []
        lines.append(f"### {_escape(club.get('name'))}")
        if not sources:
            lines.append("- 未提供可定位来源")
        for source in sources:
            title = _markdown_text(source.get("title") or "来源")
            url = _safe_url(source.get("url"))
            published = _escape(source.get("published_or_updated_at") or "日期未知")
            if url:
                lines.append(f"- [{title}]({url})（{published}）")
            else:
                lines.append(f"- {title}（URL 无效；{published}）")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Input profile and clubs JSON")
    parser.add_argument("--output", required=True, help="Output ranked JSON")
    parser.add_argument(
        "--markdown",
        help="Optional Markdown summary; omitted by default",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        packet = json.loads(Path(args.input).read_text(encoding="utf-8"))
        if not isinstance(packet, dict):
            raise ValueError("input root must be an object")
        errors, _warnings = validate_input(packet)
        if errors:
            raise ValueError("input validation failed: " + "; ".join(errors))
        result = score_packet(packet)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if args.markdown:
        Path(args.markdown).write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({"ok": True, "clubs": len(result["clubs"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
