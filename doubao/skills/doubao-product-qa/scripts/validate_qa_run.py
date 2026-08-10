#!/usr/bin/env python3
"""校验 qa-run.json 的结构、引用、执行证据和发布结论约束。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from qa_run_common import coverage_snapshot, semantic_findings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验 qa-run.json")
    parser.add_argument("qa_run", type=Path, help="qa-run.json 路径")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = args.qa_run.expanduser().resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        result = {"ok": False, "errors": 1, "warnings": 0, "findings": [{"level": "error", "path": str(path), "message": str(exc)}]}
        print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"[ERROR] {exc}")
        return 1
    if not isinstance(payload, dict):
        print(json.dumps({"ok": False, "errors": 1, "warnings": 0, "findings": [{"level": "error", "path": str(path), "message": "根节点必须是对象"}]}, ensure_ascii=False, indent=2))
        return 1

    findings = semantic_findings(payload, path.parent)
    errors = sum(item["level"] == "error" for item in findings)
    warnings = sum(item["level"] == "warning" for item in findings)
    result = {
        "ok": errors == 0,
        "qa_run": str(path),
        "errors": errors,
        "warnings": warnings,
        "coverage": coverage_snapshot(payload) if not errors or isinstance(payload.get("cases"), list) else {},
        "findings": findings,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for item in findings:
            print(f"[{item['level'].upper()}] {item['path']} - {item['message']}")
        print(f"校验完成：errors={errors}, warnings={warnings}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
