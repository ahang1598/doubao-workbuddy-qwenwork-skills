#!/usr/bin/env python3
"""Validate an intake against mode-specific runtime requirements."""

import argparse
import json
from pathlib import Path


MISSING = object()


def get_dot_path(payload, path):
    value = payload
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return MISSING
        value = value[part]
    return value


def is_empty(value):
    if value is MISSING or value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return not value
    return False


def validate(intake, config):
    failures = []
    expected_skill = config.get("case_type")
    if intake.get("skill") != expected_skill:
        failures.append(
            f"skill mismatch: expected {expected_skill!r}, got {intake.get('skill')!r}"
        )

    mode = intake.get("mode")
    requirements = config.get("intake_required_inputs", {})
    if mode not in requirements:
        failures.append(f"unsupported mode: {mode!r}")
    else:
        for path in requirements[mode]:
            if is_empty(get_dot_path(intake, path)):
                failures.append(f"missing or empty required input: {path}")

    configured_modes = config.get("modes", {})
    if mode not in configured_modes:
        failures.append(f"mode not declared by runtime: {mode!r}")

    return {"passed": not failures, "failures": failures}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("intake")
    parser.add_argument("runtime_config")
    args = parser.parse_args()
    intake = json.loads(Path(args.intake).read_text(encoding="utf-8"))
    config = json.loads(Path(args.runtime_config).read_text(encoding="utf-8"))
    result = validate(intake, config)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
