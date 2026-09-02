#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""global-legal-research 的离线 + LDH 实际环境 UAT。

脚本只调用技能公开 CLI，不读取、不打印任何鉴权环境变量。

用法：
  python tests/run_live_uat.py --mode offline
  python tests/run_live_uat.py --mode smoke
  python tests/run_live_uat.py --mode full --output /tmp/ldh-uat-report.json
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time


SKILL_ROOT = Path(__file__).resolve().parents[1]
RESOLVER = SKILL_ROOT / "scripts" / "jurisdiction_resolver.py"
CLIENT = SKILL_ROOT / "scripts" / "ldh_client.py"


def _short(value, limit=500):
    text = str(value or "")
    return text if len(text) <= limit else text[:limit] + "…"


def _run_json(script, arguments, timeout):
    command = [sys.executable, str(script), *arguments]
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=SKILL_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "command": [script.name, *arguments],
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            "error": "timeout",
        }

    elapsed_ms = int((time.monotonic() - started) * 1000)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "command": [script.name, *arguments],
            "elapsed_ms": elapsed_ms,
            "returncode": completed.returncode,
            "error": "non_json_output",
            "stdout": _short(completed.stdout),
            "stderr": _short(completed.stderr),
        }
    return {
        "ok": completed.returncode == 0,
        "command": [script.name, *arguments],
        "elapsed_ms": elapsed_ms,
        "payload": payload,
        "stderr": _short(completed.stderr),
    }


def _country_codes(value):
    found = set()
    if isinstance(value, str):
        found.add(value)
    elif isinstance(value, list):
        for item in value:
            found.update(_country_codes(item))
    elif isinstance(value, dict):
        for key in ("code", "country", "country_code", "countryCode"):
            if value.get(key):
                found.add(str(value[key]))
        for key in ("coverage", "countries", "data", "items", "results"):
            if key in value:
                found.update(_country_codes(value[key]))
        if not found:
            for key in value:
                if len(str(key)) in (2, 3, 4):
                    found.add(str(key))
    return found


def _source_ids(value):
    found = []
    if isinstance(value, str):
        if "/" in value:
            found.append(value)
    elif isinstance(value, list):
        for item in value:
            found.extend(_source_ids(item))
    elif isinstance(value, dict):
        for key in ("source", "source_id", "sourceId", "id"):
            raw = value.get(key)
            if isinstance(raw, str) and "/" in raw:
                found.append(raw)
        for nested in value.values():
            if isinstance(nested, (dict, list)):
                found.extend(_source_ids(nested))
    return list(dict.fromkeys(found))


def _document_ref(value):
    if isinstance(value, dict):
        source = value.get("source")
        source_id = value.get("source_id") or value.get("sourceId")
        if source and source_id:
            return str(source), str(source_id)
        for nested in value.values():
            if isinstance(nested, (dict, list)):
                found = _document_ref(nested)
                if found:
                    return found
    elif isinstance(value, list):
        for item in value:
            found = _document_ref(item)
            if found:
                return found
    return None


