#!/usr/bin/env python3
"""Fast DOCX package and text validation without LibreOffice."""

from __future__ import annotations

import argparse
import json
import posixpath
import sys
import time
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote
from xml.etree import ElementTree as ET


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
DC_NS = "http://purl.org/dc/elements/1.1/"
REQUIRED_PARTS = {
    "[Content_Types].xml",
    "_rels/.rels",
    "word/document.xml",
    "word/styles.xml",
    "docProps/core.xml",
}


def relationship_base(rels_name: str) -> str:
    """Return the directory against which an OOXML relationship target resolves."""
    rels = PurePosixPath(rels_name)
    if rels_name == "_rels/.rels":
        return ""
    if rels.parent.name != "_rels" or not rels.name.endswith(".rels"):
        return ""
    owner_name = rels.name[: -len(".rels")]
    owner = rels.parent.parent / owner_name
    return owner.parent.as_posix()


def inspect_docx(path: Path, extract_dir: Path | None = None) -> dict[str, object]:
    started = time.perf_counter()
    result: dict[str, object] = {
        "file": str(path),
        "ok": False,
        "errors": [],
        "warnings": [],
    }
    errors: list[str] = result["errors"]  # type: ignore[assignment]
    warnings: list[str] = result["warnings"]  # type: ignore[assignment]

    if not path.is_file():
        errors.append("file does not exist")
        result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 3)
        return result

    result["size_bytes"] = path.stat().st_size
    try:
        with zipfile.ZipFile(path) as archive:
            corrupt = archive.testzip()
            if corrupt:
                errors.append(f"CRC failure: {corrupt}")
            names = set(archive.namelist())
            missing = sorted(REQUIRED_PARTS - names)
            if missing:
                errors.append("missing required parts: " + ", ".join(missing))

            parsed: dict[str, ET.Element] = {}
            for name in sorted(names):
                if not (name.endswith(".xml") or name.endswith(".rels")):
                    continue
                try:
                    parsed[name] = ET.fromstring(archive.read(name))
                except ET.ParseError as exc:
                    errors.append(f"invalid XML in {name}: {exc}")

            document = parsed.get("word/document.xml")
            if document is not None:
                paragraphs = document.findall(f".//{{{WORD_NS}}}p")
                tables = document.findall(f".//{{{WORD_NS}}}tbl")
                sections = document.findall(f".//{{{WORD_NS}}}sectPr")
                paragraph_text = []
                for paragraph in paragraphs:
                    text = "".join(node.text or "" for node in paragraph.findall(f".//{{{WORD_NS}}}t"))
                    if text.strip():
                        paragraph_text.append(text)
                extracted = "\n".join(paragraph_text)
                result.update(
                    {
                        "paragraphs": len(paragraphs),
                        "tables": len(tables),
                        "sections": len(sections),
                        "text_chars": len(extracted),
                    }
                )
                if len(extracted.strip()) < 50:
                    errors.append("document contains too little extractable text")
                if not sections:
                    warnings.append("document has no explicit section properties")
                if extract_dir is not None:
                    extract_dir.mkdir(parents=True, exist_ok=True)
                    prefix = path.parent.parent.name if path.parent.name == "assets" else path.parent.name
                    output = extract_dir / f"{prefix}-{path.stem}.txt"
                    output.write_text(extracted + "\n", encoding="utf-8")
                    result["text_output"] = str(output)

            core = parsed.get("docProps/core.xml")
            if core is not None:
                result["author"] = core.findtext(f"{{{DC_NS}}}creator", default="")

            broken_targets: list[str] = []
            for rels_name, root in parsed.items():
                if not rels_name.endswith(".rels"):
                    continue
                base = relationship_base(rels_name)
                for rel in root.findall(f"{{{REL_NS}}}Relationship"):
                    if rel.get("TargetMode") == "External":
                        continue
                    target = unquote(rel.get("Target", "")).split("#", 1)[0]
                    if not target:
                        continue
                    resolved = posixpath.normpath(posixpath.join(base, target)).lstrip("/")
                    if resolved.startswith("../") or resolved not in names:
                        broken_targets.append(f"{rels_name} -> {target}")
            if broken_targets:
                errors.append("broken internal relationships: " + "; ".join(sorted(broken_targets)))
    except zipfile.BadZipFile as exc:
        errors.append(f"invalid DOCX ZIP package: {exc}")
    except OSError as exc:
        errors.append(f"cannot read DOCX: {exc}")

    result["ok"] = not errors
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 3)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docx", nargs="+", type=Path, help="DOCX file(s) to validate")
    parser.add_argument("--extract-dir", type=Path, help="Optional directory for extracted UTF-8 text")
    args = parser.parse_args()

    results = [inspect_docx(path, args.extract_dir) for path in args.docx]
    payload = {"ok": all(item["ok"] for item in results), "documents": results}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
