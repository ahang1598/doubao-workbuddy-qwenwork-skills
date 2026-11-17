#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
付款流向矛盾检测脚本 — verify_payment_flow.py

用于合同审查 Step 2 Layer 3 §3.4.7 的付款流向一致性检测。
LLM 提取结构化数据 → 本脚本执行确定性比对 → LLM 解读结果。

用法:
    python3 verify_payment_flow.py --json payment_flow.json
    python3 verify_payment_flow.py --json payment_flow.json --output results.json

输入 JSON 格式:
{
  "parties": {                              // 合同各方信息
    "party_a": "甲方/XX公司",
    "party_b": "乙方/YY公司"
  },
  "payment_items": [                        // 所有涉及付款/收款的条款
    {
      "label": "合作费用",                   // 付款事项名称
      "clause": "第4.1条",                   // 条款位置
      "payer": "甲方",                       // 付款方
      "payee": "乙方",                       // 收款方
      "amount": 100000,                      // 金额（可以为 null）
      "context": "甲方应在合同生效后..向乙方支付" // 原文摘录
    }
  ],
  "fee_items": [                            // 费用承担条款
    {
      "label": "运输费",
      "clause": "第3条",
      "bearer": "乙方",                     // 承担方
      "context": "运输费由乙方承担"
    }
  ],
  "obligation_items": [                     // 义务执行方条款
    {
      "label": "交付义务",
      "clause": "第5条",
      "executor": "乙方",
      "context": "乙方应在约定日期前完成交付"
    }
  ],
  "right_items": [                          // 权利/归属条款
    {
      "label": "知识产权归属",
      "clause": "第7条",
      "owner": "甲方",
      "context": "合作成果的知识产权归甲方所有"
    }
  ]
}