class UAT:
    def __init__(self, timeout):
        self.timeout = timeout
        self.cases = []
        self.search_hits = {}

    def record(self, case_id, name, scope, status, expected, actual, run=None):
        item = {
            "id": case_id,
            "name": name,
            "scope": scope,
            "status": status,
            "expected": expected,
            "actual": actual,
        }
        if run:
            item["command"] = run.get("command")
            item["elapsed_ms"] = run.get("elapsed_ms")
        self.cases.append(item)

    def resolver_case(
        self,
        case_id,
        text,
        expected_status,
        expected_codes,
        expected_ignored=None,
    ):
        run = _run_json(
            RESOLVER,
            ["--text", text],
            self.timeout,
        )
        payload = run.get("payload", {})
        actual_codes = [
            target.get("ldh_country")
            for target in payload.get("targets", [])
        ]
        passed = (
            run.get("ok")
            and payload.get("status") == expected_status
            and actual_codes == expected_codes
            and (
                expected_ignored is None
                or payload.get("ignored_mentions", []) == expected_ignored
            )
        )
        self.record(
            case_id,
            "自然语义法域映射：" + text,
            "offline",
            "PASS" if passed else "FAIL",
            {
                "status": expected_status,
                "codes": expected_codes,
                "ignored_mentions": expected_ignored,
            },
            {
                "status": payload.get("status") or run.get("error"),
                "codes": actual_codes,
                "requires_clarification": payload.get("requires_clarification"),
                "ignored_mentions": payload.get("ignored_mentions", []),
            },
            run,
        )

    def client_status_case(self, case_id, name, args, expected_status):
        run = _run_json(CLIENT, args, self.timeout)
        payload = run.get("payload", {})
        passed = run.get("ok") and payload.get("status") == expected_status
        self.record(
            case_id,
            name,
            "offline",
            "PASS" if passed else "FAIL",
            {"status": expected_status},
            {
                "status": payload.get("status") or run.get("error"),
                "reason": _short(payload.get("reason"), 240),
            },
            run,
        )

    def health(self):
        run = _run_json(CLIENT, ["health"], self.timeout)
        payload = run.get("payload", {})
        status = payload.get("status")
        if run.get("ok") and status == "ok" and payload.get("ldh_available") is True:
            outcome = "PASS"
        elif status in {
            "not_configured", "auth_failed", "quota_exhausted", "unavailable"
        }:
            outcome = "BLOCKED"
        else:
            outcome = "FAIL"
        self.record(
            "LIVE-001",
            "LDH 会话健康检查",
            "live",
            outcome,
            {"status": "ok", "ldh_available": True},
            {
                "status": status or run.get("error"),
                "ldh_available": payload.get("ldh_available"),
                "reason": _short(payload.get("reason"), 240),
            },
            run,
        )
        return outcome == "PASS"

    def coverage(self):
        run = _run_json(CLIENT, ["coverage"], self.timeout)
        payload = run.get("payload", {})
        codes = _country_codes(payload.get("coverage"))
        required = {"EU", "CoE", "UK", "US", "HK"}
        passed = (
            run.get("ok")
            and payload.get("status") == "ok"
            and required.issubset(codes)
        )
        self.record(
            "LIVE-002",
            "实时国家/地区目录",
            "live",
            "PASS" if passed else "FAIL",
            {"status": "ok", "required_codes": sorted(required)},
            {
                "status": payload.get("status") or run.get("error"),
                "codes_count": len(codes),
                "missing": sorted(required - codes),
            },
            run,
        )
        return passed

    def discover(self, code):
        run = _run_json(
            CLIENT,
            ["discover-sources", "--country", code],
            self.timeout,
        )
        payload = run.get("payload", {})
        sources = _source_ids(payload.get("sources"))
        passed = run.get("ok") and payload.get("status") == "ok" and bool(sources)
        self.record(
            "LIVE-DISC-" + code,
            code + " 实时数据源发现",
            "live",
            "PASS" if passed else "FAIL",
            {"status": "ok", "minimum_source_count": 1},
            {
                "status": payload.get("status") or run.get("error"),
                "source_count": len(sources),
                "source_sample": sources[:5],
            },
            run,
        )
        return sources

    def precise_search(self, case_id, code, namespace, query):
        run = _run_json(
            CLIENT,
            [
                "precise-search",
                "--q", query,
                "--country", code,
                "--namespace", namespace,
                "--top-k", "5",
                "--result-detail", "snippet",
            ],
            self.timeout,
        )
        payload = run.get("payload", {})
        audit = payload.get("jurisdiction_audit") or {}
        hits = payload.get("hits") or []
        core_pass = (
            run.get("ok")
            and payload.get("status") == "ok"
            and audit.get("country_validated") is True
            and bool(hits)
        )
        audit_warning = (
            audit.get("rejected_hit_count", 0) > 0
            or audit.get("unverified_country_hit_count", 0) > 0
        )
        status = "WARN" if core_pass and audit_warning else (
            "PASS" if core_pass else "FAIL"
        )
        self.record(
            case_id,
            "%s %s 精准检索" % (code, namespace),
            "live",
            status,
            {
                "status": "ok",
                "country_validated": True,
                "minimum_hit_count": 1,
            },
            {
                "status": payload.get("status") or run.get("error"),
                "hit_count": len(hits),
                "rejected_hit_count": audit.get("rejected_hit_count"),
                "unverified_country_hit_count": audit.get(
                    "unverified_country_hit_count"),
                "reason": _short(payload.get("reason"), 240),
            },
            run,
        )
        if hits:
            self.search_hits[case_id] = hits
        return hits

    def get_first_hit(self, case_id, source_case_id):
        hits = self.search_hits.get(source_case_id) or []
        if not hits:
            self.record(
                case_id,
                "搜索命中全文回取",
                "live",
                "BLOCKED",
                {"status": "ok", "document": "non-empty"},
                {"reason": "前置搜索没有命中"},
            )
            return
        hit = hits[0]
        source = hit.get("source")
        source_id = hit.get("source_id")
        if not source or source_id is None:
            self.record(
                case_id,
                "搜索命中全文回取",
                "live",
                "FAIL",
                {"source": "present", "source_id": "present"},
                {"source": source, "source_id": source_id},
            )
            return
        run = _run_json(
            CLIENT,
            ["get", "--source", str(source), "--source-id", str(source_id)],
            self.timeout,
        )
        payload = run.get("payload", {})
        passed = (
            run.get("ok")
            and payload.get("status") == "ok"
            and bool(payload.get("document"))
        )
        self.record(
            case_id,
            "搜索命中全文回取",
            "live",
            "PASS" if passed else "FAIL",
            {"status": "ok", "document": "non-empty"},
            {
                "status": payload.get("status") or run.get("error"),
                "source": source,
                "source_id": source_id,
                "document_present": bool(payload.get("document")),
                "reason": _short(payload.get("reason"), 240),
            },
            run,
        )

    def filters_for_first_hit(self, case_id, source_case_id, namespace):
        hits = self.search_hits.get(source_case_id) or []
        source = hits[0].get("source") if hits else None
        if not source:
            self.record(
                case_id,
                "实时过滤器发现",
                "live",
                "BLOCKED",
                {"status": "ok"},
                {"reason": "前置搜索没有可用 Source ID"},
            )
            return
        run = _run_json(
            CLIENT,
            [
                "discover-filters",
                "--source", str(source),
                "--namespace", namespace,
            ],
            self.timeout,
        )
        payload = run.get("payload", {})
        if run.get("ok") and payload.get("status") == "ok":
            outcome = "PASS" if payload.get("filters") else "WARN"
        else:
            outcome = "FAIL"
        self.record(
            case_id,
            "实时过滤器发现",
            "live",
            outcome,
            {"status": "ok", "source": source},
            {
                "status": payload.get("status") or run.get("error"),
                "filters_present": bool(payload.get("filters")),
                "reason": _short(payload.get("reason"), 240),
            },
            run,
        )

    def resolve_and_get(self, case_id, reference, country, hint_type):
        run = _run_json(
            CLIENT,
            [
                "resolve",
                "--reference", reference,
                "--hint-country", country,
                "--hint-type", hint_type,
            ],
            self.timeout,
        )
        payload = run.get("payload", {})
        ref = _document_ref(payload.get("resolved"))
        resolved = run.get("ok") and payload.get("status") == "ok" and ref
        self.record(
            case_id + "-R",
            "精确引用解析：" + reference,
            "live",
            "PASS" if resolved else "FAIL",
            {"status": "ok", "source_and_source_id": "present"},
            {
                "status": payload.get("status") or run.get("error"),
                "document_ref": ref,
                "reason": _short(payload.get("reason"), 240),
            },
            run,
        )
        if not ref:
            self.record(
                case_id + "-G",
                "引用解析后的全文回取",
                "live",
                "BLOCKED",
                {"status": "ok"},
                {"reason": "引用解析未返回 source + source_id"},
            )
            return
        source, source_id = ref
        get_run = _run_json(
            CLIENT,
            ["get", "--source", source, "--source-id", source_id],
            self.timeout,
        )
        get_payload = get_run.get("payload", {})
        passed = (
            get_run.get("ok")
            and get_payload.get("status") == "ok"
            and bool(get_payload.get("document"))
        )
        self.record(
            case_id + "-G",
            "引用解析后的全文回取",
            "live",
            "PASS" if passed else "FAIL",
            {"status": "ok", "document": "non-empty"},
            {
                "status": get_payload.get("status") or get_run.get("error"),
                "source": source,
                "source_id": source_id,
                "document_present": bool(get_payload.get("document")),
            },
            get_run,
        )

    def report(self, mode):
        counts = {
            status: sum(1 for item in self.cases if item["status"] == status)
            for status in ("PASS", "WARN", "FAIL", "BLOCKED")
        }
        return {
            "suite": "global-legal-research LDH UAT",
            "mode": mode,
            "generated_at_epoch": int(time.time()),
            "summary": {
                **counts,
                "total": len(self.cases),
                "accepted": counts["FAIL"] == 0 and counts["BLOCKED"] == 0,
            },
            "cases": self.cases,
        }


