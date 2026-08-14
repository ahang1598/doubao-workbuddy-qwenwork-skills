#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验第二阶段 doc.md 是否满足生成飞书 XML 的要求。"""
from __future__ import annotations

import argparse
from pathlib import Path

from generate_doc_markdown import load_doc_markdown
from validate_doc_payload import PayloadError, validate_payload


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="校验飞书文档中间产物 doc.md。")
    ap.add_argument("doc_md", help="结构化 doc.md")
    args = ap.parse_args(argv)

    path = Path(args.doc_md)
    if not path.exists():
        print(f"[错误] 找不到 doc.md: {path}")
        return 2

    try:
        doc = load_doc_markdown(path)
    except Exception as exc:  # pragma: no cover - CLI path
        print(f"[错误] 解析 doc.md 失败：{exc}")
        return 2

    try:
        warnings = validate_payload(doc)
    except PayloadError as exc:
        print(str(exc))
        return 1
    if warnings:
        for msg in warnings:
            print(f"[警告] {msg}")
    print(f"[信息] doc.md 校验通过：0 错误，{len(warnings)} 警告。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
