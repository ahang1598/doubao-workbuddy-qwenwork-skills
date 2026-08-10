#!/usr/bin/env python3
"""Validate eval contracts and execute assertions against saved responses."""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse


ALLOWED_ASSERTIONS = {
    "route_to",
    "route_not_to",
    "must_ask",
    "must_refuse",
    "must_include",
    "must_not_include",
    "capability",
    "tool_exit",
    "must_stop_after_route",
    "max_clarifying_questions",
    "no_unresolved_fact_binding",
    "numeric_claim_requires_inline_source",
    "prioritize_first_party_sources",
}
CASE_TYPES = {"positive", "edge", "negative", "adversarial"}
TEXT_FIELDS = ("text", "response", "output")
QUESTION = re.compile(r"[?？]|(?:请|需要|能否|是否).{0,18}(?:补充|确认|提供|说明)")
REFUSAL = re.compile(r"不适用|不属于|不能|无法|拒绝|应使用|请改用|建议改用|超出")
FACT_PLACEHOLDER = re.compile(
    r"\{fact:[^}]+\}|\[(?:TODO|TBD|待确认|待补充)[^\]]*\]|<fact[^>]*>",
    re.IGNORECASE,
)
NUMBER = re.compile(
    r"[-+]?\d+(?:\.\d+)?\s*(?:%|个百分点|亿元|万元|倍|美元|人民币|港元|元|万|亿)"
)
URL = re.compile(r"https?://[^\s)\]}>，。；;]+")
INLINE_SOURCE = re.compile(
    r"https?://|(?:来源|source|据|参见|引用)\s*[:：]|\[[^\]]+\]\([^)]+\)",
    re.IGNORECASE,
)
ROUTE_LINE = re.compile(
    r"(?im)^\s*(?:selected[_ -]?skill|route|路由|技能)\s*[:：=]\s*[`\"']?([a-z0-9][\w.-]*)"
)
DOMAIN_HEADING = re.compile(r"(?m)^#{1,3}\s+(?:财务|估值|候选|情景|投资观点|分析)")
FIRST_PARTY_WORDS = re.compile(
    r"官方|公司公告|公司年报|财报|监管|交易所|政府|招股书|SEC filing|annual report|investor relations",
    re.IGNORECASE,
)
FIRST_PARTY_HOST_PARTS = (
    ".gov",
    "sec.gov",
    "hkexnews.hk",
    "sse.com.cn",
    "szse.cn",
    "cninfo.com.cn",
)


def assertion_value(assertion, *aliases):
    """Return a parameter while accepting legacy assertion key names."""
    for key in ("value", "values", *aliases):
        if key in assertion:
            return assertion[key]
    return None


def validate_cases(payload):
    errors = []
    if not isinstance(payload, list):
        return [], ["eval file must be a list"]
    ids = set()
    for index, case in enumerate(payload):
        prefix = f"cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{prefix} must be an object")
            continue
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            errors.append(f"{prefix}.id missing")
        elif case_id in ids:
            errors.append(f"{prefix}.id duplicate: {case_id}")
        else:
            ids.add(case_id)
        if case.get("type") not in CASE_TYPES:
            errors.append(f"{prefix}.type invalid")
        if not isinstance(case.get("prompt"), str) or not case["prompt"].strip():
            errors.append(f"{prefix}.prompt missing")
        assertions = case.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            errors.append(f"{prefix}.assertions missing")
            continue
        for assertion_index, assertion in enumerate(assertions):
            location = f"{prefix}.assertions[{assertion_index}]"
            if not isinstance(assertion, dict):
                errors.append(f"{location} must be an object")
                continue
            kind = assertion.get("type")
            if kind not in ALLOWED_ASSERTIONS:
                errors.append(f"{location}.type unsupported: {kind}")
                continue
            value = assertion_value(
                assertion,
                "skill" if kind.startswith("route_") else "count",
                "route" if kind.startswith("route_") else "count",
            )
            if kind in {"must_include", "must_not_include"}:
                values = value if isinstance(value, list) else [value]
                if not values or any(not isinstance(item, str) or not item for item in values):
                    errors.append(f"{location} requires string value/values")
            elif kind in {"route_to", "route_not_to"} and (
                not isinstance(value, str) or not value
            ):
                errors.append(f"{location} requires value/skill/route")
            elif kind == "max_clarifying_questions" and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0
            ):
                errors.append(f"{location} requires non-negative value/count")
            elif kind in {
                "must_ask",
                "must_refuse",
                "must_stop_after_route",
                "no_unresolved_fact_binding",
                "numeric_claim_requires_inline_source",
                "prioritize_first_party_sources",
            } and not isinstance(value, bool):
                errors.append(f"{location} requires boolean value")
            elif kind == "capability" and not isinstance(value, (str, list, dict)):
                errors.append(f"{location} requires value/values")
            elif kind == "tool_exit" and not isinstance(value, dict):
                if "tool" not in assertion or not any(
                    key in assertion for key in ("expected", "exit_code", "count")
                ):
                    errors.append(f"{location} requires tool and expected/exit_code")
    return payload, errors


