#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""飞书文档 payload 的数据复算门（写入前预检）。

把 payload 里能从原始分量复算的展示数字真的算一遍，与登记值对账；并校验
numeric_facts 事实表结构、来源分级、以及「关键展示数值是否登记 / 可溯源」。
10 股逐股行情、近7日复算、量价分组和代表股理由已在第一阶段 facts.json 中校验，
文档生成阶段通过 hydrate_payload_from_facts.py 自动映射，不在本脚本重复做内容判断。

用法：
    python3 scripts/check_market_facts.py work/<板块>_payload.json

退出码：
    0：无阻断性错误（可进入飞书文档写入）
    1：存在阻断性错误（请逐条修正 payload 后再写入飞书文档）

说明：
    * [复算/信息] 行是写作阶段**唯一允许的衍生数字来源**——正文/飞书文档里的回撤、
      单日涨跌、反弹、比值等派生数字应以这里算出的为准，不要另凭印象给数。
    * 本预检与 validate_doc_payload.py 共用 market_checks.py 的展示数字复算与事实表校验。
      因此这里能过，文档 payload 校验通常也能过；这里先跑可在写入飞书前暴露编造/算错的展示数字。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import market_checks  # noqa: E402


def load_json(path: Path):
    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
    if stripped.startswith("{"):
        return json.loads(stripped)
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if m:
        return json.loads(m.group(1))
    raise ValueError(f"{path} 不含 JSON 对象")


def main(argv=None):
    parser = argparse.ArgumentParser(description="飞书文档 payload 数据复算门（写入前预检）。")
    parser.add_argument("payload", help="payload.json 路径")
    args = parser.parse_args(argv)

    path = Path(args.payload)
    try:
        p = load_json(path)
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 无法读取 JSON: {exc}")
        return 1

    infos, warnings, errors = market_checks.run_all(p)

    for msg in infos:
        print(f"[复算/信息] {msg}")
    for msg in warnings:
        print(f"[警告] {msg}")
    for msg in errors:
        print(f"[错误] {msg}")
    print(f"汇总: {len(errors)} 错误, {len(warnings)} 警告, {len(infos)} 条复算/信息")

    if errors:
        print("\n复算门未通过：上述「数字对不上 / 量纲越界 / 登记与展示打架」需先修正，再写入飞书文档。")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
