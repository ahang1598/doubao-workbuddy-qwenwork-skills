#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""追问链（Why-Chain）软门禁验证器 — 第一性原理深度追问机制

设计目的（accuracy-uplift v12 · 建议 1）
─────────────────────────────────────────────────────────────────────
报告中每个**核心结论**（带数字的预测/目标价/评级等）必须配套一份
追问链 JSON，强制把"为什么"追到客观可验证事实 / 已签合同 / 科学原理
三类终止条件之一，杜绝"市场普遍认为/卖方一致预期/公司指引/行业惯例"
等浅层停滞。

规范
─────────────────────────────────────────────────────────────────────
文件路径：OutputReport/{report_stem}_why_chain.json
文件结构（chains 数组 ≥ 3 条；每条 chain 深度 ≥ 5 层）：
{
  "report": "交易决策报告_xxxxxx_yy_yyyymmddhhmm.md",
  "generated_at": "2026-06-06T22:00:00",
  "chains": [
    {
      "claim": "比亚迪 2026 年净利润增长 25%",
      "section": "4.1.4 盈利预测",
      "chain": [
        {"depth": 1, "why": "...", "evidence_type": "推论", "source": "..."},
        ...
        {"depth": 5, "why": "...", "evidence_type": "客观事实|已签合同|科学原理",
         "source": "https://...", "stop": true}
      ]
    },
    ...
  ]
}

终止条件（depth 末层必须命中其一）
─────────────────────────────────────────────────────────────────────
A. 客观可验证事实（evidence_type ∈ {客观事实, 客观计算, 公开数据, 已公布数据}）
B. 已签合同/已发生交易（evidence_type ∈ {已签合同, 已签订单, 已建产能, 已发生交易, 已完成并购}）
C. 基本科学/会计/物理原理（evidence_type ∈ {科学原理, 会计原理, 数学公式, 物理定律}）

禁词清单（不允许作为终止位）
─────────────────────────────────────────────────────────────────────
"市场普遍认为", "卖方一致预期", "公司指引", "行业惯例",
"大家都这么说", "大家普遍", "众所周知", "习惯上",
"主流观点", "市场共识", "业内共识"

软门禁性质
─────────────────────────────────────────────────────────────────────
本验证器只产出 WARN，**不阻断交付**。结果由 report_quality_checker.py
聚合写入 `_gate_result.md` 末尾"软门禁 WARN 列表"段落。

用法
─────────────────────────────────────────────────────────────────────
# 作为 CLI 独立调用
python why_chain_validator.py OutputReport/交易决策报告_xxxxxx_yy_xxxxxxxx.md
# 作为模块被 report_quality_checker.py import
from why_chain_validator import validate_why_chain
warns = validate_why_chain(report_path)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Windows UTF-8
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── 规范常量 ──────────────────────────────────────────────────────
MIN_CHAINS = 3                # 一份报告至少 3 条核心追问链
MIN_CHAIN_DEPTH = 5           # 每条链至少 5 层
VALID_TERMINAL_TYPES = {
    # A. 客观事实
    "客观事实", "客观计算", "公开数据", "已公布数据", "历史数据", "审计数据",
    # B. 已签合同/已发生
    "已签合同", "已签订单", "已建产能", "已发生交易", "已完成并购",
    "已获牌照", "已颁布法规",
    # C. 科学/会计/物理原理
    "科学原理", "会计原理", "数学公式", "物理定律", "化学定律",
    "经济学公理", "会计恒等式",
}
BAN_TERMINAL_PHRASES = [
    "市场普遍认为", "卖方一致预期", "公司指引", "行业惯例",
    "大家都这么说", "大家普遍", "众所周知", "习惯上",
    "主流观点", "市场共识", "业内共识", "通常认为", "一般来说",
    "据传", "传言", "据说",
]


def _detect_why_chain_path(report_path: Path) -> Path:
    return report_path.parent / f"{report_path.stem}_why_chain.json"


