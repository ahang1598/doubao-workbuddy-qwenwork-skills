#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def flatten_manifest(manifest: dict[str, Any]) -> list[str]:
    paths = set(manifest.get("always", []))
    paths.update(manifest.get("formal_modeling", []))
    paths.update(manifest.get("market_value", []))
    for workflow in manifest.get("workflows", {}).values():
        paths.update(workflow.get("required", []))
        paths.update(workflow.get("conditional", []))
    return sorted(paths)


def flatten_external_required(manifest: dict[str, Any]) -> list[dict[str, str]]:
    required: list[dict[str, str]] = []
    for entries in manifest.get("external_required", {}).values():
        for entry in entries:
            skill = str(entry.get("skill", "")).strip()
            path = str(entry.get("path", "")).strip()
            if skill and path and {"skill": skill, "path": path} not in required:
                required.append({"skill": skill, "path": path})
    return required


def chunks_cover(total_lines: int, chunks: Any) -> bool:
    if total_lines <= 0 or not isinstance(chunks, list) or not chunks:
        return False
    expected_start = 1
    for chunk in chunks:
        if not isinstance(chunk, list) or len(chunk) != 2:
            return False
        start, end = chunk
        if not isinstance(start, int) or not isinstance(end, int):
            return False
        if start != expected_start or end < start or end > total_lines:
            return False
        expected_start = end + 1
    return expected_start == total_lines + 1


def validate_external_reading(
    requirements: list[dict[str, str]], ledger: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    entries = ledger.get("external_skills", [])
    if not isinstance(entries, list):
        entries = []
    checks: list[dict[str, Any]] = []
    errors: list[str] = []
    for requirement in requirements:
        matches = [
            item
            for item in entries
            if isinstance(item, dict)
            and item.get("name") == requirement["skill"]
            and item.get("path") == requirement["path"]
        ]
        entry = matches[0] if len(matches) == 1 else None
        total_lines = entry.get("total_lines") if entry else None
        coverage_complete = bool(
            entry
            and isinstance(total_lines, int)
            and chunks_cover(total_lines, entry.get("chunks_read"))
        )
        resolved_path_present = bool(entry and str(entry.get("resolved_path", "")).strip())
        eof_confirmed = bool(
            entry
            and (entry.get("end_marker_found") is True or entry.get("eof_confirmed") is True)
        )
        read_complete = bool(
            entry
            and entry.get("status") == "READ_COMPLETE"
            and eof_confirmed
            and coverage_complete
            and resolved_path_present
        )
        check = {
            **requirement,
            "entry_count": len(matches),
            "resolved_path": entry.get("resolved_path") if entry else None,
            "total_lines": total_lines,
            "chunks_read": entry.get("chunks_read") if entry else None,
            "end_marker_found": entry.get("end_marker_found") if entry else False,
            "eof_confirmed": eof_confirmed,
            "coverage_complete": coverage_complete,
            "status": "PASS" if read_complete else "INCOMPLETE",
        }
        checks.append(check)
        if not read_complete:
            errors.append(
                f"未完整读取外部必读资源：{requirement['skill']}/{requirement['path']}"
            )
    return checks, errors


def validate(skill_root: Path, ledger_path: Path) -> dict[str, Any]:
    root = skill_root.resolve()
    manifest_path = root / "references" / "reading-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    chunk_lines = int(manifest.get("chunk_lines", 100))
    declared = flatten_manifest(manifest)
    markdown_files = sorted(
        ["SKILL.md"]
        + [str(path.relative_to(root)) for path in (root / "references").glob("*.md")]
    )

    checks = []
    for relative in markdown_files:
        path = root / relative
        lines = path.read_text(encoding="utf-8").splitlines()
        marker = f"<!-- END OF FILE: {path.name} -->"
        chunks = []
        for start in range(1, len(lines) + 1, chunk_lines):
            chunks.append([start, min(start + chunk_lines - 1, len(lines))])
        checks.append(
            {
                "path": relative,
                "total_lines": len(lines),
                "suggested_chunks": chunks,
                "end_marker_found": bool(lines and lines[-1].strip() == marker),
                "declared_in_manifest": relative in declared,
            }
        )

    missing = [relative for relative in declared if not (root / relative).is_file()]
    missing_markers = [item["path"] for item in checks if not item["end_marker_found"]]
    undeclared = [item["path"] for item in checks if not item["declared_in_manifest"]]
    external_checks, external_errors = validate_external_reading(
        flatten_external_required(manifest), ledger
    )
    package_errors = []
    if missing:
        package_errors.append("必读文件缺失")
    if missing_markers:
        package_errors.append("必读文件末尾标记缺失")
    if undeclared:
        package_errors.append("存在未在manifest声明的Markdown文件")
    if package_errors:
        status = "FAIL"
    elif external_errors:
        status = "INCOMPLETE"
    else:
        status = "PASS"
    return {
        "skill_root": str(root),
        "ledger_path": str(ledger_path.resolve()),
        "manifest_version": manifest.get("version"),
        "chunk_lines": chunk_lines,
        "markdown_file_count": len(markdown_files),
        "missing_declared_files": missing,
        "missing_end_markers": missing_markers,
        "undeclared_markdown_files": undeclared,
        "external_required": external_checks,
        "errors": package_errors + external_errors,
        "files": checks,
        "status": status,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_root", type=Path)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        result = validate(args.skill_root, args.ledger)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        result = {
            "skill_root": str(args.skill_root.resolve()),
            "ledger_path": str(args.ledger.resolve()),
            "errors": [f"无法验证读取完整性：{exc}"],
            "status": "INCOMPLETE",
        }
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    print(output)
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
