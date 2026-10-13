#!/usr/bin/env python3
"""Exercise privacy detections and prove stdout/stderr never echo synthetic values."""

from __future__ import annotations

from validate_output import validate


CASES = [
    ("chinese-name", "测试姓名：张三", {"PRIVATE_LITERAL_PRESENT"}, ["张三"]),
    ("student-id", "学号：TST20260001", {"PRIVATE_LITERAL_PRESENT"}, ["TST20260001"]),
    ("email", "邮箱：synthetic.user@example.invalid", {"PII_EMAIL"}, []),
    ("phone", "手机：13900000000", {"PII_PHONE"}, []),
    ("token", "token_SYNTHETIC_ONLY_000000", {"SECRET_TOKEN"}, []),
    ("home-path", "/Users/SYNTHETIC_TEST_USER/example.txt", {"PATH_HOME"}, []),
    ("private-ipv4", "10.23.45.67", {"PRIVATE_IPV4"}, []),
    ("internal-domain", "service.campus.internal", {"INTERNAL_DOMAIN"}, []),
    ("private-absolute-path", "/private/tmp/campus/input.json", {"PATH_PRIVATE"}, []),
]


def fixture(literals: list[str]) -> dict:
    return {
        "assertions": {
            "required_substrings": [],
            "forbidden_substrings": [],
            "forbidden_regexes": [],
            "max_output_chars": 1000,
            "allow_empty_output": False,
        },
        "privacy": {"scan_standard_patterns": True, "forbidden_literals": literals},
    }


def main() -> int:
    failed = 0
    for case_id, sample, expected, literals in CASES:
        actual = set(validate(fixture(literals), sample))
        passed = expected <= actual
        failed += not passed
        print(f"{case_id} {'PASS' if passed else 'FAIL'} codes={','.join(sorted(actual)) if actual else 'NONE'}")
    print(f"SUMMARY total={len(CASES)} passed={len(CASES)-failed} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
