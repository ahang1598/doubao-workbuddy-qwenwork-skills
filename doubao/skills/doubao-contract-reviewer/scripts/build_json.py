#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_json.py  — 目的
----
从 TOML 文件生成下游 JSON 文件(modifications.json 及 4 个 verify_*.py 的输入 JSON),
彻底消除中文引号 "" '' 、全角括号 ()、反斜杠、换行符等字符在 LLM 写 JSON / Python
时被误转义导致下游解析失败的问题。

为什么选 TOML
-------------
合同原文普遍含中文引号 "" ''。
- JSON 的字符串用 " 分隔 → 遇到中文 "" 必须转义 → LLM 经常漏转
- Python 字符串也常用 " 分隔 → 同样问题
- TOML 支持单引号 '...' 和三重单引号 '''...''' 的"字面串",不解析任何转义
  中文引号、全角括号、反斜杠都可以原样写,零转义、零冲突

这是"字符集冲突"的根治方案,不是"靠 LLM 更小心"。

Python 3.11+ 内置 tomllib,零依赖;3.9/3.10 需 pip install tomli 作为回退。

用法 — 单文件
-------------
save_mods.toml:
    author = "合同审查助手"
    [[modifications]]
    type = "track_change"
    search_text = '''甲方应在合同签订后十个工作日内向乙方支付合同总额的"80%"作为预付款'''
    old_text = '80%'
    new_text = '30%'
    comment = '''【修改意见】将预付款比例从80%降至30%
【修改原因】预付款比例过高,甲方资金风险大'''
    risk_level = "P0"

执行:
    python3 build_json.py --from-toml save_mods.toml --out modifications.json

用法 — 一次生成多个(最推荐,减少往返)
--------------------------------------
save_all.toml 顶层键即为输出文件名(表头):
    [modifications]
    author = "合同审查助手"
    ... (完整 modifications.json 的内容)

    [amounts]
    total_amount = 1000000
    currency = "CNY"
    ... (完整 amounts.json 的内容)

    [dates]
    review_date = "2026-04-29"
    ...

    [cross_refs]
    ...

    [payment_flow]
    ...

执行:
    python3 build_json.py --from-toml save_all.toml --multi
生成: modifications.json / amounts.json / dates.json / cross_refs.json / payment_flow.json

说明:--multi 模式下,顶层每个表(table)会写入 <表名>.json。

退出码
------
    0   成功
    1   输入错误(文件不存在/TOML 解析失败)
    2   JSON 序列化失败
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def load_toml(toml_path: str) -> dict:
    toml_path = os.path.abspath(toml_path)
    if not os.path.isfile(toml_path):
        print(f"[ERROR] TOML 文件不存在: {toml_path}", file=sys.stderr)
        sys.exit(1)
    try:
        import tomllib  # Python 3.11+ 内置
    except ImportError:
        try:
            import tomli as tomllib  # Python 3.9/3.10 回退,API 与 tomllib 一致
        except ImportError:
            print(
                "[ERROR] 当前 Python 无 tomllib(需 3.11+),且未安装回退库 tomli。"
                "请升级到 Python 3.11+,或执行 pip install tomli。",
                file=sys.stderr,
            )
            sys.exit(1)
    try:
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
    except Exception as exc:
        print(f"[ERROR] TOML 解析失败: {exc}", file=sys.stderr)
        print(
            "       提示:字符串如含中文引号或反斜杠,请改用单引号或三重单引号字面串包裹",
            file=sys.stderr,
        )
        sys.exit(1)
    return data


def write_json(obj, out_path: str) -> None:
    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    except TypeError as exc:
        print(f"[ERROR] JSON 序列化失败: {exc}", file=sys.stderr)
        sys.exit(2)


def main():
    parser = argparse.ArgumentParser(
        description="从 TOML 生成 UTF-8 无转义 JSON"
    )
    parser.add_argument(
        "--from-toml",
        "-t",
        required=True,
        help="TOML 输入文件路径",
    )
    parser.add_argument("--out", "-o", help="单文件模式下的输出 JSON 路径")
    parser.add_argument(
        "--multi",
        action="store_true",
        help="多文件模式:TOML 顶层每个 [table] 生成一个 <table>.json",
    )
    parser.add_argument(
        "--out-dir",
        default=".",
        help="--multi 模式下输出目录(默认当前目录)",
    )
    args = parser.parse_args()

    data = load_toml(args.from_toml)

    if args.multi:
        if not isinstance(data, dict) or not data:
            print("[ERROR] --multi 模式下 TOML 顶层必须包含至少一个 [table]", file=sys.stderr)
            sys.exit(1)
        written = []
        for name, obj in data.items():
            if not isinstance(obj, dict):
                # 忽略非表顶层键
                continue
            out_path = os.path.join(args.out_dir, f"{name}.json")
            write_json(obj, out_path)
            written.append(out_path)
            size = len(json.dumps(obj, ensure_ascii=False))
            print(f"[OK] {out_path}  ({size} chars)")
        if not written:
            print("[ERROR] TOML 顶层未找到任何 [table]", file=sys.stderr)
            sys.exit(1)
    else:
        if not args.out:
            print("[ERROR] 单文件模式必须提供 --out", file=sys.stderr)
            sys.exit(1)
        write_json(data, args.out)
        print(f"[OK] {args.out}")


if __name__ == "__main__":
    main()