def read_response(responses_dir, case_id):
    """Load response text and metadata from <case-id>.md/.txt/.json."""
    text_files = [
        responses_dir / f"{case_id}{suffix}" for suffix in (".md", ".txt")
        if (responses_dir / f"{case_id}{suffix}").is_file()
    ]
    json_path = responses_dir / f"{case_id}.json"
    if len(text_files) > 1:
        raise ValueError("multiple text responses found (.md and .txt)")

    metadata = {}
    json_text = None
    if json_path.is_file():
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        if isinstance(payload, str):
            json_text = payload
        elif isinstance(payload, dict):
            metadata = payload
            for field in TEXT_FIELDS:
                if field in payload:
                    if not isinstance(payload[field], str):
                        raise ValueError(f"JSON field {field!r} must be a string")
                    json_text = payload[field]
                    break
        else:
            raise ValueError("JSON response must be an object or string")

    if text_files:
        text = text_files[0].read_text(encoding="utf-8")
        source = text_files[0]
    elif json_path.is_file() and json_text is not None:
        text = json_text
        source = json_path
    elif json_path.is_file():
        raise ValueError("JSON response has no text/response/output field")
    else:
        raise FileNotFoundError(
            f"no response for {case_id} (.md, .txt, or .json)"
        )
    return text, metadata, str(source)


def selected_route(text, metadata):
    for key in ("selected_skill", "route", "skill"):
        value = metadata.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            for nested_key in ("selected_skill", "skill", "name"):
                if isinstance(value.get(nested_key), str):
                    return value[nested_key]
    match = ROUTE_LINE.search(text)
    return match.group(1) if match else None


def question_count(text):
    return sum(
        1
        for line in text.splitlines()
        if QUESTION.search(line)
        or re.match(r"^\s*(?:[-*]\s*)?\d+[.)、]\s*[^0-9]", line)
    )


def numeric_sources_ok(text):
    for paragraph in re.split(r"\n\s*\n", text):
        if NUMBER.search(paragraph) and not INLINE_SOURCE.search(paragraph):
            return False
    return True


def first_party_sources_present(text, metadata):
    sources = metadata.get("sources")
    if isinstance(sources, list):
        for source in sources:
            if isinstance(source, dict):
                source_type = str(source.get("type", source.get("source_type", "")))
                if re.search(
                    r"first.party|official|regulator|filing|company|exchange|government",
                    source_type,
                    re.IGNORECASE,
                ):
                    return True
            elif isinstance(source, str) and FIRST_PARTY_WORDS.search(source):
                return True
    if FIRST_PARTY_WORDS.search(text):
        return True
    for raw_url in URL.findall(text):
        host = (urlparse(raw_url).hostname or "").lower()
        if any(part in host for part in FIRST_PARTY_HOST_PARTS):
            return True
    return False


def execute_assertion(assertion, text, metadata):
    kind = assertion["type"]
    value = assertion_value(
        assertion,
        "skill" if kind.startswith("route_") else "count",
        "route" if kind.startswith("route_") else "count",
    )
    route = selected_route(text, metadata)

    if kind in {"must_include", "must_not_include"}:
        values = value if isinstance(value, list) else [value]
        found = [item for item in values if item in text]
        passed = len(found) == len(values) if kind == "must_include" else not found
        return passed, f"{'found' if found else 'not found'}: {found or values}"
    if kind == "route_to":
        return route == value, f"selected route: {route!r}"
    if kind == "route_not_to":
        return route is not None and route != value, f"selected route: {route!r}"
    if kind == "must_ask":
        passed = not bool(value) or bool(QUESTION.search(text))
        return passed, f"clarifying questions detected: {question_count(text)}"
    if kind == "must_refuse":
        passed = not bool(value) or bool(REFUSAL.search(text))
        return passed, f"refusal language detected: {bool(REFUSAL.search(text))}"
    if kind == "must_stop_after_route":
        if not value:
            return True, "assertion disabled"
        passed = (
            route is not None
            and bool(REFUSAL.search(text))
            and len(text) <= 800
            and not DOMAIN_HEADING.search(text)
        )
        return passed, f"route={route!r}, chars={len(text)}, refusal={bool(REFUSAL.search(text))}"
    if kind == "max_clarifying_questions":
        count = question_count(text)
        return count <= value, f"clarifying questions: {count}, maximum: {value}"
    if kind == "no_unresolved_fact_binding":
        if not value:
            return True, "assertion disabled"
        match = FACT_PLACEHOLDER.search(text)
        return not match, f"unresolved marker: {match.group(0)!r}" if match else "no unresolved marker"
    if kind == "numeric_claim_requires_inline_source":
        if not value:
            return True, "assertion disabled"
        passed = numeric_sources_ok(text)
        return passed, "numeric claims have inline sources" if passed else "numeric claim lacks inline source"
    if kind == "prioritize_first_party_sources":
        passed = not bool(value) or first_party_sources_present(text, metadata)
        return passed, "first-party source detected" if passed else "no first-party source detected"
    if kind == "capability":
        capabilities = metadata.get("capabilities")
        if not isinstance(capabilities, dict):
            return False, "capabilities metadata unavailable"
        if isinstance(value, dict):
            passed = all(capabilities.get(key) == expected for key, expected in value.items())
        else:
            names = value if isinstance(value, list) else [value]
            passed = all(bool(capabilities.get(name)) for name in names)
        return passed, f"capabilities metadata: {capabilities}"
    if kind == "tool_exit":
        spec = value if isinstance(value, dict) else assertion
        tool = spec.get("tool")
        expected = spec.get("expected", spec.get("exit_code", spec.get("count")))
        tool_results = metadata.get("tool_results", metadata.get("tools"))
        if not isinstance(tool_results, dict):
            return False, "tool_results metadata unavailable"
        actual_record = tool_results.get(tool)
        actual = (
            actual_record.get("exit_code")
            if isinstance(actual_record, dict)
            else actual_record
        )
        return actual == expected, f"tool {tool!r} exit: {actual!r}, expected: {expected!r}"
    return False, f"assertion {kind!r} is not executable"


