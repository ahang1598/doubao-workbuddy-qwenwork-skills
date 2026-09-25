#!/usr/bin/env python3
"""Inspect saved Slides lint responses without printing the entire report.

No network access, XML parsing or lint execution. Exit 0 means the selected
report/findings were parsed; it does NOT mean lint passed. Exit 2 means missing,
invalid, unstructured or inconsistent data, or invalid command arguments.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

LEVELS = {"errors": "error", "warnings": "warning", "infos": "info"}


def encoded(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def counts(rows: list[dict]) -> dict:
    c = Counter(row["level"] for row in rows)
    return {level: c[level] for level in ("error", "warning", "info", "unknown")}


def is_report(value: Any) -> bool:
    return isinstance(value, dict) and any(k in value for k in ("summary", "document", "slides"))


class Inspector:
    def __init__(self, payload: Any):
        self.rows: list[dict] = []
        self.pages: list[dict] = []
        self.reports: list[dict] = []
        self.diagnostics: list[dict] = []
        self.metadata: dict = {}
        self.response_ok = None
        self.source_kind = "unknown"
        self.found = False
        self.api_error = False
        self.read(payload)
        if self.source_kind == "lint_rejection" and any(r["reported_summary"].get("status") == "passed" for r in self.reports):
            self.warn("$.error.message", "Lint rejection contains a passed report; response and report conflict.")
        for i, row in enumerate(self.rows, 1):
            row["issue_id"] = f"i{i:06d}"

    def warn(self, source: str, message: str) -> None:
        self.diagnostics.append({"source": source, "message": message})

    def row(self, value: Any, source: str, context: dict, level: str | None = None) -> dict:
        structured = isinstance(value, dict) and isinstance(value.get("code"), str)
        actual_level = value.get("level", level) if isinstance(value, dict) else level
        if actual_level not in LEVELS.values():
            actual_level = "unknown"
        if level and actual_level != level:
            self.warn(source, "Issue level conflicts with its classified list.")
        if not structured or actual_level == "unknown":
            self.warn(source, "Unstructured finding or unknown severity; inspect raw issue.")
        return {**context, "level": actual_level,
                "code": value.get("code") if structured else None,
                "structured": structured, "sources": [source], "issue": value}

    @staticmethod
    def signature(row: dict) -> str:
        # Compare whole issues, not just code/IDs. Infer a missing level from its
        # classified list but retain the original issue verbatim in the output.
        issue = row["issue"]
        if isinstance(issue, dict):
            issue = {**issue, "level": row["level"]}
        return encoded({"scope": row.get("scope"), "slide_number": row.get("slide_number"),
                        "slide_id": row.get("slide_id"), "issue": issue})

    def merge_mirror(self, base: list[dict], mirror: list[dict]) -> list[dict]:
        # Multiset union: preserve repeated occurrences within a list, remove
        # only mirrored occurrences from a second list in the same scope.
        available: dict[str, list[dict]] = {}
        for row in base:
            available.setdefault(self.signature(row), []).append(row)
        consumed: Counter = Counter()
        result = list(base)
        for row in mirror:
            key = self.signature(row)
            n = consumed[key]
            if n < len(available.get(key, [])):
                available[key][n]["sources"].extend(row["sources"])
            else:
                result.append(row)
            consumed[key] += 1
        return result

    def read_list(self, value: Any, source: str, context: dict, level=None) -> list[dict]:
        if not isinstance(value, list):
            self.warn(source, "Expected an issue array; raw value retained.")
            return [self.row(value, source, context, level)]
        return [self.row(v, f"{source}[{i}]", context, level) for i, v in enumerate(value)]

    def container(self, value: Any, source: str, context: dict) -> list[dict]:
        if not isinstance(value, dict):
            self.warn(source, "Expected a problem container; raw value retained.")
            return [self.row(value, source, context)]
        classified = []
        for key, level in LEVELS.items():
            if key in value:
                classified.extend(self.read_list(value[key], source + "." + key, context, level))
        has_classified = any(key in value for key in LEVELS)
        if "issues" in value:
            combined = self.read_list(value["issues"], source + ".issues", context)
            if has_classified and Counter(map(self.signature, classified)) != Counter(map(self.signature, combined)):
                self.warn(source, "Classified and combined lists disagree; unmatched findings retained.")
            return self.merge_mirror(classified, combined)
        if not has_classified:
            self.warn(source, "No recognized issue lists; raw container retained.")
            return [self.row(value, source, context)]
        return classified

    def report(self, value: dict, source: str, context: dict) -> None:
        start = len(self.rows)
        report_id = len(self.reports) + 1
        context = {**context, "report_id": report_id}
        document_context = {**context, "scope": "document", "slide_number": None}
        rows = []
        if "document" in value:
            rows.extend(self.container(value["document"], source + ".document", document_context))
        slides = value.get("slides")
        if not isinstance(slides, list):
            self.warn(source + ".slides", "Missing or invalid slides array.")
            if "slides" in value:
                rows.append(self.row(slides, source + ".slides", context))
            slides = []
        for i, slide in enumerate(slides):
            path = f"{source}.slides[{i}]"
            if not isinstance(slide, dict):
                self.warn(path, "Invalid slide entry; raw value retained.")
                rows.append(self.row(slide, path, {**context, "scope": "slide"}))
                continue
            number = slide.get("slide_number")
            if type(number) is not int or number < 1:
                self.warn(path, "Missing or invalid report slide_number; no page number guessed.")
                number = None
            # A single-page response may bind its ID to its one internal page.
            # A multi-page report must not reuse the wrapper ID on every page.
            sid = slide.get("slide_id", context.get("slide_id") if len(slides) == 1 else None)
            if sid is not None and not isinstance(sid, str):
                self.warn(path + ".slide_id", "Invalid slide ID type; no ID inferred.")
                sid = None
            ctx = {**context, "scope": "slide", "slide_number": number, "slide_id": sid}
            page_rows = self.container(slide, path, ctx)
            rows.extend(page_rows)
            self.pages.append({**ctx, "source": path, "reported_status": slide.get("status"),
                               "parsed_counts": counts(page_rows)})
        report_pages = [p for p in self.pages if p["report_id"] == report_id]
        numbers = [p["slide_number"] for p in report_pages if p["slide_number"] is not None]
        if len(numbers) != len(set(numbers)):
            self.warn(source + ".slides", "Duplicate report slide_number; page selection is ambiguous.")
        # Root `issues` can mirror document issues or a report-wide combined
        # list. Use explicit targets and full content to match nested findings.
        if "issues" in value:
            raw = value["issues"]
            if not isinstance(raw, list):
                self.warn(source + ".issues", "Expected root issues array; raw value retained.")
                raw = [raw]
            mirror = []
            for i, issue in enumerate(raw):
                target = issue.get("target", {}) if isinstance(issue, dict) else {}
                target = target if isinstance(target, dict) else {}
                number = target.get("slide_number")
                matches = [p for p in self.pages if p["report_id"] == report_id and p["slide_number"] == number] if number is not None else []
                if number is not None and len(matches) != 1:
                    self.warn(f"{source}.issues[{i}]", "Root issue refers to an absent or ambiguous report page.")
                ctx = ({**context, "scope": "slide", "slide_number": number,
                        "slide_id": target.get("slide_id", matches[0]["slide_id"] if len(matches) == 1 else None)}
                       if number is not None else document_context)
                mirror.append(self.row(issue, f"{source}.issues[{i}]", ctx))
            rows = self.merge_mirror(rows, mirror)
        for page in report_pages:
            page["parsed_counts"] = counts([r for r in rows if r["scope"] == "slide"
                                            and r["slide_number"] == page["slide_number"]
                                            and r["slide_id"] == page["slide_id"]])
        self.rows.extend(rows)
        summary = value.get("summary")
        if not isinstance(summary, dict):
            self.warn(source + ".summary", "Missing or invalid summary.")
            summary = {}
        parsed = counts(rows)
        consistent = True
        for level in LEVELS.values():
            expected = summary.get(level + "_count")
            if type(expected) is not int or expected < 0 or expected != parsed[level]:
                consistent = False
                self.warn(source + ".summary", f"{level}_count missing/invalid or differs from parsed count {parsed[level]}.")
        if type(summary.get("slide_count")) is not int or summary["slide_count"] != len(slides):
            consistent = False
            self.warn(source + ".summary", "slide_count missing/invalid or differs from returned slides.")
        if not isinstance(summary.get("status"), str):
            self.warn(source + ".summary", "Missing report status.")
        if summary.get("status") == "passed" and parsed["error"]:
            self.warn(source + ".summary", "Reported passed but error findings exist.")
        if "document" not in value and "issues" not in value:
            self.warn(source, "Document issue coverage is unspecified.")
        self.reports.append({"report_id": report_id, "source": source,
                             "reported_summary": summary, "parsed_counts": parsed,
                             "counts_match": consistent, "issue_count": len(self.rows) - start})

    def findings(self, value: Any, source: str, context: dict, depth=0) -> None:
        self.found = True
        if isinstance(value, str) and depth < 2:
            try:
                decoded = json.loads(value)
            except (ValueError, RecursionError):
                pass
            else:
                self.findings(decoded, source + "::<json>", context, depth + 1)
                return
        if is_report(value):
            self.report(value, source, context)
        elif isinstance(value, dict) and any(k in value for k in (*LEVELS, "issues")):
            self.rows.extend(self.container(value, source, context))
        elif isinstance(value, list):
            self.rows.extend(self.read_list(value, source, context))
        else:
            self.rows.append(self.row(value, source, context))

    def read(self, payload: Any) -> None:
        context = {"report_id": None, "scope": "unscoped", "slide_number": None, "slide_id": None}
        if not isinstance(payload, dict):
            raise ValueError("Expected a CLI response object or lint report object.")
        if "ok" not in payload:
            if not is_report(payload):
                raise ValueError("Unrecognized input; expected a CLI envelope or lint report.")
            self.source_kind = "report"
            self.findings(payload, "$", context)
            return
        self.response_ok = payload["ok"]
        if type(self.response_ok) is not bool:
            raise ValueError("Envelope ok must be a boolean.")
        data = payload.get("data", {})
        if isinstance(data, dict):
            self.metadata = {k: data[k] for k in ("xml_presentation_id", "revision_id", "scope", "slide_id", "slide_number") if k in data}
            for key, expected_type in (("slide_id", str), ("scope", str), ("slide_number", int), ("revision_id", int), ("xml_presentation_id", str)):
                if key in data and data[key] is not None and type(data[key]) is not expected_type:
                    self.warn("$.data." + key, "Invalid metadata type; inspect original response.")
            context["slide_id"] = data.get("slide_id")
            if data.get("slide_id") is not None:
                context.update(scope="slide", slide_number=data.get("slide_number"))
        if not self.response_ok:
            error = payload.get("error", {})
            if isinstance(error, dict) and str(error.get("code")) == "4000153":
                self.source_kind = "lint_rejection"
                self.findings(error.get("message"), "$.error.message", context)
            else:
                self.source_kind = "api_error"
                self.api_error = True
                self.rows.append(self.row(error, "$.error", context))
            return
        self.source_kind = "response"
        if not isinstance(data, dict):
            raise ValueError("Envelope data must be an object.")
        if "issues" in data:
            self.findings(data["issues"], "$.data.issues", context)
        if "slide_issues" in data:
            value = data["slide_issues"]
            if not isinstance(value, list):
                self.warn("$.data.slide_issues", "Expected per-slide array; raw value retained.")
                self.findings(value, "$.data.slide_issues", context)
            else:
                self.found = True
                for i, item in enumerate(value):
                    path = f"$.data.slide_issues[{i}]"
                    if isinstance(item, dict) and "issues" in item:
                        ctx = {**context, "scope": "slide", "slide_number": item.get("slide_number"), "slide_id": item.get("slide_id")}
                        self.findings(item["issues"], path + ".issues", ctx)
                    else:
                        self.warn(path, "Unrecognized per-slide wrapper; raw value retained.")
                        self.rows.append(self.row(item, path, context))

    @property
    def status(self) -> str:
        if self.api_error:
            return "api_error"
        if self.diagnostics:
            return "partial"
        if not self.found:
            return "no_report"
        # A passed report cannot certify additional loose findings elsewhere in
        # the same envelope (e.g. data.slide_issues next to data.issues).
        return "parsed" if self.reports and all(r["report_id"] is not None for r in self.rows) else "findings_only"


def select_rows(rows: list[dict], args) -> list[dict]:
    return [r for r in rows
            if (not args.document or r["scope"] == "document")
            and (not args.slide_number or r["scope"] == "slide" and r["slide_number"] in args.slide_number)
            and (not args.slide_id or r["slide_id"] in args.slide_id)
            and (not args.level or r["level"] in args.level)
            and (not args.code or r["code"] in args.code)
            and (not args.issue_id or r["issue_id"] in args.issue_id)]


def paginate(items: list, offset: int, limit: int, max_chars: int | None = None) -> tuple[list, dict]:
    if offset > len(items):
        raise ValueError(f"offset {offset} exceeds selected total {len(items)}.")
    out = []
    chars = 0
    oversized = None
    for item in items[offset:offset + limit]:
        size = len(json.dumps(item, ensure_ascii=False, indent=2))
        if max_chars is not None and chars + size > max_chars:
            if not out:
                oversized = item.get("issue_id") if isinstance(item, dict) else None
            break
        out.append(item)
        chars += size
    end = offset + len(out)
    return out, {"total": len(items), "offset": offset, "returned": len(out),
                 "has_more": end < len(items), "next_offset": end if end < len(items) else None,
                 "oversized_issue_id": oversized}


def render(inspector: Inspector, args) -> dict:
    known_pages = {p["slide_number"] for p in [*inspector.pages, *inspector.rows] if type(p["slide_number"]) is int}
    known_ids = {p["slide_id"] for p in [*inspector.pages, *inspector.rows] if isinstance(p["slide_id"], str)}
    if isinstance(inspector.metadata.get("slide_id"), str):
        known_ids.add(inspector.metadata["slide_id"])
    if set(args.slide_number) - known_pages:
        raise ValueError("Requested slide-number is not present in this report; no page was inferred.")
    if set(args.slide_id) - known_ids:
        raise ValueError("Requested slide-id is not explicitly present; use the report page number with the XML index.")
    if set(args.issue_id) - {r["issue_id"] for r in inspector.rows}:
        raise ValueError("Unknown issue-id for this input file.")
    selected = select_rows(inspector.rows, args)
    totals = counts(inspector.rows)
    statuses = list(dict.fromkeys(r["reported_summary"].get("status") for r in inspector.reports
                                 if isinstance(r["reported_summary"].get("status"), str)))
    result = {"schema_version": "1.0", "mode": "details" if args.details else "summary",
              "inspection_status": inspector.status, "response_ok": inspector.response_ok,
              "source_kind": inspector.source_kind, "metadata": inspector.metadata,
              "lint_status": statuses[0] if inspector.status == "parsed" and len(statuses) == 1 else "unknown",
              "parsed_counts": totals, "issue_total": len(inspector.rows),
              "document_issue_total": sum(r["scope"] == "document" for r in inspector.rows),
              "selected_issue_total": len(selected), "report_total": len(inspector.reports),
              "diagnostic_total": len(inspector.diagnostics),
              "diagnostics": inspector.diagnostics if args.output else inspector.diagnostics[:10],
              "diagnostics_truncated": not bool(args.output) and len(inspector.diagnostics) > 10,
              "notice": "Parsing/reading a summary is not lint approval. Read relevant details and document issues."}
    if args.details:
        rows, paging = paginate(selected, args.offset, args.limit, None if args.output else args.max_chars)
        result.update(issues=rows, pagination=paging)
        if paging["oversized_issue_id"]:
            result["next_action"] = "Single issue exceeds stdout budget; use --issue-id with --details --output, or raise --max-chars. No issue text was truncated."
        elif paging["has_more"]:
            result["next_action"] = "Repeat identical filters with pagination.next_offset."
        else:
            result["next_action"] = "Selected details complete; check document issues and any excluded levels/pages."
    else:
        # Page index is paged. Report metadata and diagnostics are bounded on
        # stdout; a saved summary retains their complete lists.
        pages = [p for p in inspector.pages if (not args.slide_number or p["slide_number"] in args.slide_number)
                 and (not args.slide_id or p["slide_id"] in args.slide_id)]
        result["pages"], result["page_pagination"] = paginate(pages, args.offset, args.limit)
        result["reports"] = inspector.reports if args.output else inspector.reports[:10]
        result["reports_truncated"] = not bool(args.output) and len(inspector.reports) > 10
        codes = Counter(r["code"] or "<unstructured>" for r in selected)
        result["code_counts"] = [{"code": k, "count": v} for k, v in codes.most_common(None if args.output else 20)]
        result["code_counts_truncated"] = not bool(args.output) and len(codes) > 20
        result["next_action"] = "Use --details, optionally --slide-number / --document / --level / --code; follow pagination until has_more is false."
    return result


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Complete saved response JSON (stdout or stderr), or lint report")
    parser.add_argument("--output", type=Path, help="Save selected JSON without truncation; stdout prints a receipt only; does not overwrite")
    parser.add_argument("--details", action="store_true", help="Return complete issue records instead of overview")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--document", action="store_true", help="Select document-level issues")
    scope.add_argument("--slide-number", type=int, nargs="+", action="extend", default=[], help="Internal report page number, not necessarily deck page number")
    parser.add_argument("--slide-id", nargs="+", action="extend", default=[], help="Only IDs explicitly available in response; no XML/ID inference")
    parser.add_argument("--level", choices=[*LEVELS.values(), "unknown"], nargs="+", action="extend", default=[])
    parser.add_argument("--code", nargs="+", action="extend", default=[])
    parser.add_argument("--issue-id", nargs="+", action="extend", default=[], help="Stable within this unchanged input; requires --details")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--max-chars", type=int, default=12000, help="Detail records stdout character budget; --output saves full selected records")
    args = parser.parse_args(argv)
    if args.offset < 0 or args.limit < 1 or args.max_chars < 1 or any(n < 1 for n in args.slide_number):
        parser.error("offset must be >= 0; limit, max-chars and slide-number must be > 0")
    if args.issue_id and not args.details:
        parser.error("--issue-id requires --details")
    if args.slide_id and args.document:
        parser.error("--slide-id cannot be combined with --document")
    return args


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        raw = args.input.read_bytes()
        payload = json.loads(raw.decode("utf-8-sig"))
        inspector = Inspector(payload)
        result = render(inspector, args)
        result.update(source_file=str(args.input), input_sha256=hashlib.sha256(raw).hexdigest())
        code = 0 if inspector.status in ("parsed", "findings_only") else 2
        if args.output:
            # No directory creation or overwriting an input/previous baseline.
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            print(json.dumps({"output": str(args.output), "inspection_status": inspector.status,
                              "lint_status": result["lint_status"], "pagination": result.get("pagination", result.get("page_pagination"))}, ensure_ascii=False))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return code
    except (OSError, ValueError, RecursionError) as error:
        print(json.dumps({"inspection_status": "invalid_input", "lint_status": "unknown",
                          "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
