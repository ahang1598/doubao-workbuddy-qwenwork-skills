#!/usr/bin/env python3
"""
extract_cross_doc_fields.py — B 侧字段抽取入口（Step 1.5 之 1）。

复用「合同审查清单生成器」的 cross_doc_extract.py 核心逻辑，
但产出更适合 verify_cross_doc.py 消费的 fields.json 结构：

{
  "files": [
    {"name":"...", "category":"contract|quote|po|sow|...",
     "fields":{ "<field_name>": [{"value":"...","raw":"..."}, ...] }
    },
    ...
  ]
}

并可选输出 align-md（对齐表 Markdown）。

用法：
  python extract_cross_doc_fields.py <合同> [<关联文件>...] \\
      --align-md /tmp/align.md \\
      --fields-json /tmp/fields.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

# 动态加载 A 侧 cross_doc_extract 模块（复用其字段正则与文件解析逻辑）
A_SCRIPT = (
    Path(__file__).resolve().parent.parent.parent
    / "合同审查清单生成器"
    / "scripts"
    / "cross_doc_extract.py"
)


def load_a_module() -> Any:
    if not A_SCRIPT.exists():
        raise SystemExit(
            f"[ERROR] 未找到 A 侧脚本: {A_SCRIPT}\n"
            "请确认「合同审查清单生成器」与本 skill 在同级目录下。"
        )
    spec = importlib.util.spec_from_file_location("a_cross_doc_extract", A_SCRIPT)
    if spec is None or spec.loader is None:
        raise SystemExit(f"[ERROR] 无法加载 A 侧脚本: {A_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("files", nargs="+", help="合同 + 关联文件路径列表")
    p.add_argument("--align-md", default=None)
    p.add_argument("--fields-json", required=True, help="字段抽取结果 JSON 输出路径")
    args = p.parse_args()

    a = load_a_module()

    per_file: list[dict[str, Any]] = []
    for f in args.files:
        path = Path(f).expanduser().resolve()
        if not path.exists():
            print(f"[WARN] 文件不存在，跳过: {path}", file=sys.stderr)
            continue
        try:
            text = a.read_text_any(path)
        except Exception as e:
            print(f"[WARN] 解析 {path.name} 失败: {e}", file=sys.stderr)
            continue
        per_file.append(
            {
                "name": path.name,
                "category": a.infer_category(path),
                "fields": a.extract_fields(text),
            }
        )

    if not per_file:
        print("[ERROR] 没有任何可处理的文件", file=sys.stderr)
        return 2

    Path(args.fields_json).expanduser().resolve().write_text(
        json.dumps({"files": per_file}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if args.align_md:
        align = "## 跨文件字段对齐表\n\n" + a.build_alignment_table(per_file) + "\n"
        Path(args.align_md).expanduser().resolve().write_text(align, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "files_processed": len(per_file),
                "fields_json": args.fields_json,
                "align_md": args.align_md,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
