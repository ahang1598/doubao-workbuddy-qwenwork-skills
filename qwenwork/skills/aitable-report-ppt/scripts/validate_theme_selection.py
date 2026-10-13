#!/usr/bin/env python3
"""Validate the explicit visual-theme approval gate before final report generation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


REQUIRED = ("status", "selected_preview", "approved_at", "approval_source", "selection_mode")
SELECTION_MODES = {"preview", "user_named_theme", "reuse_previous", "all_versions"}
# design-selection.json is a contract file: unknown fields are rejected so that
# extra delivery scope can never be smuggled in beside the user's selection
# (e.g. an invented "additional_full_versions"). Delivering every candidate
# theme has exactly one legal form — selection_mode == "all_versions", chosen
# explicitly by the user on the confirmation card in THIS session.
ALLOWED_FIELDS = set(REQUIRED) | {
    "selected_preview_path",
    "selected_preview_sha256",
    "note",
    "requested_changes",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("selection")
    args = parser.parse_args()
    path = Path(args.selection)
    errors: list[str] = []
    if not path.exists():
        errors.append("design-selection.json does not exist; generate three previews and wait for user selection")
        data = {}
    else:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            data = {}
            errors.append(f"cannot read selection: {exc}")
    for key in REQUIRED:
        if not data.get(key):
            errors.append(f"missing required field: {key}")
    unknown = sorted(set(data) - ALLOWED_FIELDS)
    if unknown:
        errors.append(
            f"unknown fields not allowed in design-selection.json: {unknown}. "
            "交付范围只能由 selection_mode 表达；三套都交付的唯一合法形式是用户当轮明确选择 selection_mode=all_versions，"
            "不得通过自造字段（如 additional_full_versions）在选中项之外扩大交付。"
        )
    if data.get("status") != "approved":
        errors.append("status must equal approved")
    if data.get("approval_source") != "user_explicit":
        errors.append("approval_source must equal user_explicit")
    if data.get("selection_mode") not in SELECTION_MODES:
        errors.append(f"selection_mode must be one of {sorted(SELECTION_MODES)}")
    if data.get("selection_mode") == "preview":
        preview_path = data.get("selected_preview_path")
        preview_hash = data.get("selected_preview_sha256")
        if not preview_path or not preview_hash:
            errors.append("preview selection requires selected_preview_path and selected_preview_sha256")
        elif not Path(preview_path).exists():
            errors.append("selected preview file does not exist")
        else:
            actual = hashlib.sha256(Path(preview_path).read_bytes()).hexdigest()
            if actual != preview_hash:
                errors.append("selected preview changed after user approval")
    result = {"valid": not errors, "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
