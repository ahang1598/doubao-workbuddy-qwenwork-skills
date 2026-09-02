#!/usr/bin/env python3
"""Canonical execution-mode profiles for the AI quant research team."""

from __future__ import annotations

from typing import Any


DEFAULT_MODE = "standard"

ALL_STAGES = (
    "00_intake",
    "01_source_replication",
    "02_factor_candidates",
    "03_platform_preflight",
    "04_platform_execution",
    "05_statistical_audit",
    "06_tearsheet",
    "07_final_review",
)

MODE_PROFILES: dict[str, dict[str, Any]] = {
    "fast": {
        "label_zh": "极速体验版",
        "target_minutes": [3, 5],
        "active_stages": (
            "00_intake",
            "01_source_replication",
            "07_final_review",
        ),
        "active_members": ("source-replication-researcher",),
        "source_depth": "formula_only",
        "full_translation": False,
        "max_validation_charts": 4,
        "min_candidates": 0,
        "online_preflight": False,
        "paid_execution": False,
        "statistical_audit": False,
        "environment_cache_ttl_minutes": 60,
        "allowed_conclusions": ("FAST_VALIDATED", "RESEARCH_REJECTED", "BLOCKED"),
    },
    "standard": {
        "label_zh": "标准研究版",
        "target_minutes": [10, 20],
        "active_stages": ALL_STAGES,
        "active_members": (
            "source-replication-researcher",
            "factor-engineer",
            "pandaai-experimenter",
            "overfit-auditor",
            "performance-reporter",
        ),
        "source_depth": "targeted",
        "full_translation": False,
        "max_validation_charts": 6,
        "min_candidates": 4,
        "online_preflight": True,
        "paid_execution": True,
        "statistical_audit": True,
        "environment_cache_ttl_minutes": 10,
        "allowed_conclusions": ("PROMOTE_TO_OOS", "RESEARCH_REJECTED", "BLOCKED"),
    },
    "audit": {
        "label_zh": "完整审计版",
        "target_minutes": [30, 60],
        "active_stages": ALL_STAGES,
        "active_members": (
            "source-replication-researcher",
            "factor-engineer",
            "pandaai-experimenter",
            "overfit-auditor",
            "performance-reporter",
        ),
        "source_depth": "full_replication",
        "full_translation": True,
        "max_validation_charts": 19,
        "min_candidates": 10,
        "online_preflight": True,
        "paid_execution": True,
        "statistical_audit": True,
        "environment_cache_ttl_minutes": 5,
        "allowed_conclusions": ("PROMOTE_TO_OOS", "RESEARCH_REJECTED", "BLOCKED"),
    },
}


def get_profile(mode: str) -> dict[str, Any]:
    normalized = str(mode or DEFAULT_MODE).strip().lower()
    if normalized not in MODE_PROFILES:
        raise ValueError(f"unsupported execution mode: {mode}")
    return MODE_PROFILES[normalized]


def active_stages(mode: str) -> tuple[str, ...]:
    return tuple(get_profile(mode)["active_stages"])

