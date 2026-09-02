#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""拆分树（Decomposition Tree）软门禁验证器 — 最小不可拆单元 MDU

设计目的（accuracy-uplift v12 · 建议 2）
─────────────────────────────────────────────────────────────────────
营收/利润预测必须拆到"最小不可拆单元（MDU, Minimum Decomposition Unit）"
—— 继续拆分得到的子单元，其量价驱动变量与父单元相同（即拆了也没新增信息）。
每个叶子节点必须回答四问：量、价、份额、成本。

规范
─────────────────────────────────────────────────────────────────────
文件路径：OutputReport/{report_stem}_decomposition_tree.json
{
  "report": "...",
  "company": "比亚迪",
  "fiscal_year": 2026,
  "total_revenue_forecast": 800000000000,
  "trees": [
    {
      "business": "新能源汽车",
      "revenue_share": 0.78,
      "children": [
        {
          "business": "海外销售",
          "revenue_share": 0.30,
          "children": [
            {
              "business": "欧洲市场",
              "revenue_share": 0.55,
              "is_leaf": true,
              "drivers": {
                "volume": {"value": "...", "source": "..."},
                "price":  {"value": "...", "source": "..."},
                "share":  {"value": "...", "source": "..."},
                "cost":   {"value": "...", "source": "..."}
              }
            },
            ...
          ]
        }
      ]
    },
    ...
  ]
}

软门禁规则
─────────────────────────────────────────────────────────────────────
1. 拆分深度 < 3 层 → WARN
2. 占营收 ≥ 10% 的业务未拆到叶子（无 is_leaf=true 且无 children）→ WARN
3. 叶子节点 drivers 四问任一缺失或无 source → WARN
4. 同一父节点下子节点 revenue_share 加总偏离 100% > 5% → WARN

业务类型 → 期望拆分终点对照
─────────────────────────────────────────────────────────────────────
| 制造业产品 | 单代际单 SKU × 单一终端客户类型 |
| 服务/订阅  | 单价段 × 单客群 × 单付费模式 |
| 金融       | 单产品线 × 单风险等级 × 单期限 |
| 零售       | 单业态 × 单地区 × 单 SKU 大类 |
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

MIN_DEPTH = 3                          # 至少拆 3 层
LARGE_BUSINESS_THRESHOLD = 0.10        # 占营收 ≥ 10% 必须拆到叶子
DRIVER_KEYS = ("volume", "price", "share", "cost")
SHARE_SUM_TOLERANCE = 0.05


def _detect_tree_path(report_path: Path) -> Path:
    return report_path.parent / f"{report_path.stem}_decomposition_tree.json"


def _tree_depth(node: dict) -> int:
    children = node.get("children") or []
    if not children:
        return 1
    return 1 + max(_tree_depth(c) for c in children if isinstance(c, dict))


def _walk(node: dict, path: List[str], warns: List[str], parent_share: float = 1.0) -> None:
    """递归校验节点"""
    name = node.get("business", "?")
    cur_path = path + [name]
    label = " → ".join(cur_path)
    share = float(node.get("revenue_share") or 0)
    abs_share = parent_share * share if share > 0 else parent_share

    children = node.get("children") or []
    is_leaf = bool(node.get("is_leaf")) or not children

    if is_leaf:
        drivers = node.get("drivers") or {}
        for k in DRIVER_KEYS:
            d = drivers.get(k)
            if not isinstance(d, dict) or not str(d.get("value", "")).strip():
                warns.append(
                    f"[拆分树·WARN] 叶子「{label}」缺少驱动变量「{k}」（量/价/份额/成本四问之一）"
                )
            elif not str(d.get("source", "")).strip():
                warns.append(
                    f"[拆分树·WARN] 叶子「{label}」驱动「{k}」缺 source（信源），无法追溯"
                )
    else:
        # 子节点 revenue_share 加总
        share_sum = sum(float(c.get("revenue_share") or 0) for c in children if isinstance(c, dict))
        if abs(share_sum - 1.0) > SHARE_SUM_TOLERANCE:
            warns.append(
                f"[拆分树·WARN] 节点「{label}」子节点 revenue_share 加总 {share_sum:.2f}，"
                f"偏离 1.00 超过 {SHARE_SUM_TOLERANCE}"
            )
        # 大业务（绝对营收占比 ≥10%）必须拆到底
        if abs_share >= LARGE_BUSINESS_THRESHOLD:
            # 已有 children 则继续递归即可（深度由顶层 _tree_depth 校验）
            pass
        for c in children:
            if isinstance(c, dict):
                _walk(c, cur_path, warns, abs_share)


def validate_decomposition_tree(report_path: Path) -> List[str]:
    warns: List[str] = []
    tree_path = _detect_tree_path(report_path)
    if not tree_path.exists():
        warns.append(
            f"[拆分树·WARN] 未产出拆分树文件 `{tree_path.name}`。"
            "建议 2（拆到不可拆）要求营收/利润预测拆到 MDU 最小不可拆单元，"
            "叶子节点须回答量/价/份额/成本四问。示例见 `decomposition_tree_validator.py` docstring。"
        )
        return warns

    try:
        data = json.loads(tree_path.read_text(encoding="utf-8"))
    except Exception as e:
        warns.append(f"[拆分树·WARN] 文件 `{tree_path.name}` 解析失败: {e}")
        return warns

    trees = data.get("trees", []) if isinstance(data, dict) else []
    if not trees:
        warns.append(f"[拆分树·WARN] `{tree_path.name}` trees 数组为空")
        return warns

    for tree in trees:
        if not isinstance(tree, dict):
            continue
        biz = tree.get("business", "?")
        depth = _tree_depth(tree)
        share = float(tree.get("revenue_share") or 0)
        if share >= LARGE_BUSINESS_THRESHOLD and depth < MIN_DEPTH:
            warns.append(
                f"[拆分树·WARN] 大业务「{biz}」（占营收 {share:.0%}）拆分深度仅 {depth} 层 < {MIN_DEPTH} 层。"
                "请继续拆到 MDU（单代际 SKU × 终端客户类型 / 单价段 × 单客群 × 单付费模式 等）。"
            )
        _walk(tree, [], warns)

    return warns


def main() -> None:
    parser = argparse.ArgumentParser(description="拆分树（MDU）软门禁验证器")
    parser.add_argument("report", help="报告 Markdown 路径")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    args = parser.parse_args()

    report_path = Path(args.report)
    warns = validate_decomposition_tree(report_path)
    if args.format == "json":
        print(json.dumps({"pass": len(warns) == 0, "warns": warns}, ensure_ascii=False, indent=2))
    else:
        if not warns:
            print(f"✅ 拆分树软门禁 PASS: {report_path.name}")
        else:
            print(f"⚠️ 拆分树软门禁 {len(warns)} 条 WARN:")
            for w in warns:
                print(f"  - {w}")
    sys.exit(0)


if __name__ == "__main__":
    main()
