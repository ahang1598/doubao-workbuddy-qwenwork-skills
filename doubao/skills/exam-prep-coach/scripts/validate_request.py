#!/usr/bin/env python3
import json
import sys

REQUIRED = ["考试类型与日期", "当前基础、目标分数、每日可用时间", "薄弱模块与历史错题", "教材、题库或课程约束"]


def emit(payload, code=0):
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--help" in argv or "-h" in argv:
        return emit({
            "ok": True,
            "usage": "python3 scripts/validate_request.py < request.json",
            "required": REQUIRED,
            "contract": "valid JSON on stdin; returns code 0 when complete, code 2 when fields are missing or input is invalid"
        }, 0)
    raw = sys.stdin.read()
    if not raw.strip():
        return emit({"ok": False, "error": "empty_stdin", "missing": REQUIRED, "required": REQUIRED}, 2)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return emit({"ok": False, "error": "invalid_json", "message": str(exc), "required": REQUIRED}, 2)
    if not isinstance(data, dict):
        return emit({"ok": False, "error": "expected_object", "required": REQUIRED}, 2)
    missing = [field for field in REQUIRED if not data.get(field)]
    return emit({"ok": not missing, "missing": missing, "required": REQUIRED}, 0 if not missing else 2)


if __name__ == "__main__":
    raise SystemExit(main())
