#!/usr/bin/env python3
"""Source-bound offline analysis, passive workbook export and replay verification."""

import argparse
from decimal import localcontext
import json
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

import cash_workflow
import debt_workflow
import workbook_io
import workflow_inputs as limits
from workflow_inputs import (Budget, Context, LocalResourceLimit, VERSION, check_private,
                             digest, directory_path, dumps, file_receipt, private_directory, private_file,
                             read_json, within)

MAX_OUTPUT_FILE_BYTES = 32 * 1024 * 1024
MAX_OUTPUT_TOTAL_BYTES = 256 * 1024 * 1024
MAX_OUTPUT_ENTRIES = 2048


def compute(data, source_root):
    with localcontext() as context:
        context.prec = 512
        ctx = Context(data, source_root)
        if data["debt_analysis"] is None and data["cash_analysis"] is None:
            raise ValueError("at least one analysis must be supplied")
        result = {"version": VERSION, "as_of": ctx.as_of, "cutoff": "end_of_day",
                  "meta": ctx.meta, "report_metadata": ctx.report_metadata, "sources": ctx.source_manifest(),
                  "debt_analysis": None, "cash_analysis": None}
        if data["debt_analysis"] is not None:
            result["debt_analysis"] = debt_workflow.analyze(ctx, data["debt_analysis"])
        if data["cash_analysis"] is not None:
            result["cash_analysis"] = cash_workflow.analyze(ctx, data["cash_analysis"])
        result["used_evidence_ids"] = sorted(ctx.used)
        result["evidence"] = list(ctx.evidence.values())
        result["semantic_source_mapping_verified"] = False
        result["limitations"] = [
            "Source hashes prove unchanged bytes, not correct semantic extraction or legal interpretation.",
            "Debt and cash-product analyses are separate scopes; balances are not implicitly shared.",
            "Unknowns remain unknown. Scenario assumptions are not confirmed facts.",
            "No search, trade, credit approval or host delivery is performed by this script.",
        ]
        return result, ctx


def literal(value):
    # Code spans disable Markdown links, HTML and autolinks. Pipes/newlines use
    # visible display escapes so untrusted values cannot break the table.
    value = str(value).replace("|", "&#124;").replace("\r", "\\r").replace("\n", "\\n")
    fence = "`" * (1 + max((len(run) for run in re.findall(r"`+", value)), default=0))
    return f"{fence} {value} {fence}"


def report(result):
    lines = ["# Fixed-Income Offline Calculation", "",
             f"Cutoff: {literal(result['as_of'])} (end of day).",
             f"Scope: {literal(result['meta']['scope'])}; currency: {literal(result['meta']['currency'])}; unit: {literal(result['meta']['unit'])}.",
             f"Business timezone: {literal(result['report_metadata']['business_timezone']['value'] or 'unknown')}.",
             f"Material classification: {literal(result['report_metadata']['material_classification']['value'] or 'unknown')}.",
             "", "This is a calculation supplement, not a complete legal/credit opinion or trading instruction.",
             "Original-source semantic mapping still requires human/model review.",
             "Local files are not evidence that the host delivered them to a user.",
             "", "## Result Trace",
             "", "| Result JSON pointer | Exact value |", "| --- | --- |"]
    budget = Budget(MAX_OUTPUT_FILE_BYTES, "report bytes")
    budget.spend(sum(len(line.encode("utf-8")) + 1 for line in lines))
    for key, value in workbook_io.flatten(result):
        text = "unknown" if value is None else dumps(value).strip() if not isinstance(value, str) else value
        line = f"| {literal(key)} | {literal(text)} |"
        budget.spend(len(line.encode("utf-8")) + 1)
        lines.append(line)
    tail = ["", "## Binding", "", "result.json SHA-256: `" + digest(dumps(result).encode()) + "`",
            "Workbook numeric display uses 15 significant digits; result.json retains calculation precision.",
            "Model identities are checked before projection. Workbook Model/Projected/delta columns separate display rounding from model values.",
            "Projection is per row, not a new rolled balance. Unknown interest segments have no formula; partial subtotals are not complete coupons.",
            "Workbook formulas check cash conservation and supplied simple-interest segments, not every financial model.",
            "Text uses inert code spans; displayed pipe/newline escapes are exact only in result.json.",
            ""]
    budget.spend(sum(len(line.encode("utf-8")) + 1 for line in tail))
    lines.extend(tail)
    return "\n".join(lines)


def write_new(path, raw):
    path = Path(path)
    within(len(raw), MAX_OUTPUT_FILE_BYTES, "output file bytes")
    if path.suffix == ".json":
        within(len(raw), limits.MAX_INPUT_BYTES, "replay JSON bytes")
    with private_file(path) as stream:
        stream.write(raw)


def hash_file(path, budget=None):
    return file_receipt(path, MAX_OUTPUT_FILE_BYTES,
                        budget if budget is not None else Budget(MAX_OUTPUT_FILE_BYTES, "file bytes"))


def script_hashes():
    paths = []
    for p in Path(__file__).parent.glob("*.py"):
        within(len(paths) + 1, limits.MAX_SOURCE_FILES, "script count")
        paths.append(p)
    budget = Budget(limits.MAX_TOTAL_SOURCE_BYTES, "script bytes")
    return {p.name: hash_file(p, budget)["sha256"] for p in sorted(paths)}


