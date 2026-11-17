#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_direction_packs.py — 按持方预编译规则包

把 risk-library.index.json 里的 43 条规则,按 direction 字段拆成 3 个文件:
  - risk-library.self.json   : 我方代理时加载(always + self + both)
  - risk-library.other.json  : 代理对方时加载(always + other + both)
  - risk-library.always.json : 仅普适规则(always),用于"无明确持方"场景

LLM 在 Step 0 识别持方后,只需读对应的一份,而不必再扫整个 index 自己过滤。
节省一点 token,更主要是降低误触发对方专属规则的概率(避免帮我方时去补对方
义务的违约责任)。

一次性脚本:打包 skill 时跑一次,运行期不再用。审查工作流不依赖它。
"""
import argparse
import json
import os
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description="按 direction 拆 risk-library.index.json")
    ap.add_argument("input", nargs="?", default="risk-library.index.json",
                    help="源索引,默认 ./risk-library.index.json")
    ap.add_argument("--out-dir", default=None,
                    help="输出目录,默认与 input 同目录")
    args = ap.parse_args()

    src = Path(args.input).resolve()
    if not src.exists():
        print(f"[build_direction_packs] ERROR: {src} not found", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir).resolve() if args.out_dir else src.parent

    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    rules = data.get("rules", [])

    buckets = {
        "self": [],   # always + self + both
        "other": [],  # always + other + both
        "always": [], # 仅 always
    }
    for r in rules:
        d = (r.get("direction") or "always").lower()
        if d == "always":
            buckets["self"].append(r)
            buckets["other"].append(r)
            buckets["always"].append(r)
        elif d == "self":
            buckets["self"].append(r)
        elif d == "other":
            buckets["other"].append(r)
        elif d == "both":
            buckets["self"].append(r)
            buckets["other"].append(r)
        else:
            # 未识别方向当 always 处理,但记日志提醒
            print(f"[build_direction_packs] WARN: rule {r.get('id')} has unknown direction "
                  f"'{r.get('direction')}', treated as always", file=sys.stderr)
            buckets["self"].append(r)
            buckets["other"].append(r)
            buckets["always"].append(r)

    summary = {}
    for key, rs in buckets.items():
        out_path = out_dir / f"risk-library.{key}.json"
        out_obj = {
            "version": data.get("version", ""),
            "source": "risk-library.index.json",
            "direction_pack": key,
            "description": (
                f"direction-filtered rule pack for direction='{key}'. "
                f"LLM 在 Step 0 识别持方后加载本文件,无需再读 risk-library.index.json。"
            ),
            "_fields": data.get("_fields", {}),
            "_pack_rules": {
                "self":   "always + self + both",
                "other":  "always + other + both",
                "always": "always only(无明确持方时回退)",
            }[key],
            "rules_count": len(rs),
            "rules": rs,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out_obj, f, ensure_ascii=False, indent=2)
        summary[key] = {"count": len(rs), "path": str(out_path)}

    print(json.dumps({"is_error": False, "packs": summary,
                      "total_source_rules": len(rules)},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