def write_results(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("evals", help="path to evals.json")
    parser.add_argument("--responses-dir", type=Path)
    parser.add_argument("--results-json", type=Path)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="validate the eval contract without loading responses",
    )
    args = parser.parse_args()

    try:
        payload = json.loads(Path(args.evals).read_text(encoding="utf-8"))
    except Exception as error:
        print(f"ERROR: cannot load evals: {error}")
        return 2

    cases, errors = validate_cases(payload)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        result = {
            "mode": "validation",
            "passed": False,
            "errors": errors,
            "summary": {"cases": len(cases), "errors": len(errors)},
        }
        if args.results_json:
            write_results(args.results_json, result)
        print(f"SUMMARY cases={len(cases)} errors={len(errors)} passed=0 failed=0")
        return 1

    if args.validate_only:
        result = {
            "mode": "validation",
            "passed": True,
            "errors": [],
            "summary": {"cases": len(cases), "errors": 0},
        }
        if args.results_json:
            write_results(args.results_json, result)
        print(f"SUMMARY cases={len(cases)} errors=0 passed={len(cases)} failed=0")
        return 0

    if args.responses_dir is None:
        print("ERROR: --responses-dir is required unless --validate-only is used")
        print(f"SUMMARY cases={len(cases)} errors=1 passed=0 failed={len(cases)}")
        return 2
    if not args.responses_dir.is_dir():
        print(f"ERROR: responses directory does not exist: {args.responses_dir}")
        print(f"SUMMARY cases={len(cases)} errors=1 passed=0 failed={len(cases)}")
        return 2

    case_results = []
    for case in cases:
        case_id = case["id"]
        try:
            text, metadata, source = read_response(args.responses_dir, case_id)
            assertion_results = []
            for assertion in case["assertions"]:
                passed, detail = execute_assertion(assertion, text, metadata)
                assertion_results.append(
                    {"assertion": assertion, "passed": passed, "detail": detail}
                )
            passed = all(item["passed"] for item in assertion_results)
            case_result = {
                "id": case_id,
                "passed": passed,
                "response_file": source,
                "assertions": assertion_results,
            }
        except Exception as error:
            passed = False
            case_result = {
                "id": case_id,
                "passed": False,
                "error": str(error),
                "assertions": [],
            }
        case_results.append(case_result)
        print(f"{'PASS' if passed else 'FAIL'} {case_id}")
        if not passed:
            if case_result.get("error"):
                print(f"  ERROR: {case_result['error']}")
            for row in case_result["assertions"]:
                if not row["passed"]:
                    print(f"  {row['assertion']['type']}: {row['detail']}")

    passed_count = sum(item["passed"] for item in case_results)
    failed_count = len(case_results) - passed_count
    result = {
        "mode": "execution",
        "passed": failed_count == 0,
        "summary": {
            "cases": len(case_results),
            "passed": passed_count,
            "failed": failed_count,
        },
        "cases": case_results,
    }
    if args.results_json:
        write_results(args.results_json, result)
    print(
        f"SUMMARY cases={len(case_results)} errors=0 "
        f"passed={passed_count} failed={failed_count}"
    )
    return 1 if failed_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
