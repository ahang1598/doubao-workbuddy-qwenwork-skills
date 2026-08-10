#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def flatten_manifest(manifest):
    paths = set(manifest.get("always", []))
    paths.update(manifest.get("formal_modeling", []))
    paths.update(manifest.get("market_value", []))
    for workflow in manifest.get("workflows", {}).values():
        paths.update(workflow.get("required", []))
        paths.update(workflow.get("conditional", []))
    return sorted(paths)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_root")
    parser.add_argument("--output")
    args = parser.parse_args()

    root = Path(args.skill_root).resolve()
    manifest_path = root / "references" / "reading-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
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
        checks.append({
            "path": relative,
            "total_lines": len(lines),
            "suggested_chunks": chunks,
            "end_marker_found": bool(lines and lines[-1].strip() == marker),
            "declared_in_manifest": relative in declared,
        })

    missing = [relative for relative in declared if not (root / relative).is_file()]
    missing_markers = [item["path"] for item in checks if not item["end_marker_found"]]
    undeclared = [item["path"] for item in checks if not item["declared_in_manifest"]]
    result = {
        "skill_root": str(root),
        "manifest_version": manifest.get("version"),
        "chunk_lines": chunk_lines,
        "markdown_file_count": len(markdown_files),
        "missing_declared_files": missing,
        "missing_end_markers": missing_markers,
        "undeclared_markdown_files": undeclared,
        "files": checks,
    }
    result["status"] = "PASS" if not missing and not missing_markers and not undeclared else "FAIL"
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    print(output)
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
