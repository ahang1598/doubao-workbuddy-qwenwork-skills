#!/usr/bin/env python3
import json
import sys

REQUIRED = ["场景、时长、听众和目标", "个人经历、优势、证据和真实限制", "竞选岗位/社团/奖项要求", "想要的语气：自然、正式、幽默、稳重"]


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
