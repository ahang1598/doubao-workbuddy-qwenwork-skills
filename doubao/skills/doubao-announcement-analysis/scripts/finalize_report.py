#!/usr/bin/env python3
"""交付流程的唯一入口脚本（把源稿变成飞书文档创建源）。

用法（唯一路径，不要拆开跑内部 helper）：
  python3 scripts/finalize_report.py <源markdown文件> [facts.json] \
      --display-output <display markdown 输出路径> [--docx-output <可选docx路径>]

编排逻辑（任何一步失败都会以非零退出码中止，不会生成新的 display markdown）：
  1. normalize_report.py：把源稿里的草稿直角引号「」『』，以及英文直引号包裹的中文短语，原地转换成中文弯引号。
  2. check_facts.py（提供了 facts.json 时才跑）：门禁 1，校验 facts.json 结构。
  3. lint_report.py：门禁 2，校验源稿语气/边界/来源问题。**这是硬门禁**——有
     ERROR 级问题时退出码非零，finalize 直接中止，不会生成 display markdown；
     必须回到源稿改完问题再重新跑这个脚本，不能跳过或绕过。WARNING 不阻断，但
     不能直接无视：要么确认是误报，要么按建议改写后重跑。
  4. make_display_markdown.py：结合 facts.json 把 `{fact:claim_id}` 转换成
     `[n]` 标记，生成 display markdown。
  5. make_docx.py（提供了 --docx-output 才跑）：可选 Word 导出，非默认交付物，
     只有用户明确要求时才应该传这个参数。

`scripts/normalize_report.py`、`scripts/check_facts.py`、`scripts/lint_report.py`、
`scripts/make_display_markdown.py` 都是这个脚本的内部 helper，不要拆开单独运行
来完成交付——直接跑这一条命令。
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
        description="交付唯一入口：规范化 + 门禁1(facts) + 门禁2(lint) + 生成 display markdown。"
    )
    parser.add_argument("markdown", help="源 Markdown 文件（含 {fact:claim_id} 绑定）")
    parser.add_argument("facts", nargs="?", default=None, help="可选 facts.json，用于门禁校验")
    parser.add_argument("--docx-output", default=None, help="可选 DOCX 导出路径；不传则不生成，非默认交付物")
    parser.add_argument("--display-output", default=None, help="display markdown 输出路径（默认 <源文件名>-display.md）")
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
        # 可选导出复用飞书文档同一份 display 副本，保证 [n] 来源标记一致。
        run_step([str(SCRIPT_DIR / "make_docx.py"), str(display_output), "-o", str(docx_output)])

    print("Finalized report:")
    print(f"- Source markdown: {markdown_path}")
    print(f"- Display markdown: {display_output}")
    if docx_output is not None:
        print(f"- Optional DOCX export: {docx_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