def run_suite(mode, timeout):
    suite = UAT(timeout)

    suite.resolver_case(
        "MAP-001",
        "比较欧盟和英国关于被遗忘权判例",
        "ok",
        ["EU", "UK"],
    )
    suite.resolver_case(
        "MAP-002",
        "欧洲人权法院第8条隐私权判例",
        "ok",
        ["CoE"],
    )
    suite.resolver_case(
        "MAP-003",
        "加州 CCPA 合规义务",
        "ok",
        ["US"],
    )
    suite.resolver_case(
        "MAP-004",
        "广东省数据条例",
        "ok",
        ["CN"],
    )
    suite.resolver_case(
        "MAP-005",
        "Georgia company law",
        "ambiguous",
        [],
    )
    suite.resolver_case(
        "MAP-006",
        "What remedies are available in a contract dispute?",
        "unresolved",
        [],
    )
    suite.resolver_case(
        "MAP-007",
        "CELEX 32016R0679 Article 17",
        "ok",
        ["EU"],
    )
    suite.resolver_case(
        "MAP-008",
        "企业在俄罗斯申请一张数字认证牌照（CA）需要什么条件",
        "ok",
        ["RU"],
        [{
            "mention": "CA",
            "reason": "domain_acronym",
            "expansion": "Certification Authority",
        }],
    )
    suite.resolver_case(
        "MAP-009",
        "请检索国家代码 CA 的隐私法规",
        "ok",
        ["CA"],
    )
    suite.resolver_case(
        "MAP-010",
        "Compare FR and DE data retention laws",
        "ok",
        ["FR", "DE"],
    )
    suite.client_status_case(
        "NEG-001",
        "非规范 GB 代码必须阻断并提示 UK",
        [
            "precise-search",
            "--q", "data protection",
            "--country", "GB",
            "--namespace", "legislation",
        ],
        "bad_request",
    )
    suite.client_status_case(
        "NEG-002",
        "非法日期必须在联网前阻断",
        [
            "precise-search",
            "--q", "data protection",
            "--country", "EU",
            "--namespace", "legislation",
            "--date-start", "2026-99-99",
        ],
        "bad_request",
    )

    if mode == "offline":
        return suite.report(mode)

    if not suite.health():
        return suite.report(mode)
    suite.coverage()

    for code in ("EU", "CoE", "UK"):
        suite.discover(code)
    if mode == "full":
        for code in ("US", "HK"):
            suite.discover(code)

    suite.precise_search(
        "SEARCH-EU-LEG",
        "EU",
        "legislation",
        "GDPR Article 17 right to erasure",
    )
    suite.precise_search(
        "SEARCH-COE-CASE",
        "CoE",
        "case_law",
        "European Convention Article 8 privacy personal data",
    )
    suite.precise_search(
        "SEARCH-UK-LEG",
        "UK",
        "legislation",
        "Data Protection Act 2018 personal data processing",
    )

    suite.get_first_hit("LIVE-GET-001", "SEARCH-EU-LEG")
    suite.filters_for_first_hit(
        "LIVE-FILTER-001",
        "SEARCH-COE-CASE",
        "case_law",
    )

    if mode == "full":
        suite.precise_search(
            "SEARCH-US-CASE",
            "US",
            "case_law",
            "Carpenter v United States cell-site location Fourth Amendment",
        )
        suite.precise_search(
            "SEARCH-HK-LEG",
            "HK",
            "legislation",
            "Personal Data Privacy Ordinance data user",
        )
        suite.precise_search(
            "SEARCH-US-CA-LEG",
            "US",
            "legislation",
            "California Consumer Privacy Act CCPA California",
        )
        suite.resolve_and_get(
            "RESOLVE-EU-001",
            "ECLI:EU:C:2014:317",
            "EU",
            "case_law",
        )
        suite.resolve_and_get(
            "RESOLVE-UK-001",
            "[2021] UKSC 50",
            "UK",
            "case_law",
        )

    return suite.report(mode)


def main():
    parser = argparse.ArgumentParser(description="global-legal-research LDH UAT")
    parser.add_argument(
        "--mode",
        choices=["offline", "smoke", "full"],
        default="smoke",
        help="offline=仅映射/负向；smoke=核心实时链路；full=扩展法域+引用解析",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="每个子命令超时秒数，默认 60",
    )
    parser.add_argument("--output", help="可选：把 JSON 报告写入指定路径")
    args = parser.parse_args()

    report = run_suite(args.mode, args.timeout)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)

    if report["summary"]["FAIL"]:
        return 1
    if report["summary"]["BLOCKED"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