def validate_why_chain(report_path: Path) -> List[str]:
    """返回 WARN 列表（空 = 通过软门禁）。"""
    warns: List[str] = []
    wc_path = _detect_why_chain_path(report_path)

    if not wc_path.exists():
        warns.append(
            f"[追问链·WARN] 未产出追问链文件 `{wc_path.name}`。"
            "建议 1（第一性原理）要求每个核心结论配套一份 ≥5 层的追问链，"
            "终止于客观事实/已签合同/科学原理三类之一。"
            "示例结构见 `scripts/why_chain_validator.py` 顶部 docstring。"
        )
        return warns

    try:
        data = json.loads(wc_path.read_text(encoding="utf-8"))
    except Exception as e:
        warns.append(f"[追问链·WARN] 文件 `{wc_path.name}` 解析失败: {e}")
        return warns

    chains = data.get("chains", []) if isinstance(data, dict) else []
    if not isinstance(chains, list) or len(chains) < MIN_CHAINS:
        warns.append(
            f"[追问链·WARN] 追问链条数 {len(chains)} < 最低要求 {MIN_CHAINS}。"
            "至少需覆盖：① 营收/利润核心预测；② 目标价/估值；③ 评级/操作判断。"
        )

    for i, chain in enumerate(chains, 1):
        if not isinstance(chain, dict):
            warns.append(f"[追问链·WARN] 第 {i} 条 chain 不是对象")
            continue
        claim = chain.get("claim", "?")[:50]
        steps = chain.get("chain", [])
        if not isinstance(steps, list):
            warns.append(f"[追问链·WARN] 第 {i} 条「{claim}」chain 字段非数组")
            continue
        depth = len(steps)
        if depth < MIN_CHAIN_DEPTH:
            warns.append(
                f"[追问链·WARN] 第 {i} 条「{claim}」追问深度仅 {depth} < {MIN_CHAIN_DEPTH}。"
                "请继续刨根问底直到落到客观事实/已签合同/科学原理。"
            )
        # 终止层检查
        if steps:
            last = steps[-1] if isinstance(steps[-1], dict) else {}
            et = str(last.get("evidence_type", "")).strip()
            why_text = str(last.get("why", ""))
            if et not in VALID_TERMINAL_TYPES:
                warns.append(
                    f"[追问链·WARN] 第 {i} 条「{claim}」末层 evidence_type='{et}'，"
                    f"不在允许集合（客观事实/已签合同/科学原理三大类）。"
                )
            for ban in BAN_TERMINAL_PHRASES:
                if ban in why_text:
                    warns.append(
                        f"[追问链·WARN] 第 {i} 条「{claim}」末层 why 含禁词「{ban}」，"
                        "应继续追问到客观依据。"
                    )
                    break
            # 末层缺少 source URL
            src = str(last.get("source", "")).strip()
            if et in VALID_TERMINAL_TYPES and et not in {"科学原理", "会计原理", "数学公式", "物理定律", "化学定律", "经济学公理", "会计恒等式"}:
                if not src or (not src.startswith("http") and "P." not in src and "年报" not in src and "公告" not in src):
                    warns.append(
                        f"[追问链·WARN] 第 {i} 条「{claim}」末层为客观事实/已签合同类，"
                        "但缺少可溯源 source（URL / 年报 P.x / 公告编号）。"
                    )

    return warns


def main() -> None:
    parser = argparse.ArgumentParser(description="追问链（Why-Chain）软门禁验证器")
    parser.add_argument("report", help="报告 Markdown 路径")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    report_path = Path(args.report)
    warns = validate_why_chain(report_path)
    if args.format == "json":
        print(json.dumps({"pass": len(warns) == 0, "warns": warns}, ensure_ascii=False, indent=2))
    else:
        if not warns:
            print(f"✅ 追问链软门禁 PASS: {report_path.name}")
        else:
            print(f"⚠️ 追问链软门禁 {len(warns)} 条 WARN:")
            for w in warns:
                print(f"  - {w}")
    sys.exit(0)  # 软门禁不阻断


if __name__ == "__main__":
    main()
