#!/usr/bin/env python3
"""用显式映射分析 git diff 的直接、上下游和共享组件回归范围。"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def changed_files_from_diff(text: str) -> list[str]:
    files = set()
    for line in text.splitlines():
        if line.startswith("+++ b/") or line.startswith("--- a/"):
            value = line[6:].strip()
            if value != "/dev/null":
                files.add(value)
        elif line.startswith("diff --git a/"):
            match = re.match(r"diff --git a/(.*?) b/(.*)$", line)
            if match:
                files.add(match.group(2))
    return sorted(files)


def load_mapping(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("mappings"), list):
        raise ValueError("映射必须是包含 mappings 数组的 JSON 对象")
    return payload


def add_with_reasons(target: dict[str, list[str]], case_ids: list[Any], reason: str) -> None:
    for case_id in case_ids:
        target.setdefault(str(case_id), []).append(reason)


def analyze(changed_files: list[str], mapping: dict[str, Any]) -> dict[str, Any]:
    buckets = {name: {} for name in ("direct", "upstream", "downstream", "shared")}
    matched_files: set[str] = set()
    matched_mapping_ids: set[str] = set()
    for item in mapping.get("mappings", []):
        mapping_id = str(item.get("id", "mapping"))
        patterns = [str(value) for value in item.get("path_globs", [])]
        matches = sorted({path for path in changed_files if any(fnmatch.fnmatch(path, pattern) for pattern in patterns)})
        if not matches:
            continue
        matched_files.update(matches)
        matched_mapping_ids.add(mapping_id)
        reason = f"{mapping_id} 匹配文件：{', '.join(matches)}"
        add_with_reasons(buckets["direct"], item.get("direct_case_ids", []), reason)
        add_with_reasons(buckets["upstream"], item.get("upstream_case_ids", []), reason)
        add_with_reasons(buckets["downstream"], item.get("downstream_case_ids", []), reason)
        add_with_reasons(buckets["shared"], item.get("shared_case_ids", []), reason)

    selected = set().union(*(set(bucket) for bucket in buckets.values()))
    history = mapping.get("failure_history", [])
    historical = {}
    for item in history:
        case_id = str(item.get("case_id", ""))
        if case_id in selected and item.get("status") in {"failed", "flaky", "blocked"}:
            historical.setdefault(case_id, []).append(
                f"历史状态={item.get('status')}；最近失败={item.get('last_failure', 'unknown')}"
            )

    all_cases = {str(value) for value in mapping.get("all_case_ids", [])}
    suggested_not_run = [
        {"case_id": case_id, "reason": "未命中显式变更映射；仍需由发布风险复核"}
        for case_id in sorted(all_cases - selected)
    ]
    unmapped = sorted(set(changed_files) - matched_files)
    confidence = "high" if changed_files and not unmapped else "medium" if matched_files else "low"
    return {
        "schema_version": 1,
        "changed_files": changed_files,
        "matched_mapping_ids": sorted(matched_mapping_ids),
        "direct_cases": [{"case_id": key, "reasons": value} for key, value in sorted(buckets["direct"].items())],
        "upstream_cases": [{"case_id": key, "reasons": value} for key, value in sorted(buckets["upstream"].items())],
        "downstream_cases": [{"case_id": key, "reasons": value} for key, value in sorted(buckets["downstream"].items())],
        "shared_component_cases": [{"case_id": key, "reasons": value} for key, value in sorted(buckets["shared"].items())],
        "historically_risky_cases": [{"case_id": key, "reasons": value} for key, value in sorted(historical.items())],
        "suggested_not_run": suggested_not_run,
        "unmapped_changes": unmapped,
        "risk_omissions": [
            "存在未映射变更，必须人工检查路由、API operation、数据模型和共享组件影响"
        ] if unmapped else [],
        "confidence": confidence,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="分析代码变更对应的测试回归范围")
    parser.add_argument("--mapping", type=Path, required=True, help="显式用例映射 JSON")
    parser.add_argument("--diff-file", type=Path, help="git diff 文件；省略时从 --repo 读取")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--base", default="HEAD~1", help="git diff 基线")
    parser.add_argument("--head", default="HEAD", help="git diff 目标")
    parser.add_argument("--changed-file", action="append", help="直接指定变更文件，可重复")
    parser.add_argument("--out", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        mapping = load_mapping(args.mapping.expanduser().resolve())
        if args.changed_file:
            changed = sorted(set(args.changed_file))
        elif args.diff_file:
            changed = changed_files_from_diff(args.diff_file.read_text(encoding="utf-8"))
        else:
            completed = subprocess.run(
                ["git", "diff", "--no-ext-diff", "--unified=0", args.base, args.head],
                cwd=str(args.repo.expanduser().resolve()), text=True, capture_output=True, check=False,
            )
            if completed.returncode != 0:
                raise ValueError(completed.stderr.strip() or "git diff 失败")
            changed = changed_files_from_diff(completed.stdout)
        result = analyze(changed, mapping)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"变更影响分析失败：{exc}", file=sys.stderr)
        return 2
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.expanduser().resolve().write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
