#!/usr/bin/env python3
"""Finalize a report source markdown for Feishu document delivery.

This is the single command the workflow should run at delivery time:
  python3 scripts/finalize_report.py report.md [facts.json]

It normalizes the source markdown in place, runs lint, and creates a
reader-facing markdown copy where internal fact bindings are converted to
plain [n] source markers. The display markdown is the source for the built-in
Feishu document creation step. DOCX export is optional and only runs when
--docx-output is provided.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def run_step(args: list[str]) -> None:
    subprocess.run([sys.executable, *args], check=True)


def validate_output_paths(markdown_path: Path, display_output: Path, docx_output: Path | None = None) -> None:
    if markdown_path.name.endswith("-display.md"):
        raise SystemExit(
            "[错误] 输入文件看起来是已清理的 display markdown。"
            "请改用保留 {fact:...} 绑定的源 markdown。"
        )
    if display_output == markdown_path:
        raise SystemExit("[错误] display markdown 不能覆盖源 markdown，否则会丢失源稿审计标记。")
    if docx_output is not None and (docx_output == markdown_path or docx_output == display_output):
        raise SystemExit("[错误] DOCX 输出路径不能与源 markdown 或 display markdown 相同。")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Single delivery entry: normalize, lint, and generate display markdown for Feishu delivery."
    )
    parser.add_argument("markdown", help="Source markdown file")
    parser.add_argument("facts", nargs="?", default=None, help="Optional facts.json for lint checks")
    parser.add_argument("--docx-output", default=None, help="Optional DOCX export path; omitted by default")
    parser.add_argument("--display-output", default=None, help="Output display markdown path (default: <stem>-display.md)")
    args = parser.parse_args()

    markdown_path = Path(args.markdown).resolve()
    facts_path = Path(args.facts).resolve() if args.facts else None
    docx_output = Path(args.docx_output).resolve() if args.docx_output else None
    display_output = (
        Path(args.display_output).resolve()
        if args.display_output
        else markdown_path.with_name(f"{markdown_path.stem}-display.md")
    )

    if not markdown_path.exists():
        raise SystemExit(f"[错误] 找不到 Markdown 文件: {markdown_path}")
    if facts_path is not None and not facts_path.exists():
        raise SystemExit(f"[错误] 找不到 facts.json: {facts_path}")
    validate_output_paths(markdown_path, display_output, docx_output)

    run_step([str(SCRIPT_DIR / "normalize_report.py"), str(markdown_path)])

    if facts_path is not None:
        run_step([str(SCRIPT_DIR / "check_facts.py"), str(facts_path)])

    lint_args = [str(SCRIPT_DIR / "lint_report.py"), str(markdown_path)]
    if facts_path is not None:
        lint_args.append(str(facts_path))
    run_step(lint_args)

    display_args = [str(SCRIPT_DIR / "make_display_markdown.py"), str(markdown_path), str(display_output)]
    if facts_path is not None:
        display_args.extend(["--facts", str(facts_path)])
    run_step(display_args)
    if docx_output is not None:
        # Optional export uses the same reader-facing copy as Feishu delivery,
        # so generated [n] source markers stay visible.
        run_step([str(SCRIPT_DIR / "make_docx.py"), str(display_output), "-o", str(docx_output)])

    print("Finalized report:")
    print(f"- Source markdown: {markdown_path}")
    print(f"- Display markdown: {display_output}")
    if docx_output is not None:
        print(f"- Optional DOCX export: {docx_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