def copy_sources(ctx, output):
    within(len(ctx.sources), limits.MAX_SOURCE_FILES, "source count")
    total = 0
    for source in ctx.sources.values():
        size = Path(source["resolved_path"]).stat().st_size
        within(size, limits.MAX_SOURCE_BYTES, "source bytes before copy")
        total += size
        within(total, limits.MAX_TOTAL_SOURCE_BYTES, "total source bytes before copy")
    budget = Budget(limits.MAX_TOTAL_SOURCE_BYTES, "total copied source bytes")
    for source in ctx.sources.values():
        target = output / "sources" / source["path"]
        private_directory(target.parent, exist_ok=True)
        with private_file(target) as dest:
            receipt = file_receipt(source["resolved_path"], limits.MAX_SOURCE_BYTES, budget, dest)
        if receipt != {"sha256": source["sha256"], "bytes": source["bytes"]}:
            raise ValueError("source changed during snapshot; partial output retained, not verified")


def output_files(output):
    entries, files = Budget(MAX_OUTPUT_ENTRIES, "output entries"), []

    def walk(directory, depth):
        within(depth, 18, "output directory depth")
        with os.scandir(directory) as children:
            for entry in children:
                entries.spend(1)
                path = Path(entry.path)
                check_private(path)
                if entry.is_dir(follow_symlinks=False):
                    walk(path, depth + 1)
                else:
                    files.append(path)
    walk(output, 0)
    return sorted(files)


def inventory(output, paths):
    total, budget = 0, Budget(MAX_OUTPUT_TOTAL_BYTES, "total output bytes")
    for path in paths:
        size = path.stat().st_size
        within(size, MAX_OUTPUT_FILE_BYTES, "output file bytes")
        total += size
        within(total, MAX_OUTPUT_TOTAL_BYTES, "total output bytes")
    return {str(path.relative_to(output)): hash_file(path, budget) for path in paths}


def verify(output):
    output = directory_path(output).resolve(strict=True)
    check_private(output)
    paths = output_files(output)
    manifest = read_json(output / "manifest.json")
    if (set(manifest) != {"version", "files", "scripts", "status", "host_delivery_confirmed"}
            or manifest["version"] != VERSION or manifest["scripts"] != script_hashes()
            or manifest["status"] != "locally_reconciled" or manifest["host_delivery_confirmed"] is not False):
        raise ValueError("manifest or calculation script binding changed")
    actual = inventory(output, paths)
    actual.pop("manifest.json", None)
    if actual != manifest["files"]:
        raise ValueError("output file set/hash mismatch")
    data = read_json(output / "input.json")
    result, _ = compute(data, output / "sources")
    if dumps(read_json(output / "result.json")) != dumps(result):
        raise ValueError("result replay mismatch")
    with (output / "report.md").open("rb") as stream:
        raw_report = stream.read(MAX_OUTPUT_FILE_BYTES + 1)
    within(len(raw_report), MAX_OUTPUT_FILE_BYTES, "report bytes during replay")
    if raw_report.decode("utf-8") != report(result):
        raise ValueError("report does not match replayed results")
    check = workbook_io.inspect(output / "calculations.xlsx", expected=workbook_io.specification(data, result))
    if check["status"] != "reconciled":
        raise ValueError("workbook not reconciled: " + dumps(check))
    return {"status": "locally_reconciled", "output": str(output),
            "manifest_sha256": hash_file(output / "manifest.json")["sha256"],
            "source_semantics_verified": False, "host_delivery_confirmed": False,
            "verified_file_count": len(actual), "workbook": check}


def generate(input_path, source_root, output):
    output = directory_path(output)
    if output.exists():
        raise ValueError("output directory already exists; never overwrite a prior run")
    # Use the saved wire types from the first calculation onward. Decimal JSON
    # literals serialize as exact strings, so replay must see the same cells.
    data = json.loads(dumps(read_json(input_path)))
    result, ctx = compute(data, source_root)
    input_raw, result_raw = dumps(data).encode(), dumps(result).encode()
    report_raw = report(result).encode()
    private_directory(output)
    copy_sources(ctx, output)
    write_new(output / "input.json", input_raw)
    write_new(output / "result.json", result_raw)
    write_new(output / "report.md", report_raw)
    workbook_io.write(output / "calculations.xlsx", workbook_io.specification(data, result))
    check = workbook_io.inspect(output / "calculations.xlsx", expected=workbook_io.specification(data, result))
    if check["status"] != "reconciled":
        raise ValueError("output verification failed; partial output retained")
    files = inventory(output, output_files(output))
    write_new(output / "manifest.json", dumps({
        "version": VERSION, "files": files, "scripts": script_hashes(),
        "status": "locally_reconciled", "host_delivery_confirmed": False,
    }).encode())
    return verify(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("input", type=Path)
    run.add_argument("--source-root", type=Path, required=True)
    run.add_argument("--out-dir", type=Path, required=True)
    check = sub.add_parser("verify")
    check.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        result = generate(args.input, args.source_root, args.out_dir) if args.command == "run" else verify(args.output)
        print(dumps(result), end="")
    except LocalResourceLimit as exc:
        parser.exit(2, f"Workflow not verified: {exc}; no feasibility or zero-gap conclusion.\n")
    except (ValueError, TypeError, KeyError, OSError, ArithmeticError, ET.ParseError, zipfile.BadZipFile) as exc:
        parser.exit(2, f"Workflow not verified: {exc}\n")


if __name__ == "__main__":
    main()