输出: JSON 格式的矛盾检测结果。
"""

import argparse
import json
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional


def normalize_party(name: str, parties: Dict) -> str:
    """
    标准化当事方名称。
    将"XX公司"等全称映射回"甲方"/"乙方"。
    """
    if not name:
        return name

    name = name.strip()
    party_a = parties.get("party_a", "")
    party_b = parties.get("party_b", "")

    # 直接匹配
    if name in ("甲方", "Party A", "party_a"):
        return "甲方"
    if name in ("乙方", "Party B", "party_b"):
        return "乙方"
    if name in ("丙方", "Party C", "party_c"):
        return "丙方"

    # 公司名匹配
    if party_a and (name in party_a or party_a in name):
        return "甲方"
    if party_b and (name in party_b or party_b in name):
        return "乙方"

    # 尝试分割"甲方/XX公司"格式
    for sep in ('/', '（', '(', '、'):
        if sep in party_a:
            parts = party_a.split(sep)
            for p in parts:
                p = p.strip().rstrip('）').rstrip(')')
                if name == p:
                    return "甲方"
        if sep in party_b:
            parts = party_b.split(sep)
            for p in parts:
                p = p.strip().rstrip('）').rstrip(')')
                if name == p:
                    return "乙方"

    return name  # 无法归一化时保持原样


def detect_payment_flow_contradictions(payment_items: List[Dict], parties: Dict) -> List[Dict]:
    """
    检测付款流向矛盾。
    同一付款事项在不同条款中的付款方→收款方方向是否一致。
    """
    results = []

    # 按付款事项分组
    groups = defaultdict(list)
    for item in payment_items:
        label = item.get("label", "").strip()
        if label:
            groups[label].append(item)

    for label, items in groups.items():
        if len(items) < 2:
            continue  # 只出现一次无法比对

        # 标准化所有付款方/收款方
        flows = []
        for item in items:
            payer = normalize_party(item.get("payer", ""), parties)
            payee = normalize_party(item.get("payee", ""), parties)
            flows.append({
                "clause": item.get("clause", "未知"),
                "payer": payer,
                "payee": payee,
                "direction": f"{payer}→{payee}",
                "context": item.get("context", ""),
            })

        # 检查方向是否一致
        directions = set(f["direction"] for f in flows)
        if len(directions) > 1:
            results.append({
                "check": "payment_flow_contradiction",
                "label": label,
                "status": "fail",
                "risk_level": "P0",
                "directions": list(directions),
                "details": flows,
                "message": (
                    f"付款事项「{label}」在不同条款中的付款方向不一致："
                    + "；".join(f"{f['clause']}:{f['direction']}" for f in flows)
                )
            })
        else:
            results.append({
                "check": "payment_flow_consistency",
                "label": label,
                "status": "pass",
                "direction": list(directions)[0],
                "clauses": [f["clause"] for f in flows],
                "message": f"付款事项「{label}」方向一致：{list(directions)[0]}"
            })

    return results


def detect_fee_bearer_contradictions(fee_items: List[Dict], parties: Dict) -> List[Dict]:
    """
    检测费用承担主体矛盾。
    同一费用在不同条款中的承担方是否一致。
    """
    results = []

    groups = defaultdict(list)
    for item in fee_items:
        label = item.get("label", "").strip()
        if label:
            groups[label].append(item)

    for label, items in groups.items():
        if len(items) < 2:
            continue

        bearers = []
        for item in items:
            bearer = normalize_party(item.get("bearer", ""), parties)
            bearers.append({
                "clause": item.get("clause", "未知"),
                "bearer": bearer,
                "context": item.get("context", ""),
            })

        unique_bearers = set(b["bearer"] for b in bearers)
        if len(unique_bearers) > 1:
            results.append({
                "check": "fee_bearer_contradiction",
                "label": label,
                "status": "fail",
                "risk_level": "P0",
                "bearers": list(unique_bearers),
                "details": bearers,
                "message": (
                    f"费用「{label}」承担主体在不同条款中矛盾："
                    + "；".join(f"{b['clause']}:{b['bearer']}" for b in bearers)
                )
            })
        else:
            results.append({
                "check": "fee_bearer_consistency",
                "label": label,
                "status": "pass",
                "bearer": list(unique_bearers)[0],
                "clauses": [b["clause"] for b in bearers],
                "message": f"费用「{label}」承担方一致：{list(unique_bearers)[0]}"
            })

    return results


def detect_obligation_contradictions(obligation_items: List[Dict], parties: Dict) -> List[Dict]:
    """检测义务执行方矛盾。"""
    results = []

    groups = defaultdict(list)
    for item in obligation_items:
        label = item.get("label", "").strip()
        if label:
            groups[label].append(item)

    for label, items in groups.items():
        if len(items) < 2:
            continue

        executors = []
        for item in items:
            executor = normalize_party(item.get("executor", ""), parties)
            executors.append({
                "clause": item.get("clause", "未知"),
                "executor": executor,
                "context": item.get("context", ""),
            })

        unique_executors = set(e["executor"] for e in executors)
        if len(unique_executors) > 1:
            results.append({
                "check": "obligation_executor_contradiction",
                "label": label,
                "status": "fail",
                "risk_level": "P0",
                "executors": list(unique_executors),
                "details": executors,
                "message": (
                    f"义务「{label}」执行方在不同条款中矛盾："
                    + "；".join(f"{e['clause']}:{e['executor']}" for e in executors)
                )
            })

    return results


def detect_right_contradictions(right_items: List[Dict], parties: Dict) -> List[Dict]:
    """检测权利归属矛盾。"""
    results = []

    groups = defaultdict(list)
    for item in right_items:
        label = item.get("label", "").strip()
        if label:
            groups[label].append(item)

    for label, items in groups.items():
        if len(items) < 2:
            continue

        owners = []
        for item in items:
            owner = normalize_party(item.get("owner", ""), parties)
            owners.append({
                "clause": item.get("clause", "未知"),
                "owner": owner,
                "context": item.get("context", ""),
            })

        unique_owners = set(o["owner"] for o in owners)
        if len(unique_owners) > 1:
            results.append({
                "check": "right_ownership_contradiction",
                "label": label,
                "status": "fail",
                "risk_level": "P0",
                "owners": list(unique_owners),
                "details": owners,
                "message": (
                    f"权利「{label}」归属在不同条款中矛盾："
                    + "；".join(f"{o['clause']}:{o['owner']}" for o in owners)
                )
            })

    return results


def cross_validate_payment_vs_obligation(payment_items: List[Dict],
                                          obligation_items: List[Dict],
                                          parties: Dict) -> List[Dict]:
    """
    交叉校验：付款方向 vs 义务方向。
    例如：付款条款说"甲方付给乙方"，但义务条款说"甲方负责交付"（甲方既付钱又干活→可能有误）。
    仅做提示级别的检测。
    """
    results = []

    # 构建付款方集合
    payer_set = set()
    for item in payment_items:
        payer = normalize_party(item.get("payer", ""), parties)
        payer_set.add(payer)

    # 检查义务方是否同时也是付款方（同一事项）
    for item in obligation_items:
        executor = normalize_party(item.get("executor", ""), parties)
        label = item.get("label", "")

        # 查找同名付款事项
        for pi in payment_items:
            pi_label = pi.get("label", "")
            pi_payer = normalize_party(pi.get("payer", ""), parties)

            # 如果同一事项的付款方和义务执行方是同一人
            if pi_label == label and pi_payer == executor and label:
                results.append({
                    "check": "payment_obligation_overlap",
                    "label": label,
                    "status": "warn",
                    "risk_level": "P2",
                    "party": executor,
                    "payment_clause": pi.get("clause", "未知"),
                    "obligation_clause": item.get("clause", "未知"),
                    "message": (
                        f"「{label}」中 {executor} 既是付款方又是义务执行方，"
                        f"请确认合同逻辑是否合理"
                    )
                })

    return results


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run_all_checks(data: Dict) -> Dict:
    """执行所有流向矛盾检测。"""
    parties = data.get("parties", {})
    payment_items = data.get("payment_items", [])
    fee_items = data.get("fee_items", [])
    obligation_items = data.get("obligation_items", [])
    right_items = data.get("right_items", [])

    all_checks = []

    # 付款流向矛盾
    all_checks.extend(detect_payment_flow_contradictions(payment_items, parties))

    # 费用承担主体矛盾
    all_checks.extend(detect_fee_bearer_contradictions(fee_items, parties))

    # 义务执行方矛盾
    all_checks.extend(detect_obligation_contradictions(obligation_items, parties))

    # 权利归属矛盾
    all_checks.extend(detect_right_contradictions(right_items, parties))

    # 交叉校验
    all_checks.extend(cross_validate_payment_vs_obligation(
        payment_items, obligation_items, parties))

    # 汇总
    fail_count = sum(1 for c in all_checks if c.get("status") == "fail")
    warn_count = sum(1 for c in all_checks if c.get("status") == "warn")
    pass_count = sum(1 for c in all_checks if c.get("status") == "pass")

    contradiction_count = sum(1 for c in all_checks if "contradiction" in c.get("check", ""))

    results = {
        "summary": {
            "total_checks": len(all_checks),
            "contradictions_found": fail_count,
            "warnings": warn_count,
            "consistent": pass_count,
            "payment_items_count": len(payment_items),
            "fee_items_count": len(fee_items),
            "obligation_items_count": len(obligation_items),
            "right_items_count": len(right_items),
        },
        "checks": all_checks,
    }

    if fail_count > 0:
        results["summary"]["overall"] = "FAIL"
        results["summary"]["message"] = f"发现 {fail_count} 处流向/归属矛盾"
    elif warn_count > 0:
        results["summary"]["overall"] = "WARN"
        results["summary"]["message"] = f"{warn_count} 处流向警告需确认"
    else:
        results["summary"]["overall"] = "PASS"
        results["summary"]["message"] = "所有流向/归属检查一致"

    return results


def main():
    parser = argparse.ArgumentParser(description="合同付款流向矛盾检测脚本")
    parser.add_argument("--json", "-j", required=True, help="输入 JSON 文件路径")
    parser.add_argument("--output", "-o", help="输出结果 JSON 文件路径")
    args = parser.parse_args()

    with open(args.json, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = run_all_checks(data)
    output_json = json.dumps(results, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"[OK] 验证结果已写入 {args.output}")
    else:
        print(output_json)

    sys.exit(1 if results["summary"]["overall"] == "FAIL" else 0)


if __name__ == "__main__":
    main()
