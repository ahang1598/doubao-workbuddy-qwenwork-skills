#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数值计算验证脚本 — verify_amounts.py

用于合同审查 Step 2 Layer 3 §3.4.3 的金额一致性验证。
LLM 提取结构化数据 → 本脚本执行确定性计算 → LLM 解读结果。

用法:
    python3 verify_amounts.py --json amounts.json

输入 JSON 格式:
{
  "total_amount": 1000000,          // 可以为 null（总额留空/未知）
  "currency": "CNY",
  "installments": [
    {
      "label": "首期款",
      "clause": "第4.1条",
      "amount": 300000,             // 可以为 null
      "percentage": 30              // 可以为 null
    }
  ],
  "deposit": {
    "amount": 200000,
    "type": "定金",
    "clause": "第5条"
  },
  "penalty_rates": [
    {
      "party": "甲方",
      "daily_rate": 0.0005,
      "clause": "第10.1条"
    }
  ],
  "amounts_uppercase": [
    {
      "clause": "第3条",
      "numeric": 1000000,
      "uppercase_text": "壹佰万元整"
    }
  ]
}

输出: JSON 格式的验证结果，包含每项检查的 pass/fail 和详细信息。
"""

import argparse
import json
import math
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 大写金额解析
# ---------------------------------------------------------------------------

_CN_DIGITS = {
    '零': 0, '壹': 1, '贰': 2, '叁': 3, '肆': 4,
    '伍': 5, '陆': 6, '柒': 7, '捌': 8, '玖': 9,
    '〇': 0, '一': 1, '二': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
}

_CN_UNITS = {
    '拾': 10, '佰': 100, '仟': 1000, '萬': 10000,
    '亿': 100000000, '十': 10, '百': 100, '千': 1000,
    '万': 10000,
}


def parse_cn_amount(text: str) -> Optional[float]:
    """
    解析中文大写金额。
    支持: "壹佰万元整", "叁拾伍万陆仟元", "壹仟零伍拾元贰角叁分" 等。
    返回 None 表示无法解析。
    """
    if not text:
        return None

    # 去除"人民币"、"元整"、"元"、"整"等后缀
    text = text.replace('人民币', '').replace('元整', '').replace('元', '')
    text = text.replace('整', '').replace('正', '').strip()

    # 处理角/分
    jiao = 0.0
    fen = 0.0
    if '角' in text:
        parts = text.split('角')
        jiao_part = parts[0][-1] if parts[0] else '0'
        if jiao_part in _CN_DIGITS:
            jiao = _CN_DIGITS[jiao_part] * 0.1
            text = parts[0][:-1] + (''.join(parts[1:]) if len(parts) > 1 else '')
        if '分' in text:
            fen_parts = text.split('分')
            fen_digit = fen_parts[0][-1] if fen_parts[0] else '0'
            if fen_digit in _CN_DIGITS:
                fen = _CN_DIGITS[fen_digit] * 0.01
                text = fen_parts[0][:-1]

    if not text.strip():
        return jiao + fen

    # 解析整数部分
    result = 0
    current = 0
    yi_part = 0  # 亿级别

    for char in text:
        if char in _CN_DIGITS:
            current = _CN_DIGITS[char]
        elif char in _CN_UNITS:
            unit = _CN_UNITS[char]
            if unit == 100000000:  # 亿
                yi_part = (result + current) * unit
                result = 0
                current = 0
            elif unit == 10000:  # 万
                result = (result + current) * unit
                current = 0
            else:
                result += current * unit
                current = 0

    result += current + yi_part

    return float(result) + jiao + fen


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _safe_number(val) -> Optional[float]:
    """安全地将值转换为 float，None/非数值返回 None。"""
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 验证逻辑
# ---------------------------------------------------------------------------

def verify_installment_sum(total_amount: Optional[float], installments: List[Dict]) -> Dict:
    """验证分期金额之和是否等于总金额。"""
    if not installments:
        return {"check": "installment_amount_sum", "status": "skip", "message": "无分期付款数据"}

    amounts = [_safe_number(inst.get("amount")) for inst in installments]
    valid_amounts = [a for a in amounts if a is not None]

    if not valid_amounts:
        return {"check": "installment_amount_sum", "status": "skip", "message": "分期付款无金额数据"}

    actual_sum = sum(valid_amounts)

    # 总额未知时，仅报告合计金额，不做 pass/fail 判定
    if total_amount is None or total_amount <= 0:
        return {
            "check": "installment_amount_sum",
            "status": "info",
            "total_amount": None,
            "installment_amounts": valid_amounts,
            "actual_sum": actual_sum,
            "message": f"总金额未知，分期金额合计 {actual_sum}（无法校验是否等于总额）"
        }

    diff = abs(actual_sum - total_amount)

    result = {
        "check": "installment_amount_sum",
        "total_amount": total_amount,
        "installment_amounts": valid_amounts,
        "actual_sum": actual_sum,
        "difference": diff,
    }

    if diff < 0.01:  # 允许1分钱的浮点误差
        result["status"] = "pass"
        result["message"] = f"分期金额合计 {actual_sum} = 总金额 {total_amount}"
    else:
        result["status"] = "fail"
        result["risk_level"] = "P0"
        result["message"] = (
            f"分期金额合计 {actual_sum} ≠ 总金额 {total_amount}，"
            f"差额 {diff}"
        )
        result["clauses"] = [inst.get("clause", "未知") for inst in installments]

    return result


def verify_percentage_sum(installments: List[Dict]) -> Dict:
    """验证分期百分比之和是否等于100%。"""
    percentages = [_safe_number(inst.get("percentage")) for inst in installments]
    valid_pcts = [p for p in percentages if p is not None]

    if not valid_pcts:
        return {"check": "installment_percentage_sum", "status": "skip", "message": "无百分比数据"}

    actual_sum = sum(valid_pcts)
    diff = abs(actual_sum - 100)

    result = {
        "check": "installment_percentage_sum",
        "percentages": valid_pcts,
        "actual_sum": actual_sum,
        "difference": diff,
    }

    if diff < 0.01:
        result["status"] = "pass"
        result["message"] = f"百分比合计 {actual_sum}% = 100%"
    else:
        result["status"] = "fail"
        result["risk_level"] = "P0"
        result["message"] = (
            f"百分比合计 {actual_sum}% ≠ 100%，差额 {diff}%"
        )
        result["clauses"] = [inst.get("clause", "未知") for inst in installments]

    return result


def verify_amount_percentage_consistency(total_amount: Optional[float], installments: List[Dict]) -> Dict:
    """
    验证每期金额是否与总价×百分比一致。

    当总额已知时：直接比较 amount vs total_amount * percentage / 100。
    当总额未知时（新增）：从各期的 amount/percentage 反推隐含总额，
    检查各期反推结果是否自洽。
    """
    if not installments:
        return {"check": "amount_percentage_consistency", "status": "skip", "message": "无分期数据"}

    # 收集同时有金额和百分比的分期
    pairs = []
    for inst in installments:
        amount = _safe_number(inst.get("amount"))
        pct = _safe_number(inst.get("percentage"))
        if amount is not None and pct is not None and pct > 0:
            pairs.append({
                "label": inst.get("label", "未知"),
                "clause": inst.get("clause", "未知"),
                "amount": amount,
                "percentage": pct,
                "implied_total": round(amount / pct * 100, 2),
            })

    if len(pairs) < 1:
        return {"check": "amount_percentage_consistency", "status": "skip", "message": "同时有金额和百分比的分期不足"}

    # --- 情况1：总额已知 ---
    if total_amount is not None and total_amount > 0:
        mismatches = []
        for p in pairs:
            expected = total_amount * p["percentage"] / 100
            diff = abs(p["amount"] - expected)
            if diff > 0.01:
                mismatches.append({
                    "label": p["label"],
                    "clause": p["clause"],
                    "stated_amount": p["amount"],
                    "expected_amount": round(expected, 2),
                    "stated_percentage": p["percentage"],
                    "difference": round(diff, 2),
                })

        result = {"check": "amount_percentage_consistency"}
        if mismatches:
            result["status"] = "fail"
            result["risk_level"] = "P0"
            result["mismatches"] = mismatches
            result["message"] = f"{len(mismatches)} 期金额与百分比不一致（基于已知总额 {total_amount}）"
        else:
            result["status"] = "pass"
            result["message"] = "所有分期金额与百分比一致"
        return result

    # --- 情况2：总额未知 → 反推自洽性检验（核心新增） ---
    implied_totals = [p["implied_total"] for p in pairs]

    # 检查所有反推总额是否一致
    min_total = min(implied_totals)
    max_total = max(implied_totals)
    spread = max_total - min_total

    result = {
        "check": "amount_percentage_consistency",
        "total_amount_unknown": True,
        "implied_totals": [
            {
                "label": p["label"],
                "clause": p["clause"],
                "amount": p["amount"],
                "percentage": p["percentage"],
                "implied_total": p["implied_total"],
                "formula": f"{p['amount']} / {p['percentage']}% = {p['implied_total']}"
            }
            for p in pairs
        ],
    }

    if spread < 0.01:
        result["status"] = "pass"
        result["message"] = (
            f"总额未知，但各期反推的隐含总额一致 = {implied_totals[0]}"
        )
        result["consistent_implied_total"] = implied_totals[0]
    else:
        result["status"] = "fail"
        result["risk_level"] = "P0"
        detail_parts = [f"{p['label']}({p['clause']})→{p['implied_total']}" for p in pairs]
        detail_str = '、'.join(detail_parts)
        result["message"] = (
            f"总额未知，各期反推的隐含总额不一致：{detail_str}。"
            f"差额 {round(spread, 2)}"
        )
        result["clauses"] = [p["clause"] for p in pairs]

    return result


def verify_deposit(total_amount: Optional[float], deposit: Dict) -> Dict:
    """验证定金/订金比例。"""
    if not deposit:
        return {"check": "deposit", "status": "skip", "message": "无定金数据"}

    amount = _safe_number(deposit.get("amount"))
    if amount is None:
        return {"check": "deposit", "status": "skip", "message": "定金金额为空"}

    deposit_type = deposit.get("type", "定金")
    clause = deposit.get("clause", "未知")

    result = {
        "check": "deposit",
        "deposit_type": deposit_type,
        "amount": amount,
        "total_amount": total_amount,
        "clause": clause,
    }

    if total_amount is not None and total_amount > 0:
        ratio = amount / total_amount * 100
        result["ratio"] = round(ratio, 2)

        if deposit_type == "定金" and ratio > 20:
            result["status"] = "fail"
            result["risk_level"] = "P0"
            result["message"] = (
                f"定金 {amount} 占总额 {ratio:.1f}%，超过法定上限 20%。"
                f"超出部分（{round(amount - total_amount * 0.2, 2)}）不具有定金效力"
            )
        elif deposit_type == "定金" and ratio > 15:
            result["status"] = "warn"
            result["risk_level"] = "P2"
            result["message"] = f"定金比例 {ratio:.1f}%，接近法定上限 20%"
        else:
            result["status"] = "pass"
            result["message"] = f"定金比例 {ratio:.1f}%，符合法定要求"
    else:
        result["status"] = "info"
        result["message"] = f"总金额未知，无法计算定金比例（定金金额：{amount}）"

    return result


def verify_penalty_rates(penalty_rates: List[Dict]) -> Dict:
    """验证违约金日利率折年化是否超过24%。"""
    if not penalty_rates:
        return {"check": "penalty_rates", "status": "skip", "message": "无违约金利率数据"}

    issues = []
    for rate_info in penalty_rates:
        daily_rate = _safe_number(rate_info.get("daily_rate"))
        if daily_rate is None:
            continue

        party = rate_info.get("party", "未知")
        clause = rate_info.get("clause", "未知")
        annual_rate = daily_rate * 365 * 100  # 百分比

        entry = {
            "party": party,
            "clause": clause,
            "daily_rate": daily_rate,
            "annual_rate_pct": round(annual_rate, 2),
        }

        if annual_rate > 24:
            entry["status"] = "fail"
            entry["message"] = f"{party}违约金年化 {annual_rate:.2f}%，超过司法保护上限 24%"
        elif annual_rate > 15.4:  # LPR 4倍（按3.85%计算）
            entry["status"] = "warn"
            entry["message"] = f"{party}违约金年化 {annual_rate:.2f}%，超过 LPR 四倍"
        else:
            entry["status"] = "pass"
            entry["message"] = f"{party}违约金年化 {annual_rate:.2f}%，合理范围"

        issues.append(entry)

    if not issues:
        return {"check": "penalty_rates", "status": "skip", "message": "无有效违约金利率数据"}

    result = {
        "check": "penalty_rates",
        "details": issues,
    }

    has_fail = any(i["status"] == "fail" for i in issues)
    has_warn = any(i["status"] == "warn" for i in issues)

    if has_fail:
        result["status"] = "fail"
        result["risk_level"] = "P0"
        result["message"] = "存在违约金利率超标"
    elif has_warn:
        result["status"] = "warn"
        result["risk_level"] = "P1"
        result["message"] = "存在违约金利率偏高"
    else:
        result["status"] = "pass"
        result["message"] = "所有违约金利率在合理范围"

    return result


def verify_uppercase_amounts(amounts_uppercase: List[Dict]) -> Dict:
    """验证大写金额与数字金额是否一致。"""
    if not amounts_uppercase:
        return {"check": "uppercase_amounts", "status": "skip", "message": "无大小写金额数据"}

    issues = []
    for entry in amounts_uppercase:
        numeric = _safe_number(entry.get("numeric"))
        text = entry.get("uppercase_text", "")
        clause = entry.get("clause", "未知")

        if numeric is None:
            issues.append({
                "clause": clause,
                "status": "skip",
                "message": f"数字金额为空，跳过"
            })
            continue

        parsed = parse_cn_amount(text)

        item = {
            "clause": clause,
            "numeric_value": numeric,
            "uppercase_text": text,
            "parsed_value": parsed,
        }

        if parsed is None:
            item["status"] = "warn"
            item["message"] = f"无法解析大写金额: {text}"
        elif abs(parsed - numeric) < 0.01:
            item["status"] = "pass"
            item["message"] = f"大小写一致: {numeric} = {text}"
        else:
            item["status"] = "fail"
            item["message"] = f"大小写不一致: 数字 {numeric} ≠ 大写 {text}（解析为 {parsed}）"

        issues.append(item)

    result = {
        "check": "uppercase_amounts",
        "details": issues,
    }

    has_fail = any(i["status"] == "fail" for i in issues)
    if has_fail:
        result["status"] = "fail"
        result["risk_level"] = "P0"
        result["message"] = "存在大小写金额不一致"
    else:
        result["status"] = "pass"
        result["message"] = "所有大小写金额一致"

    return result


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run_all_checks(data: Dict) -> Dict:
    """执行所有数值验证检查。"""
    total_amount = _safe_number(data.get("total_amount"))
    installments = data.get("installments", [])
    deposit = data.get("deposit")
    penalty_rates = data.get("penalty_rates", [])
    amounts_uppercase = data.get("amounts_uppercase", [])

    results = {
        "summary": {
            "total_amount": total_amount,
            "total_amount_known": total_amount is not None and total_amount > 0,
            "currency": data.get("currency", "CNY"),
            "installment_count": len(installments),
        },
        "checks": [],
    }

    # 执行各项检查
    results["checks"].append(verify_installment_sum(total_amount, installments))
    results["checks"].append(verify_percentage_sum(installments))
    results["checks"].append(verify_amount_percentage_consistency(total_amount, installments))
    results["checks"].append(verify_deposit(total_amount, deposit))
    results["checks"].append(verify_penalty_rates(penalty_rates))
    results["checks"].append(verify_uppercase_amounts(amounts_uppercase))

    # 汇总
    all_checks = results["checks"]
    fail_count = sum(1 for c in all_checks if c["status"] == "fail")
    warn_count = sum(1 for c in all_checks if c["status"] == "warn")
    pass_count = sum(1 for c in all_checks if c["status"] == "pass")
    skip_count = sum(1 for c in all_checks if c["status"] == "skip")
    info_count = sum(1 for c in all_checks if c["status"] == "info")

    results["summary"]["fail"] = fail_count
    results["summary"]["warn"] = warn_count
    results["summary"]["pass"] = pass_count
    results["summary"]["skip"] = skip_count
    results["summary"]["info"] = info_count

    if fail_count > 0:
        results["summary"]["overall"] = "FAIL"
        results["summary"]["message"] = f"{fail_count} 项数值验证未通过"
    elif warn_count > 0:
        results["summary"]["overall"] = "WARN"
        results["summary"]["message"] = f"{warn_count} 项数值验证有警告"
    else:
        results["summary"]["overall"] = "PASS"
        results["summary"]["message"] = "所有数值验证通过"

    return results


def main():
    parser = argparse.ArgumentParser(description="合同数值计算验证脚本")
    parser.add_argument("--json", "-j", required=True, help="输入 JSON 文件路径")
    parser.add_argument("--output", "-o", help="输出结果 JSON 文件路径（可选，默认输出到 stdout）")
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

    # 退出码: 有 fail 则非零
    sys.exit(1 if results["summary"]["overall"] == "FAIL" else 0)


if __name__ == "__main__":
    main()
